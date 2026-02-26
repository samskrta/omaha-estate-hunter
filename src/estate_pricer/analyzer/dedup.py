"""Cross-photo item deduplication using fuzzy matching."""

from difflib import SequenceMatcher


def _similarity(a: str, b: str) -> float:
    """Calculate string similarity ratio between 0 and 1."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate_items(
    items: list[dict],
    name_threshold: float = 0.75,
    query_threshold: float = 0.70,
) -> list[dict]:
    """Remove duplicate items that appear across multiple photos.

    When two items are similar enough, keeps the one with higher confidence.
    Falls back to the one with more notable features.

    Args:
        items: List of identified item dicts.
        name_threshold: Minimum name similarity to consider a duplicate.
        query_threshold: Minimum search query similarity to consider a duplicate.

    Returns:
        Deduplicated list of items.
    """
    if not items:
        return []

    confidence_rank = {"high": 3, "medium": 2, "low": 1}

    # Sort by confidence descending so we keep the best identification
    sorted_items = sorted(
        items,
        key=lambda x: confidence_rank.get(x.get("confidence", "low"), 0),
        reverse=True,
    )

    kept = []
    for item in sorted_items:
        is_duplicate = False
        for existing in kept:
            # Check name similarity
            name_sim = _similarity(item.get("name", ""), existing.get("name", ""))
            # Check search query similarity
            query_sim = _similarity(
                item.get("search_query", ""), existing.get("search_query", "")
            )
            # Check category match
            same_category = item.get("category") == existing.get("category")

            if same_category and (
                name_sim >= name_threshold or query_sim >= query_threshold
            ):
                is_duplicate = True
                # Merge notable features from the duplicate into the kept item
                existing_features = set(existing.get("notable_features", []))
                new_features = set(item.get("notable_features", []))
                existing["notable_features"] = list(existing_features | new_features)
                break

        if not is_duplicate:
            kept.append(item)

    return kept
