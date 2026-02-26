"""Scraper for EstateSales.ORG listings."""

import re
from datetime import datetime, timezone

from estate_pricer.config import ScraperConfig
from estate_pricer.scraper.base import BaseScraper, SaleData


class EstateSalesOrgScraper(BaseScraper):
    """Scraper for estatesales.org estate sale listings."""

    URL_PATTERN = re.compile(
        r"https?://(www\.)?estatesales\.org/estate-sales/\d+"
    )

    def __init__(self, config: ScraperConfig):
        super().__init__(config)

    @staticmethod
    def can_handle(url: str) -> bool:
        return bool(EstateSalesOrgScraper.URL_PATTERN.match(url))

    async def scrape(self, url: str) -> SaleData:
        """Scrape an EstateSales.ORG listing page."""
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

                title = await self._extract_text(page, "h1")
                location = await self._extract_text(page, ".sale-location, .location")
                company = await self._extract_text(page, ".company-name, .hosted-by")
                dates = await self._extract_dates(page)
                photo_urls = await self._extract_photo_urls(page)

            finally:
                await browser.close()

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
        try:
            el = page.locator(selector).first
            text = await el.text_content(timeout=5000)
            return text.strip() if text else ""
        except Exception:
            return ""

    async def _extract_dates(self, page) -> list[str]:
        dates = []
        try:
            date_els = page.locator(".sale-dates .date, .sale-date, time")
            count = await date_els.count()
            for i in range(count):
                text = await date_els.nth(i).text_content()
                if text:
                    dates.append(text.strip())
        except Exception:
            pass
        return dates

    async def _extract_photo_urls(self, page) -> list[str]:
        urls = set()
        selectors = [
            ".gallery img",
            ".photo-gallery img",
            ".sale-images img",
            ".carousel img",
        ]

        for selector in selectors:
            try:
                images = page.locator(selector)
                count = await images.count()
                for i in range(count):
                    el = images.nth(i)
                    src = await el.get_attribute("src")
                    if not src or "placeholder" in src:
                        src = await el.get_attribute("data-src")
                    if src and src.startswith("http"):
                        urls.add(src)
            except Exception:
                continue

        return list(urls)
