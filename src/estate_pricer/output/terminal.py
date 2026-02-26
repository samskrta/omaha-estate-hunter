"""Rich terminal output for estate sale pricing results."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


console = Console()

CONFIDENCE_STARS = {
    "high": "\u2605\u2605\u2605",
    "medium": "\u2605\u2605\u2606",
    "low": "\u2605\u2606\u2606",
    "none": "\u2606\u2606\u2606",
}

CONFIDENCE_COLORS = {
    "high": "green",
    "medium": "yellow",
    "low": "red",
    "none": "dim",
}


def format_price(price: float | None) -> str:
    """Format a price as USD string."""
    if price is None:
        return "N/A"
    return f"${price:,.2f}"


def format_range(low: float | None, high: float | None) -> str:
    """Format a price range."""
    if low is None or high is None:
        return "N/A"
    return f"${low:,.0f}-${high:,.0f}"


def render_results(
    sale_info: dict | None,
    items: list[dict],
    pricing: dict[str, dict],
    total_photos: int = 0,
    api_cost: float = 0.0,
    sort_by: str = "value",
    min_value: float | None = None,
    min_confidence: str | None = None,
    categories: list[str] | None = None,
):
    """Render pricing results as a rich terminal table.

    Args:
        sale_info: Sale metadata dict (title, location, dates, source_url).
        items: List of identified item dicts.
        pricing: Dict mapping item_id to pricing data dict.
        total_photos: Number of photos analyzed.
        api_cost: Estimated API cost.
        sort_by: Sort key ('value', 'confidence', 'category').
        min_value: Minimum median value filter.
        min_confidence: Minimum confidence filter.
        categories: Category filter list.
    """
    # Header
    if sale_info:
        title = sale_info.get("title", "Unknown Sale")
        location = sale_info.get("location", "")
        dates = sale_info.get("sale_dates", [])
        date_str = f" ({', '.join(dates)})" if dates else ""
        source = sale_info.get("source_url", "")

        console.print()
        console.print(
            Panel(
                f"[bold]{title}[/bold] - {location}{date_str}\n[dim]{source}[/dim]",
                title="Estate Sale Analysis",
                border_style="blue",
            )
        )
    else:
        console.print()
        console.print(Panel("Photo Analysis Results", border_style="blue"))

    # Build combined data
    rows = []
    for item in items:
        item_pricing = pricing.get(item["item_id"], {})
        median = item_pricing.get("price_median")
        low = item_pricing.get("price_low")
        high = item_pricing.get("price_high")
        comps = item_pricing.get("results_count", 0)
        price_conf = item_pricing.get("pricing_confidence", "none")
        item_conf = item.get("confidence", "low")

        # Apply filters
        if min_value is not None and (median is None or median < min_value):
            continue
        if min_confidence:
            conf_order = ["low", "medium", "high"]
            if min_confidence in conf_order:
                min_idx = conf_order.index(min_confidence)
                item_idx = conf_order.index(item_conf) if item_conf in conf_order else -1
                if item_idx < min_idx:
                    continue
        if categories and item.get("category") not in categories:
            continue

        rows.append({
            "item": item,
            "median": median,
            "low": low,
            "high": high,
            "comps": comps,
            "price_conf": price_conf,
            "item_conf": item_conf,
        })

    # Sort
    if sort_by == "value":
        rows.sort(key=lambda r: r["median"] or 0, reverse=True)
    elif sort_by == "confidence":
        conf_rank = {"high": 3, "medium": 2, "low": 1, "none": 0}
        rows.sort(key=lambda r: conf_rank.get(r["item_conf"], 0), reverse=True)
    elif sort_by == "category":
        rows.sort(key=lambda r: r["item"]["category"])

    # Build table
    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Conf", justify="center", width=5)
    table.add_column("Item", min_width=30)
    table.add_column("Category", width=14)
    table.add_column("Median $", justify="right", width=10)
    table.add_column("Range", justify="right", width=14)
    table.add_column("# Comps", justify="right", width=9)

    total_median = 0.0
    total_low = 0.0
    total_high = 0.0

    for row in rows:
        stars = CONFIDENCE_STARS.get(row["item_conf"], "\u2606\u2606\u2606")
        color = CONFIDENCE_COLORS.get(row["item_conf"], "dim")

        name = row["item"]["name"]
        brand = row["item"].get("brand")
        if brand and brand.lower() not in name.lower():
            name = f"{brand} {name}"

        median_str = format_price(row["median"])
        range_str = format_range(row["low"], row["high"])
        comps_str = f"{row['comps']} sold" if row["comps"] else "no data"

        table.add_row(
            Text(stars, style=color),
            name,
            row["item"]["category"].replace("_", " ").title(),
            median_str,
            range_str,
            comps_str,
        )

        if row["median"]:
            total_median += row["median"]
        if row["low"]:
            total_low += row["low"]
        if row["high"]:
            total_high += row["high"]

    console.print(table)

    # Summary
    console.print()
    summary_parts = [
        f"[bold]Total Estimated Value:[/bold] {format_price(total_median)} (median)",
        f"  |  {format_range(total_low, total_high)} (range)",
    ]
    console.print("".join(summary_parts))

    stats_parts = [
        f"[dim]Items Identified: {len(rows)}",
    ]
    if total_photos:
        stats_parts.append(f"Photos Analyzed: {total_photos}")
    if api_cost > 0:
        stats_parts.append(f"API Cost: ${api_cost:.2f}")
    console.print(" | ".join(stats_parts) + "[/dim]")
    console.print()
