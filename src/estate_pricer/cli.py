"""CLI interface for Estate Sale Pricer."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from estate_pricer.config import load_config
from estate_pricer.db import Database

app = typer.Typer(
    name="estate-pricer",
    help="Analyze estate sale photos and estimate resale value via eBay comps.",
    add_completion=False,
)
console = Console()


def _get_config():
    return load_config()


def _get_db(config=None):
    if config is None:
        config = _get_config()
    return Database(config.db_path)


@app.command()
def scan(
    url: str = typer.Argument(..., help="URL of the estate sale listing"),
    output: str = typer.Option("terminal", "--output", "-o", help="Output format: terminal, json, csv, html"),
    output_file: Optional[str] = typer.Option(None, "--output-file", "-f", help="Output file path"),
    min_value: Optional[float] = typer.Option(None, "--min-value", help="Minimum median value filter"),
    min_confidence: Optional[str] = typer.Option(None, "--min-confidence", help="Minimum confidence: low, medium, high"),
    sort: str = typer.Option("value", "--sort", "-s", help="Sort by: value, confidence, category"),
    categories: Optional[str] = typer.Option(None, "--category", "-c", help="Filter categories (comma-separated)"),
    accuracy: bool = typer.Option(False, "--accuracy", help="Use claude-opus-4-6 for higher accuracy"),
):
    """Scan an estate sale listing: scrape photos, identify items, and price them."""
    config = _get_config()
    db = _get_db(config)

    if accuracy:
        config.analyzer.model = "claude-opus-4-6"

    if not config.anthropic_api_key:
        console.print("[red]Error:[/red] ANTHROPIC_API_KEY not set. Add it to your .env file.")
        raise typer.Exit(1)

    if not config.ebay_client_id or not config.ebay_client_secret:
        console.print("[yellow]Warning:[/yellow] eBay API keys not set. Pricing will be skipped.")

    asyncio.run(_scan_async(url, config, db, output, output_file, min_value, min_confidence, sort, categories))


async def _scan_async(url, config, db, output_fmt, output_file, min_value, min_confidence, sort, categories):
    from estate_pricer.scraper.detector import detect_scraper
    from estate_pricer.analyzer.vision import analyze_photos
    from estate_pricer.analyzer.dedup import deduplicate_items
    from estate_pricer.pricer.ebay import EbayClient
    from estate_pricer.pricer.calculator import calculate_pricing
    from estate_pricer.pricer.cache import PricingCache

    # Step 1: Scrape
    console.print(f"\n[bold blue]Scraping[/bold blue] {url}")
    try:
        scraper = detect_scraper(url, config.scraper)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    sale_data = await scraper.scrape(url)
    console.print(f"  Found [bold]{len(sale_data.photos)}[/bold] photos")

    # Save to DB
    db.save_sale({
        "sale_id": sale_data.sale_id,
        "source_url": sale_data.source_url,
        "title": sale_data.title,
        "location": sale_data.location,
        "sale_dates": sale_data.sale_dates,
        "company_name": sale_data.company_name,
        "scraped_at": sale_data.scraped_at,
    })
    for photo in sale_data.photos:
        db.save_photo({
            "photo_id": photo.photo_id,
            "sale_id": sale_data.sale_id,
            "source_url": photo.source_url,
            "local_path": photo.local_path,
            "caption": photo.caption,
            "download_status": photo.download_status,
        })

    # Step 2: Analyze photos
    successful_photos = [p.local_path for p in sale_data.photos if p.download_status == "success"]
    if not successful_photos:
        console.print("[red]Error:[/red] No photos were successfully downloaded.")
        raise typer.Exit(1)

    context = config.analyzer.context_template.format(location=sale_data.location or "unknown location")
    console.print(f"[bold blue]Analyzing[/bold blue] {len(successful_photos)} photos with {config.analyzer.model}...")
    items = await analyze_photos(successful_photos, config, context, sale_data.sale_id)
    items = deduplicate_items(items)
    console.print(f"  Identified [bold]{len(items)}[/bold] unique items")

    for item in items:
        db.save_item(item)

    # Step 3: Price items
    pricing = {}
    if config.ebay_client_id and config.ebay_client_secret:
        console.print(f"[bold blue]Pricing[/bold blue] {len(items)} items via eBay...")
        cache = PricingCache(db, config.pricer.cache_ttl_days)

        with EbayClient(config) as ebay:
            for item in items:
                # Check cache first
                cached = cache.get(item["search_query"])
                if cached:
                    pricing[item["item_id"]] = cached
                    continue

                results, query_used = ebay.search_with_broadening(
                    item["search_query"],
                    brand=item.get("brand"),
                    category=item.get("category"),
                    broadening_threshold=config.pricer.broadening_threshold,
                    limit=config.pricer.max_comps,
                )

                price_data = calculate_pricing(
                    results,
                    item["item_id"],
                    query_used,
                    config.pricer.outlier_std_devs,
                )
                pricing[item["item_id"]] = price_data
                cache.put(price_data)

    # Step 4: Output
    sale_info = {
        "title": sale_data.title,
        "location": sale_data.location,
        "sale_dates": sale_data.sale_dates,
        "source_url": sale_data.source_url,
    }
    category_list = [c.strip() for c in categories.split(",")] if categories else None

    _render_output(output_fmt, output_file, sale_info, items, pricing,
                   len(successful_photos), sort, min_value, min_confidence, category_list)


@app.command()
def analyze(
    path: str = typer.Argument(..., help="Path to a directory of photos or a single image"),
    context: str = typer.Option("", "--context", help="Context about the sale (e.g., '1960s ranch home in Lincoln, NE')"),
    output: str = typer.Option("terminal", "--output", "-o", help="Output format: terminal, json, csv, html"),
    output_file: Optional[str] = typer.Option(None, "--output-file", "-f", help="Output file path"),
    min_value: Optional[float] = typer.Option(None, "--min-value", help="Minimum median value filter"),
    min_confidence: Optional[str] = typer.Option(None, "--min-confidence", help="Minimum confidence: low, medium, high"),
    sort: str = typer.Option("value", "--sort", "-s", help="Sort by: value, confidence, category"),
    categories: Optional[str] = typer.Option(None, "--category", "-c", help="Filter categories (comma-separated)"),
    accuracy: bool = typer.Option(False, "--accuracy", help="Use claude-opus-4-6 for higher accuracy"),
    skip_pricing: bool = typer.Option(False, "--skip-pricing", help="Skip eBay pricing lookup"),
):
    """Analyze local photos (skip scraping). Identify items and optionally price them."""
    config = _get_config()
    db = _get_db(config)

    if accuracy:
        config.analyzer.model = "claude-opus-4-6"

    if not config.anthropic_api_key:
        console.print("[red]Error:[/red] ANTHROPIC_API_KEY not set. Add it to your .env file.")
        raise typer.Exit(1)

    # Gather image paths
    photo_path = Path(path)
    if photo_path.is_dir():
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        image_paths = sorted(
            str(p) for p in photo_path.iterdir()
            if p.suffix.lower() in image_extensions
        )
    elif photo_path.is_file():
        image_paths = [str(photo_path)]
    else:
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    if not image_paths:
        console.print(f"[red]Error:[/red] No images found in {path}")
        raise typer.Exit(1)

    asyncio.run(_analyze_async(
        image_paths, config, db, context, output, output_file,
        min_value, min_confidence, sort, categories, skip_pricing,
    ))


async def _analyze_async(
    image_paths, config, db, context, output_fmt, output_file,
    min_value, min_confidence, sort, categories, skip_pricing,
):
    from estate_pricer.analyzer.vision import analyze_photos
    from estate_pricer.analyzer.dedup import deduplicate_items
    from estate_pricer.pricer.ebay import EbayClient
    from estate_pricer.pricer.calculator import calculate_pricing
    from estate_pricer.pricer.cache import PricingCache

    console.print(f"\n[bold blue]Analyzing[/bold blue] {len(image_paths)} photos with {config.analyzer.model}...")
    items = await analyze_photos(image_paths, config, context)
    items = deduplicate_items(items)
    console.print(f"  Identified [bold]{len(items)}[/bold] unique items")

    # Price items
    pricing = {}
    if not skip_pricing and config.ebay_client_id and config.ebay_client_secret:
        console.print(f"[bold blue]Pricing[/bold blue] {len(items)} items via eBay...")
        cache = PricingCache(db, config.pricer.cache_ttl_days)

        with EbayClient(config) as ebay:
            for item in items:
                cached = cache.get(item["search_query"])
                if cached:
                    pricing[item["item_id"]] = cached
                    continue

                results, query_used = ebay.search_with_broadening(
                    item["search_query"],
                    brand=item.get("brand"),
                    category=item.get("category"),
                    broadening_threshold=config.pricer.broadening_threshold,
                    limit=config.pricer.max_comps,
                )
                price_data = calculate_pricing(
                    results, item["item_id"], query_used, config.pricer.outlier_std_devs,
                )
                pricing[item["item_id"]] = price_data
                cache.put(price_data)
    elif not skip_pricing:
        console.print("[yellow]Warning:[/yellow] eBay API keys not set. Skipping pricing.")

    category_list = [c.strip() for c in categories.split(",")] if categories else None
    _render_output(output_fmt, output_file, None, items, pricing,
                   len(image_paths), sort, min_value, min_confidence, category_list)


@app.command()
def price(
    query: str = typer.Argument(..., help="eBay search query for the item"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max number of comps"),
):
    """Look up eBay sold prices for a specific item query."""
    config = _get_config()

    if not config.ebay_client_id or not config.ebay_client_secret:
        console.print("[red]Error:[/red] eBay API keys not set. Add EBAY_CLIENT_ID and EBAY_CLIENT_SECRET to your .env file.")
        raise typer.Exit(1)

    from estate_pricer.pricer.ebay import EbayClient
    from estate_pricer.pricer.calculator import calculate_pricing

    console.print(f"\n[bold blue]Searching[/bold blue] eBay sold listings for: [bold]{query}[/bold]")

    with EbayClient(config) as ebay:
        results, query_used = ebay.search_with_broadening(
            query,
            broadening_threshold=config.pricer.broadening_threshold,
            limit=limit,
        )

    if not results:
        console.print("[yellow]No sold listings found.[/yellow]")
        raise typer.Exit(0)

    price_data = calculate_pricing(results, "manual", query_used, config.pricer.outlier_std_devs)

    console.print(f"\n  Query: [dim]{query_used}[/dim]")
    console.print(f"  Results: [bold]{price_data['results_count']}[/bold] sold comps")
    console.print(f"  Median: [bold green]${price_data['price_median']:,.2f}[/bold green]")
    console.print(f"  Range: ${price_data['price_low']:,.2f} - ${price_data['price_high']:,.2f}")
    console.print(f"  Average: ${price_data['price_average']:,.2f}")
    console.print(f"  Confidence: {price_data['pricing_confidence']}")

    if results:
        console.print("\n  [bold]Recent sales:[/bold]")
        for sale in results[:5]:
            console.print(f"    ${sale['sold_price']:,.2f} — {sale['title'][:60]}")
    console.print()


@app.command()
def reprice(
    sale_id: str = typer.Argument(..., help="Sale ID to re-price"),
):
    """Re-price items from a previous scan with fresh eBay data."""
    config = _get_config()
    db = _get_db(config)

    if not config.ebay_client_id or not config.ebay_client_secret:
        console.print("[red]Error:[/red] eBay API keys not set.")
        raise typer.Exit(1)

    sale = db.get_sale(sale_id)
    if not sale:
        console.print(f"[red]Error:[/red] Sale '{sale_id}' not found in database.")
        raise typer.Exit(1)

    items = db.get_items_for_sale(sale_id)
    if not items:
        console.print(f"[yellow]No items found for sale '{sale_id}'.[/yellow]")
        raise typer.Exit(0)

    from estate_pricer.pricer.ebay import EbayClient
    from estate_pricer.pricer.calculator import calculate_pricing

    console.print(f"\n[bold blue]Re-pricing[/bold blue] {len(items)} items for: {sale.get('title', sale_id)}")

    pricing = {}
    with EbayClient(config) as ebay:
        for item in items:
            results, query_used = ebay.search_with_broadening(
                item["search_query"],
                brand=item.get("brand"),
                category=item.get("category"),
                broadening_threshold=config.pricer.broadening_threshold,
                limit=config.pricer.max_comps,
            )
            price_data = calculate_pricing(
                results, item["item_id"], query_used, config.pricer.outlier_std_devs,
            )
            pricing[item["item_id"]] = price_data
            db.save_pricing(price_data)

    sale_info = {
        "title": sale.get("title"),
        "location": sale.get("location"),
        "sale_dates": sale.get("sale_dates", []),
        "source_url": sale.get("source_url"),
    }

    from estate_pricer.output.terminal import render_results
    render_results(sale_info, items, pricing)


def _render_output(
    output_fmt, output_file, sale_info, items, pricing,
    total_photos, sort, min_value, min_confidence, categories,
):
    """Render results in the requested format."""
    if output_fmt == "terminal" or (output_fmt != "terminal" and not output_file):
        from estate_pricer.output.terminal import render_results
        render_results(
            sale_info, items, pricing,
            total_photos=total_photos,
            sort_by=sort,
            min_value=min_value,
            min_confidence=min_confidence,
            categories=categories,
        )

    if output_fmt == "json":
        from estate_pricer.output.json_export import export_json
        result = export_json(sale_info, items, pricing, output_file)
        if output_file:
            console.print(f"\n[green]JSON exported to:[/green] {output_file}")
        else:
            console.print(result)

    elif output_fmt == "csv":
        from estate_pricer.output.csv_export import export_csv
        result = export_csv(items, pricing, output_file)
        if output_file:
            console.print(f"\n[green]CSV exported to:[/green] {output_file}")
        else:
            console.print(result)

    elif output_fmt == "html":
        from estate_pricer.output.html_export import export_html
        result = export_html(sale_info, items, pricing, output_file)
        if output_file:
            console.print(f"\n[green]HTML report exported to:[/green] {output_file}")
        else:
            console.print(result)


if __name__ == "__main__":
    app()
