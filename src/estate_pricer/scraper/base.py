"""Abstract base class for estate sale scrapers."""

import asyncio
import hashlib
import random
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx

from estate_pricer.config import ScraperConfig


@dataclass
class PhotoData:
    photo_id: str
    source_url: str
    local_path: str = ""
    caption: str | None = None
    download_status: str = "pending"  # success | failed | skipped


@dataclass
class SaleData:
    sale_id: str
    source_url: str
    title: str = ""
    location: str = ""
    sale_dates: list[str] = field(default_factory=list)
    company_name: str | None = None
    photos: list[PhotoData] = field(default_factory=list)
    scraped_at: str = ""


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class BaseScraper(ABC):
    """Abstract base for estate sale site scrapers."""

    def __init__(self, config: ScraperConfig):
        self.config = config

    @staticmethod
    @abstractmethod
    def can_handle(url: str) -> bool:
        """Return True if this scraper can handle the given URL."""
        ...

    @abstractmethod
    async def scrape(self, url: str) -> SaleData:
        """Scrape a sale listing and return structured data.

        Must be implemented by subclasses. Should:
        1. Load the page and extract metadata
        2. Find all photo URLs
        3. Download photos to local storage
        4. Return SaleData with all info populated
        """
        ...

    def _generate_sale_id(self, url: str) -> str:
        """Generate a deterministic sale ID from the URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:12]

    def _get_download_dir(self, sale_id: str) -> Path:
        """Get the photo download directory for a sale."""
        path = Path(self.config.download_dir) / sale_id / "photos"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _random_user_agent(self) -> str:
        """Get a random user agent string."""
        return random.choice(USER_AGENTS)

    async def _random_delay(self):
        """Wait a random delay between requests."""
        delay = random.uniform(
            self.config.request_delay_min,
            self.config.request_delay_max,
        )
        await asyncio.sleep(delay)

    async def _download_photo(
        self,
        photo_url: str,
        save_dir: Path,
        index: int,
        caption: str | None = None,
    ) -> PhotoData:
        """Download a single photo with retry logic.

        Args:
            photo_url: URL of the photo to download.
            save_dir: Directory to save the photo in.
            index: Photo index for filename.
            caption: Optional caption text.

        Returns:
            PhotoData with download result.
        """
        photo_id = str(uuid.uuid5(uuid.NAMESPACE_URL, photo_url))
        ext = Path(photo_url.split("?")[0]).suffix or ".jpg"
        local_path = str(save_dir / f"photo_{index:03d}{ext}")

        for attempt in range(self.config.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.config.photo_timeout) as client:
                    resp = await client.get(
                        photo_url,
                        headers={"User-Agent": self._random_user_agent()},
                        follow_redirects=True,
                    )
                    resp.raise_for_status()

                    with open(local_path, "wb") as f:
                        f.write(resp.content)

                    return PhotoData(
                        photo_id=photo_id,
                        source_url=photo_url,
                        local_path=local_path,
                        caption=caption,
                        download_status="success",
                    )
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    await asyncio.sleep(wait)
                else:
                    return PhotoData(
                        photo_id=photo_id,
                        source_url=photo_url,
                        local_path="",
                        caption=caption,
                        download_status="failed",
                    )

    async def _download_photos(
        self,
        photo_urls: list[str | tuple[str, str | None]],
        save_dir: Path,
    ) -> list[PhotoData]:
        """Download multiple photos with delays.

        Args:
            photo_urls: List of URLs or (url, caption) tuples.
            save_dir: Directory to save photos in.

        Returns:
            List of PhotoData results.
        """
        photos = []
        for i, item in enumerate(photo_urls):
            if isinstance(item, tuple):
                url, caption = item
            else:
                url, caption = item, None

            photo = await self._download_photo(url, save_dir, i, caption)
            photos.append(photo)

            if i < len(photo_urls) - 1:
                await self._random_delay()

        return photos
