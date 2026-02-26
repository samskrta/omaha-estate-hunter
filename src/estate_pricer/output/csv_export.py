"""CSV export for estate sale pricing results."""

import csv
import io
from pathlib import Path


def export_csv(
    items: list[dict],
    pricing: dict[str, dict],
    output_path: str | None = None,
) -> str:
    """Export results as CSV.

    Args:
        items: List of identified item dicts.
        pricing: Dict mapping item_id to pricing data.
        output_path: Optional file path to write to.

    Returns:
        CSV string of the results.
    """
    fieldnames = [
        "name",
        "category",
        "brand",
        "model",
        "era",
        "condition",
        "confidence",
        "search_query",
        "median_price",
        "low_price",
        "high_price",
        "avg_price",
        "num_comps",
        "pricing_confidence",
        "notable_features",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for item in items:
        item_pricing = pricing.get(item["item_id"], {})
        features = item.get("notable_features", [])

        writer.writerow({
            "name": item.get("name", ""),
            "category": item.get("category", ""),
            "brand": item.get("brand", ""),
            "model": item.get("model", ""),
            "era": item.get("era", ""),
            "condition": item.get("condition_estimate", ""),
            "confidence": item.get("confidence", ""),
            "search_query": item.get("search_query", ""),
            "median_price": item_pricing.get("price_median", ""),
            "low_price": item_pricing.get("price_low", ""),
            "high_price": item_pricing.get("price_high", ""),
            "avg_price": item_pricing.get("price_average", ""),
            "num_comps": item_pricing.get("results_count", ""),
            "pricing_confidence": item_pricing.get("pricing_confidence", ""),
            "notable_features": "; ".join(features) if features else "",
        })

    csv_str = output.getvalue()

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as f:
            f.write(csv_str)

    return csv_str
