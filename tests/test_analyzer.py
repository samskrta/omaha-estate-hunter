"""Tests for analyzer modules."""

from estate_pricer.analyzer.vision import _validate_item


class TestValidateItem:
    def test_valid_item(self):
        item = {
            "name": "KitchenAid K5-A Mixer",
            "category": "appliances",
            "search_query": "KitchenAid K5-A mixer",
            "confidence": "high",
            "condition_estimate": "good",
            "notable_features": ["avocado green"],
        }
        result = _validate_item(item)
        assert result is not None
        assert result["name"] == "KitchenAid K5-A Mixer"
        assert "item_id" in result

    def test_missing_name_returns_none(self):
        item = {"search_query": "test", "category": "other", "confidence": "low"}
        assert _validate_item(item) is None

    def test_missing_search_query_returns_none(self):
        item = {"name": "Test", "category": "other", "confidence": "low"}
        assert _validate_item(item) is None

    def test_normalizes_invalid_category(self):
        item = {
            "name": "Test",
            "search_query": "test",
            "category": "INVALID_CATEGORY",
            "confidence": "high",
        }
        result = _validate_item(item)
        assert result["category"] == "other"

    def test_normalizes_invalid_confidence(self):
        item = {
            "name": "Test",
            "search_query": "test",
            "category": "tools",
            "confidence": "very_high",
        }
        result = _validate_item(item)
        assert result["confidence"] == "low"

    def test_normalizes_invalid_condition(self):
        item = {
            "name": "Test",
            "search_query": "test",
            "category": "tools",
            "confidence": "high",
            "condition_estimate": "mint",
        }
        result = _validate_item(item)
        assert result["condition_estimate"] == "unknown"

    def test_ensures_notable_features_is_list(self):
        item = {
            "name": "Test",
            "search_query": "test",
            "category": "tools",
            "confidence": "high",
            "notable_features": "not a list",
        }
        result = _validate_item(item)
        assert result["notable_features"] == []
