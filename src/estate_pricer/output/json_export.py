"""JSON export for estate sale pricing results."""

import json
from datetime import datetime, timezone
from pathlib import Path


def export_json(
    sale_info: dict | None,
    items: list[dict],
    pricing: dict[str, dict],
    output_path: str | None = None,
) -> str:
    """Export results as JSON.

    Args:
        sale_info: Sale metadata dict.
        items: List of identified item dicts.
        pricing: Dict mapping item_id to pricing data.
        output_path: Optional file path to write to.

    Returns:
        JSON string of the results.
    """
    export_data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "sale": sale_info,
        "items": [],
    }

    for item in items:
        item_pricing = pricing.get(item["item_id"], {})
        export_data["items"].append({
            "item": item,
            "pricing": item_pricing,
        })

    json_str = json.dumps(export_data, indent=2, default=str)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(json_str)

    return json_str
