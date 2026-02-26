"""SQLite-backed pricing cache."""

from estate_pricer.db import Database


class PricingCache:
    """Cache layer for eBay pricing lookups backed by SQLite."""

    def __init__(self, db: Database, ttl_days: int = 7):
        self.db = db
        self.ttl_days = ttl_days

    def get(self, search_query: str) -> dict | None:
        """Look up cached pricing for a search query.

        Args:
            search_query: The eBay search query.

        Returns:
            Cached pricing dict or None if not found / expired.
        """
        return self.db.get_cached_pricing(search_query, max_age_days=self.ttl_days)

    def put(self, pricing_data: dict):
        """Store pricing data in the cache.

        Args:
            pricing_data: Pricing dict to store.
        """
        self.db.save_pricing(pricing_data)
