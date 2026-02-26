"""Tests for price calculator module."""

from estate_pricer.pricer.calculator import calculate_pricing, remove_outliers


class TestRemoveOutliers:
    def test_empty_list(self):
        assert remove_outliers([]) == []

    def test_single_value(self):
        assert remove_outliers([100.0]) == [100.0]

    def test_two_values(self):
        assert remove_outliers([50.0, 100.0]) == [50.0, 100.0]

    def test_no_outliers(self):
        prices = [95.0, 100.0, 105.0, 98.0, 102.0]
        result = remove_outliers(prices)
        assert result == prices

    def test_removes_high_outlier(self):
        prices = [100.0, 105.0, 98.0, 102.0, 99.0, 500.0]
        result = remove_outliers(prices)
        assert 500.0 not in result
        assert 100.0 in result

    def test_removes_low_outlier(self):
        prices = [100.0, 105.0, 98.0, 102.0, 99.0, 1.0]
        result = remove_outliers(prices)
        assert 1.0 not in result

    def test_identical_values(self):
        prices = [50.0, 50.0, 50.0, 50.0]
        result = remove_outliers(prices)
        assert result == prices


class TestCalculatePricing:
    def test_empty_results(self):
        result = calculate_pricing([], "item-1", "test query")
        assert result["results_count"] == 0
        assert result["price_median"] is None
        assert result["pricing_confidence"] == "none"

    def test_single_result(self):
        sold_items = [{"sold_price": 50.0, "title": "Test Item"}]
        result = calculate_pricing(sold_items, "item-1", "test query")
        assert result["results_count"] == 1
        assert result["price_median"] == 50.0
        assert result["price_low"] == 50.0
        assert result["price_high"] == 50.0
        assert result["pricing_confidence"] == "low"

    def test_multiple_results(self):
        sold_items = [
            {"sold_price": 100.0, "title": "Item A"},
            {"sold_price": 150.0, "title": "Item B"},
            {"sold_price": 120.0, "title": "Item C"},
            {"sold_price": 130.0, "title": "Item D"},
            {"sold_price": 110.0, "title": "Item E"},
        ]
        result = calculate_pricing(sold_items, "item-1", "test query")
        assert result["results_count"] == 5
        assert result["price_median"] == 120.0
        assert result["price_low"] == 100.0
        assert result["price_high"] == 150.0
        assert result["pricing_confidence"] == "medium"

    def test_high_confidence_many_results(self):
        sold_items = [{"sold_price": float(i * 10)} for i in range(1, 15)]
        result = calculate_pricing(sold_items, "item-1", "test query")
        assert result["pricing_confidence"] == "high"

    def test_skips_zero_prices(self):
        sold_items = [
            {"sold_price": 0.0},
            {"sold_price": 100.0},
            {"sold_price": 50.0},
        ]
        result = calculate_pricing(sold_items, "item-1", "test query")
        assert result["results_count"] == 2

    def test_item_id_and_query_preserved(self):
        sold_items = [{"sold_price": 75.0}]
        result = calculate_pricing(sold_items, "my-item", "vintage lamp brass")
        assert result["item_id"] == "my-item"
        assert result["search_query_used"] == "vintage lamp brass"

    def test_recent_sales_capped_at_10(self):
        sold_items = [{"sold_price": float(i)} for i in range(1, 25)]
        result = calculate_pricing(sold_items, "item-1", "test query")
        assert len(result["recent_sales"]) == 10
