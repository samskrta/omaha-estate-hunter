"""Scraper for EstateSales.NET listings."""

import re
from datetime import datetime, timezone

from estate_pricer.config import ScraperConfig
from estate_pricer.scraper.base import BaseScraper, SaleData


class EstateSalesNetScraper(BaseScraper):
    """Scraper for estatesales.net estate sale listings."""

    URL_PATTERN = re.compile(
        r"https?://(www\.)?estatesales\.net/estate-sales/\w+/[\w-]+/\d+"
    )

    def __init__(self, config: ScraperConfig):
        super().__init__(config)

    @staticmethod
    def can_handle(url: str) -> bool:
        return bool(EstateSalesNetScraper.URL_PATTERN.match(url))

    async def scrape(self, url: str) -> SaleData:
        """Scrape an EstateSales.NET listing page.

        Uses Playwright to handle JS-rendered gallery content.
        """
        from playwright.async_api import async_playwright

        sale_id = self._generate_sale_id(url)
        save_dir = self._get_download_dir(sale_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent=self._random_user_agent()
            )

            try:
                await page.goto(url, timeout=self.config.page_timeout * 1000)
                await page.wait_for_load_state("networkidle")

                # Extract sale metadata
                title = await self._extract_text(page, "h1.sale-title, h1")
                location = await self._extract_text(page, ".sale-address, .address")
                company = await self._extract_text(page, ".company-name, .org-name")
                dates = await self._extract_dates(page)

                # Extract photo URLs from the gallery
                photo_urls = await self._extract_photo_urls(page)

            finally:
                await browser.close()

        # Download all photos
        photos = await self._download_photos(photo_urls, save_dir)

        return SaleData(
            sale_id=sale_id,
            source_url=url,
            title=title,
            location=location,
            sale_dates=dates,
            company_name=company if company else None,
            photos=photos,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )

    async def _extract_text(self, page, selector: str) -> str:
        """Extract text content from the first matching element."""
        try:
            el = page.locator(selector).first
            text = await el.text_content(timeout=5000)
            return text.strip() if text else ""
        except Exception:
            return ""

    async def _extract_dates(self, page) -> list[str]:
        """Extract sale dates from the page."""
        dates = []
        try:
            date_elements = page.locator(".sale-dates .date-item, .sale-date, time")
            count = await date_elements.count()
            for i in range(count):
                text = await date_elements.nth(i).text_content()
                if text:
                    dates.append(text.strip())
        except Exception:
            pass
        return dates

    async def _extract_photo_urls(self, page) -> list[str]:
        """Extract all photo URLs from the gallery."""
        urls = set()

        # Try multiple selector strategies for EstateSales.NET
        selectors = [
            "img.gallery-image",
            ".photo-gallery img",
            ".sale-photos img",
            '[data-gallery] img',
            ".swiper-slide img",
            ".photo-grid img",
        ]

        for selector in selectors:
            try:
                images = page.locator(selector)
                count = await images.count()
                for i in range(count):
                    el = images.nth(i)
                    # Try src, then data-src for lazy-loaded images
                    src = await el.get_attribute("src")
                    if not src or "placeholder" in src or "loading" in src:
                        src = await el.get_attribute("data-src")
                    if not src:
                        src = await el.get_attribute("data-lazy-src")

                    if src and src.startswith("http"):
                        # Upgrade to full-size image if it's a thumbnail
                        src = self._get_full_size_url(src)
                        urls.add(src)
            except Exception:
                continue

        # If gallery selectors failed, fall back to any large images
        if not urls:
            try:
                all_imgs = page.locator("img")
                count = await all_imgs.count()
                for i in range(count):
                    el = all_imgs.nth(i)
                    src = await el.get_attribute("src")
                    if src and src.startswith("http"):
                        # Filter out small icons/logos
                        width = await el.get_attribute("width")
                        if width and int(width) < 100:
                            continue
                        urls.add(src)
            except Exception:
                pass

        return list(urls)

    def _get_full_size_url(self, url: str) -> str:
        """Convert thumbnail URL to full-size image URL."""
        # EstateSales.NET uses CDN URLs with size parameters
        # Replace common thumbnail patterns
        url = re.sub(r"/thumbs/", "/photos/", url)
        url = re.sub(r"_thumb\.", ".", url)
        url = re.sub(r"\?.*$", "", url)  # Remove query params that might limit size
        return url
