"""URL detection and scraper routing."""

from estate_pricer.config import ScraperConfig
from estate_pricer.scraper.base import BaseScraper
from estate_pricer.scraper.estatesales_net import EstateSalesNetScraper
from estate_pricer.scraper.estatesales_org import EstateSalesOrgScraper


# Registered scrapers in priority order
SCRAPER_CLASSES: list[type[BaseScraper]] = [
    EstateSalesNetScraper,
    EstateSalesOrgScraper,
]

SUPPORTED_SITES = [
    "EstateSales.NET (estatesales.net/estate-sales/[state]/[city]/[id])",
    "EstateSales.ORG (estatesales.org/estate-sales/[id])",
]


def detect_scraper(url: str, config: ScraperConfig) -> BaseScraper:
    """Detect the appropriate scraper for a given URL.

    Args:
        url: The estate sale listing URL.
        config: Scraper configuration.

    Returns:
        An instantiated scraper for the URL.

    Raises:
        ValueError: If the URL doesn't match any supported site.
    """
    for scraper_cls in SCRAPER_CLASSES:
        if scraper_cls.can_handle(url):
            return scraper_cls(config)

    supported = "\n  - ".join(SUPPORTED_SITES)
    raise ValueError(
        f"Unsupported URL: {url}\n\nSupported sites:\n  - {supported}"
    )
