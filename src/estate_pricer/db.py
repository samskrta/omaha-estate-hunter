"""SQLite database setup and query helpers."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sales (
    sale_id TEXT PRIMARY KEY,
    source_url TEXT NOT NULL,
    title TEXT,
    location TEXT,
    sale_dates TEXT,
    company_name TEXT,
    scraped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS photos (
    photo_id TEXT PRIMARY KEY,
    sale_id TEXT NOT NULL REFERENCES sales(sale_id),
    source_url TEXT NOT NULL,
    local_path TEXT,
    caption TEXT,
    download_status TEXT NOT NULL,
    analyzed_at TEXT
);

CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    photo_id TEXT NOT NULL REFERENCES photos(photo_id),
    sale_id TEXT NOT NULL REFERENCES sales(sale_id),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    era TEXT,
    condition_estimate TEXT,
    notable_features TEXT,
    search_query TEXT NOT NULL,
    confidence TEXT NOT NULL,
    confidence_reasoning TEXT,
    estimated_value_hint TEXT,
    identified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pricing (
    pricing_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(item_id),
    search_query_used TEXT NOT NULL,
    results_count INTEGER,
    price_low REAL,
    price_median REAL,
    price_high REAL,
    price_average REAL,
    pricing_confidence TEXT,
    recent_sales TEXT,
    queried_at TEXT NOT NULL
);
"""


class Database:
    """SQLite database wrapper for estate pricer data."""

    def __init__(self, db_path: str = "./data/estate_pricer.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_sale(self, sale_data: dict):
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO sales
                   (sale_id, source_url, title, location, sale_dates, company_name, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    sale_data["sale_id"],
                    sale_data["source_url"],
                    sale_data.get("title"),
                    sale_data.get("location"),
                    json.dumps(sale_data.get("sale_dates", [])),
                    sale_data.get("company_name"),
                    sale_data["scraped_at"],
                ),
            )

    def save_photo(self, photo_data: dict):
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO photos
                   (photo_id, sale_id, source_url, local_path, caption, download_status, analyzed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    photo_data["photo_id"],
                    photo_data["sale_id"],
                    photo_data["source_url"],
                    photo_data.get("local_path"),
                    photo_data.get("caption"),
                    photo_data["download_status"],
                    photo_data.get("analyzed_at"),
                ),
            )

    def save_item(self, item_data: dict):
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO items
                   (item_id, photo_id, sale_id, name, category, brand, model, era,
                    condition_estimate, notable_features, search_query, confidence,
                    confidence_reasoning, estimated_value_hint, identified_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item_data["item_id"],
                    item_data["photo_id"],
                    item_data["sale_id"],
                    item_data["name"],
                    item_data["category"],
                    item_data.get("brand"),
                    item_data.get("model"),
                    item_data.get("era"),
                    item_data.get("condition_estimate"),
                    json.dumps(item_data.get("notable_features", [])),
                    item_data["search_query"],
                    item_data["confidence"],
                    item_data.get("confidence_reasoning"),
                    item_data.get("estimated_value_hint"),
                    item_data["identified_at"],
                ),
            )

    def save_pricing(self, pricing_data: dict):
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO pricing
                   (pricing_id, item_id, search_query_used, results_count,
                    price_low, price_median, price_high, price_average,
                    pricing_confidence, recent_sales, queried_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pricing_data["pricing_id"],
                    pricing_data["item_id"],
                    pricing_data["search_query_used"],
                    pricing_data.get("results_count"),
                    pricing_data.get("price_low"),
                    pricing_data.get("price_median"),
                    pricing_data.get("price_high"),
                    pricing_data.get("price_average"),
                    pricing_data.get("pricing_confidence"),
                    json.dumps(pricing_data.get("recent_sales", [])),
                    pricing_data["queried_at"],
                ),
            )

    def get_sale(self, sale_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM sales WHERE sale_id = ?", (sale_id,)
            ).fetchone()
            if row:
                result = dict(row)
                result["sale_dates"] = json.loads(result["sale_dates"] or "[]")
                return result
        return None

    def get_items_for_sale(self, sale_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM items WHERE sale_id = ? ORDER BY confidence DESC, name",
                (sale_id,),
            ).fetchall()
            items = []
            for row in rows:
                item = dict(row)
                item["notable_features"] = json.loads(item["notable_features"] or "[]")
                items.append(item)
            return items

    def get_pricing_for_item(self, item_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM pricing WHERE item_id = ? ORDER BY queried_at DESC LIMIT 1",
                (item_id,),
            ).fetchone()
            if row:
                result = dict(row)
                result["recent_sales"] = json.loads(result["recent_sales"] or "[]")
                return result
        return None

    def get_all_pricing_for_sale(self, sale_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT p.* FROM pricing p
                   JOIN items i ON p.item_id = i.item_id
                   WHERE i.sale_id = ?
                   ORDER BY p.price_median DESC NULLS LAST""",
                (sale_id,),
            ).fetchall()
            results = []
            for row in rows:
                result = dict(row)
                result["recent_sales"] = json.loads(result["recent_sales"] or "[]")
                results.append(result)
            return results

    def get_cached_pricing(self, search_query: str, max_age_days: int = 7) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                """SELECT * FROM pricing
                   WHERE search_query_used = ?
                   AND julianday('now') - julianday(queried_at) <= ?
                   ORDER BY queried_at DESC LIMIT 1""",
                (search_query, max_age_days),
            ).fetchone()
            if row:
                result = dict(row)
                result["recent_sales"] = json.loads(result["recent_sales"] or "[]")
                return result
        return None
