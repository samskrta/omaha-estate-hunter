"""Tests for scraper modules."""

from estate_pricer.scraper.estatesales_net import EstateSalesNetScraper
from estate_pricer.scraper.estatesales_org import EstateSalesOrgScraper
from estate_pricer.scraper.detector import detect_scraper
from estate_pricer.config import ScraperConfig

import pytest


class TestEstateSalesNetScraper:
    def test_can_handle_valid_url(self):
        assert EstateSalesNetScraper.can_handle(
            "https://estatesales.net/estate-sales/NE/Omaha/12345"
        )

    def test_can_handle_www(self):
        assert EstateSalesNetScraper.can_handle(
            "https://www.estatesales.net/estate-sales/NE/Omaha/12345"
        )

    def test_cannot_handle_other_site(self):
        assert not EstateSalesNetScraper.can_handle(
            "https://estatesales.org/estate-sales/12345"
        )

    def test_cannot_handle_random_url(self):
        assert not EstateSalesNetScraper.can_handle(
            "https://example.com/something"
        )


class TestEstateSalesOrgScraper:
    def test_can_handle_valid_url(self):
        assert EstateSalesOrgScraper.can_handle(
            "https://estatesales.org/estate-sales/12345"
        )

    def test_cannot_handle_net(self):
        assert not EstateSalesOrgScraper.can_handle(
            "https://estatesales.net/estate-sales/NE/Omaha/12345"
        )


class TestDetector:
    def test_detects_estatesales_net(self):
        config = ScraperConfig()
        scraper = detect_scraper(
            "https://estatesales.net/estate-sales/NE/Omaha/12345", config
        )
        assert isinstance(scraper, EstateSalesNetScraper)

    def test_detects_estatesales_org(self):
        config = ScraperConfig()
        scraper = detect_scraper(
            "https://estatesales.org/estate-sales/12345", config
        )
        assert isinstance(scraper, EstateSalesOrgScraper)

    def test_raises_for_unsupported_url(self):
        config = ScraperConfig()
        with pytest.raises(ValueError, match="Unsupported URL"):
            detect_scraper("https://example.com/sale", config)
