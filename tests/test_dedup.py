"""Tests for item deduplication module."""

from estate_pricer.analyzer.dedup import deduplicate_items


class TestDeduplicateItems:
    def test_empty_list(self):
        assert deduplicate_items([]) == []

    def test_no_duplicates(self):
        items = [
            {"name": "KitchenAid Mixer", "category": "appliances", "search_query": "KitchenAid mixer", "confidence": "high", "notable_features": []},
            {"name": "Pyrex Bowl", "category": "kitchenware", "search_query": "Pyrex mixing bowl", "confidence": "medium", "notable_features": []},
        ]
        result = deduplicate_items(items)
        assert len(result) == 2

    def test_exact_duplicates(self):
        items = [
            {"name": "KitchenAid K5-A Mixer", "category": "appliances", "search_query": "KitchenAid K5-A mixer", "confidence": "high", "notable_features": ["avocado"]},
            {"name": "KitchenAid K5-A Mixer", "category": "appliances", "search_query": "KitchenAid K5-A mixer", "confidence": "medium", "notable_features": ["working"]},
        ]
        result = deduplicate_items(items)
        assert len(result) == 1
        # Should keep the high-confidence one
        assert result[0]["confidence"] == "high"
        # Should merge features
        assert "avocado" in result[0]["notable_features"]
        assert "working" in result[0]["notable_features"]

    def test_similar_names_same_category(self):
        items = [
            {"name": "Pyrex 401 Primary Blue Bowl", "category": "kitchenware", "search_query": "Pyrex 401 blue mixing bowl", "confidence": "high", "notable_features": []},
            {"name": "Pyrex 401 Blue Mixing Bowl", "category": "kitchenware", "search_query": "Pyrex 401 mixing bowl blue", "confidence": "medium", "notable_features": []},
        ]
        result = deduplicate_items(items)
        assert len(result) == 1

    def test_similar_names_different_category(self):
        items = [
            {"name": "Vintage Lamp", "category": "furniture", "search_query": "vintage lamp", "confidence": "low", "notable_features": []},
            {"name": "Vintage Lamp", "category": "electronics", "search_query": "vintage lamp", "confidence": "low", "notable_features": []},
        ]
        result = deduplicate_items(items)
        # Different categories should not be deduplicated
        assert len(result) == 2

    def test_keeps_higher_confidence(self):
        items = [
            {"name": "KitchenAid Stand Mixer", "category": "appliances", "search_query": "KitchenAid stand mixer", "confidence": "low", "notable_features": []},
            {"name": "KitchenAid Stand Mixer Red", "category": "appliances", "search_query": "KitchenAid stand mixer red", "confidence": "high", "notable_features": ["red"]},
        ]
        result = deduplicate_items(items)
        assert len(result) == 1
        assert result[0]["confidence"] == "high"
