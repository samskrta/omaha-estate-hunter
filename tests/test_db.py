"""Tests for database module."""

import json
import os
import tempfile

from estate_pricer.db import Database


class TestDatabase:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = Database(self.tmp.name)

    def teardown_method(self):
        os.unlink(self.tmp.name)

    def test_save_and_get_sale(self):
        sale = {
            "sale_id": "test-sale-1",
            "source_url": "https://example.com/sale/1",
            "title": "Test Estate Sale",
            "location": "Omaha, NE",
            "sale_dates": ["March 15, 2025", "March 16, 2025"],
            "company_name": "Test Co",
            "scraped_at": "2025-03-14T00:00:00Z",
        }
        self.db.save_sale(sale)
        result = self.db.get_sale("test-sale-1")
        assert result is not None
        assert result["title"] == "Test Estate Sale"
        assert result["sale_dates"] == ["March 15, 2025", "March 16, 2025"]

    def test_get_nonexistent_sale(self):
        result = self.db.get_sale("nonexistent")
        assert result is None

    def test_save_and_get_items(self):
        # First save a sale
        self.db.save_sale({
            "sale_id": "s1",
            "source_url": "https://example.com",
            "scraped_at": "2025-01-01T00:00:00Z",
        })
        self.db.save_photo({
            "photo_id": "p1",
            "sale_id": "s1",
            "source_url": "https://example.com/photo.jpg",
            "download_status": "success",
        })
        self.db.save_item({
            "item_id": "i1",
            "photo_id": "p1",
            "sale_id": "s1",
            "name": "KitchenAid Mixer",
            "category": "appliances",
            "brand": "KitchenAid",
            "search_query": "KitchenAid mixer",
            "confidence": "high",
            "notable_features": ["avocado green"],
            "identified_at": "2025-01-01T00:00:00Z",
        })

        items = self.db.get_items_for_sale("s1")
        assert len(items) == 1
        assert items[0]["name"] == "KitchenAid Mixer"
        assert items[0]["notable_features"] == ["avocado green"]

    def test_save_and_get_pricing(self):
        # Setup dependencies
        self.db.save_sale({
            "sale_id": "s1",
            "source_url": "https://example.com",
            "scraped_at": "2025-01-01T00:00:00Z",
        })
        self.db.save_photo({
            "photo_id": "p1",
            "sale_id": "s1",
            "source_url": "https://example.com/photo.jpg",
            "download_status": "success",
        })
        self.db.save_item({
            "item_id": "i1",
            "photo_id": "p1",
            "sale_id": "s1",
            "name": "Test Item",
            "category": "other",
            "search_query": "test item",
            "confidence": "low",
            "notable_features": [],
            "identified_at": "2025-01-01T00:00:00Z",
        })
        self.db.save_pricing({
            "pricing_id": "pr1",
            "item_id": "i1",
            "search_query_used": "test item",
            "results_count": 5,
            "price_low": 10.0,
            "price_median": 25.0,
            "price_high": 50.0,
            "price_average": 27.0,
            "pricing_confidence": "medium",
            "recent_sales": [{"title": "Test", "price": 25.0}],
            "queried_at": "2025-01-01T00:00:00Z",
        })

        pricing = self.db.get_pricing_for_item("i1")
        assert pricing is not None
        assert pricing["price_median"] == 25.0
        assert pricing["pricing_confidence"] == "medium"

    def test_upsert_sale(self):
        sale = {
            "sale_id": "s1",
            "source_url": "https://example.com",
            "title": "Original",
            "scraped_at": "2025-01-01T00:00:00Z",
        }
        self.db.save_sale(sale)

        sale["title"] = "Updated"
        self.db.save_sale(sale)

        result = self.db.get_sale("s1")
        assert result["title"] == "Updated"
