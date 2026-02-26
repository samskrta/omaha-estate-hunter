"""eBay Browse API client for sold listing lookups."""

import time
from dataclasses import dataclass

import httpx

from estate_pricer.config import Config


EBAY_AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


@dataclass
class EbayToken:
    access_token: str
    expires_at: float  # Unix timestamp


class EbayClient:
    """Client for eBay Browse API sold listing searches."""

    def __init__(self, config: Config):
        self.config = config
        self._token: EbayToken | None = None
        self._http = httpx.Client(timeout=30)

    def _get_token(self) -> str:
        """Get or refresh OAuth client credentials token."""
        now = time.time()
        if self._token and self._token.expires_at > now + 60:
            return self._token.access_token

        response = self._http.post(
            EBAY_AUTH_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(self.config.ebay_client_id, self.config.ebay_client_secret),
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )
        response.raise_for_status()
        data = response.json()

        self._token = EbayToken(
            access_token=data["access_token"],
            expires_at=now + data.get("expires_in", 7200),
        )
        return self._token.access_token

    def search_sold(
        self,
        query: str,
        limit: int = 20,
        category_ids: list[str] | None = None,
    ) -> list[dict]:
        """Search eBay sold/completed listings.

        Args:
            query: Search query string.
            limit: Max number of results (up to 200).
            category_ids: Optional eBay category IDs to filter by.

        Returns:
            List of sold item dicts with title, price, date, condition, url, image.
        """
        token = self._get_token()

        params = {
            "q": query,
            "limit": str(min(limit, 200)),
            "sort": "newlyListed",
            "filter": "buyingOptions:{FIXED_PRICE|AUCTION},conditions:{NEW|USED|VERY_GOOD|GOOD|ACCEPTABLE}",
        }

        if category_ids:
            params["category_ids"] = ",".join(category_ids)

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "X-EBAY-C-ENDUSERCTX": "affiliateCampaignId=<default>",
        }

        response = self._http.get(
            EBAY_SEARCH_URL,
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        items = []
        for item_summary in data.get("itemSummaries", []):
            price_info = item_summary.get("price", {})
            image_info = item_summary.get("image", {})

            items.append({
                "title": item_summary.get("title", ""),
                "sold_price": float(price_info.get("value", 0)),
                "currency": price_info.get("currency", "USD"),
                "condition": item_summary.get("condition", "Not Specified"),
                "listing_url": item_summary.get("itemWebUrl", ""),
                "image_url": image_info.get("imageUrl"),
                "item_id": item_summary.get("itemId", ""),
            })

        return items

    def search_with_broadening(
        self,
        primary_query: str,
        brand: str | None = None,
        category: str | None = None,
        broadening_threshold: int = 3,
        limit: int = 20,
    ) -> tuple[list[dict], str]:
        """Search with automatic query broadening if results are insufficient.

        Tries the primary query first, then progressively broader queries.

        Args:
            primary_query: Primary search query from vision analysis.
            brand: Brand name for broadened searches.
            category: Category name for broadened searches.
            broadening_threshold: Min results before broadening.
            limit: Max results per query.

        Returns:
            Tuple of (results list, query that was used).
        """
        # Try primary query
        results = self.search_sold(primary_query, limit=limit)
        if len(results) >= broadening_threshold:
            return results, primary_query

        # Try brand + category if available
        if brand and category:
            broader_query = f"{brand} {category}"
            results = self.search_sold(broader_query, limit=limit)
            if len(results) >= broadening_threshold:
                return results, broader_query

        # Try just category keywords
        if category:
            # Extract key terms from primary query
            terms = primary_query.split()
            if len(terms) > 3:
                shorter_query = " ".join(terms[:3])
                results = self.search_sold(shorter_query, limit=limit)
                if results:
                    return results, shorter_query

        # Return whatever we have (possibly empty)
        return results, primary_query

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
