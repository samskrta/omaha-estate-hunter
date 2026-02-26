"""Price statistics calculation with outlier removal."""

import math
import statistics
import uuid
from datetime import datetime, timezone


def remove_outliers(prices: list[float], std_devs: float = 2.0) -> list[float]:
    """Remove price outliers beyond N standard deviations from the mean.

    Args:
        prices: List of prices.
        std_devs: Number of standard deviations for outlier threshold.

    Returns:
        Filtered list with outliers removed.
    """
    if len(prices) < 3:
        return prices

    mean = statistics.mean(prices)
    stdev = statistics.stdev(prices)

    if stdev == 0:
        return prices

    return [p for p in prices if abs(p - mean) <= std_devs * stdev]


def calculate_pricing(
    sold_items: list[dict],
    item_id: str,
    search_query: str,
    outlier_std_devs: float = 2.0,
) -> dict:
    """Calculate pricing statistics from sold item data.

    Args:
        sold_items: List of dicts with 'sold_price' field.
        item_id: ID of the item being priced.
        search_query: Query used to find these comps.
        outlier_std_devs: Std devs for outlier removal.

    Returns:
        Pricing data dict ready for database storage.
    """
    prices = [item["sold_price"] for item in sold_items if item.get("sold_price", 0) > 0]

    if not prices:
        return {
            "pricing_id": str(uuid.uuid4()),
            "item_id": item_id,
            "search_query_used": search_query,
            "results_count": 0,
            "price_low": None,
            "price_median": None,
            "price_high": None,
            "price_average": None,
            "pricing_confidence": "none",
            "recent_sales": sold_items[:10],
            "queried_at": datetime.now(timezone.utc).isoformat(),
        }

    # Remove outliers
    filtered = remove_outliers(prices, outlier_std_devs)
    if not filtered:
        filtered = prices  # Fallback if all removed

    price_low = min(filtered)
    price_high = max(filtered)
    price_median = statistics.median(filtered)
    price_average = statistics.mean(filtered)

    # Determine confidence based on comp count
    count = len(filtered)
    if count >= 10:
        confidence = "high"
    elif count >= 3:
        confidence = "medium"
    elif count >= 1:
        confidence = "low"
    else:
        confidence = "none"

    return {
        "pricing_id": str(uuid.uuid4()),
        "item_id": item_id,
        "search_query_used": search_query,
        "results_count": count,
        "price_low": round(price_low, 2),
        "price_median": round(price_median, 2),
        "price_high": round(price_high, 2),
        "price_average": round(price_average, 2),
        "pricing_confidence": confidence,
        "recent_sales": sold_items[:10],
        "queried_at": datetime.now(timezone.utc).isoformat(),
    }
