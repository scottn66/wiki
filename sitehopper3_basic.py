#!/usr/bin/env python3
"""siteHopper3 basic script.

A minimal, readable version of the core refactor ideas:
- canonical Wikipedia keys
- SQLite-backed page + edge cache
- real or fake scraper
- bounded crawl
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import random
import sqlite3
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

WIKI_BASE_URL = "https://en.wikipedia.org"
WIKI_PATH_PREFIX = "/wiki/"


def utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonicalize_page_key(page: str) -> str:
    """Normalize input into a canonical page key, e.g. 'Artificial_intelligence'."""
    if page is None:
        raise ValueError("page cannot be None")
    s = str(page).strip()
    if not s:
        raise ValueError("page cannot be empty")

    if s.startswith("http://") or s.startswith("https://"):
        path = urlparse(s).path
    else:
        path = s

    path = path.split("#", 1)[0].split("?", 1)[0]
    if path.startswith(WIKI_PATH_PREFIX):
        key = path[len(WIKI_PATH_PREFIX) :]
    else:
        key = path

    return unquote(key).replace(" ", "_").strip("/")


def wiki_url(page_key: str, base_url: str = WIKI_BASE_URL) -> str:
    return f"{base_url}{WIKI_PATH_PREFIX}{canonicalize_page_key(page_key)}"


def pretty_title(page_key: str) -> str:
    return canonicalize_page_key(page_key).replace("_", " ")


@dataclass(frozen=True)
class PageRecord:
    page: str
    url: str
    content: str
    status_code: int
    fetched_at: str


class SimpleWikiStore:
    """Small SQLite store for pages (nodes) and links (edges)."""

    def __init__(self, db_path: str = "sitehopper_basic.db", base_url: str = WIKI_BASE_URL):
        self.db_path = db_path
        self.base_url = base_url
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pages (
                page TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                content TEXT,
                status_code INTEGER,
                fetched_at TEXT
            );

            CREATE TABLE IF NOT EXISTS edges (
                src_page TEXT NOT NULL,
                dst_page TEXT NOT NULL,
                PRIMARY KEY (src_page, dst_page),
                FOREIGN KEY (src_page) REFERENCES pages(page),
                FOREIGN KEY (dst_page) REFERENCES pages(page)
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def counts(self) -> dict[str, int]:
        cur = self.conn.cursor()
        pages = cur.execute("SELECT COUNT(*) AS n FROM pages").fetchone()["n"]
        edges = cur.execute("SELECT COUNT(*) AS n FROM edges").fetchone()["n"]
        return {"pages": int(pages), "edges": int(edges)}

    def get_page(self, page: str) -> Optional[sqlite3.Row]:
        key = canonicalize_page_key(page)
        return self.conn.execute("SELECT * FROM pages WHERE page = ?", (key,)).fetchone()

    def neighbors(self, page: str, limit: Optional[int] = None) -> list[str]:
        key = canonicalize_page_key(page)
        sql = """
            SELECT dst_page
            FROM edges
            WHERE src_page = ?
            ORDER BY dst_page
        """
        params: Sequence[object]
        if limit is None:
            params = (key,)
        else:
            sql += " LIMIT ?"
            params = (key, int(limit))
        rows = self.conn.execute(sql, params).fetchall()
        return [r["dst_page"] for r in rows]

    def upsert_page(self, record: PageRecord) -> None:
        self.conn.execute(
            """
            INSERT INTO pages(page, url, content, status_code, fetched_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(page) DO UPDATE SET
                url = excluded.url,
                content = excluded.content,
                status_code = excluded.status_code,
                fetched_at = excluded.fetched_at
            """,
            (record.page, record.url, record.content, record.status_code, record.fetched_at),
        )

    def ensure_placeholder_pages(self, keys: Iterable[str]) -> None:
        rows = []
        for key in keys:
            norm = canonicalize_page_key(key)
            rows.append((norm, wiki_url(norm, self.base_url)))
        self.conn.executemany(
            "INSERT OR IGNORE INTO pages(page, url) VALUES(?, ?)",
            rows,
        )

    def upsert_edges(self, src_page: str, dst_pages: Iterable[str]) -> None:
        src = canonicalize_page_key(src_page)
        dst_list = [canonicalize_page_key(d) for d in dst_pages]
        self.ensure_placeholder_pages([src, *dst_list])
        self.conn.executemany(
            "INSERT OR IGNORE INTO edges(src_page, dst_page) VALUES(?, ?)",
            [(src, d) for d in dst_list],
        )

    def write_page_and_edges(self, record: PageRecord, outlinks: Iterable[str]) -> None:
        self.upsert_page(record)
        self.upsert_edges(record.page, outlinks)
        self.conn.commit()


class WikipediaScraper:
    """Real Wikipedia fetcher."""

    def __init__(self, base_url: str = WIKI_BASE_URL, timeout: int = 15):
        self.base_url = base_url
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (siteHopper basic crawler)"
        }

    def _clean_outlinks(self, hrefs: Iterable[str]) -> list[str]:
        out: list[str] = []
        for href in hrefs:
            if not href or not href.startswith("/wiki/"):
                continue
            href = href.split("#", 1)[0].split("?", 1)[0]
            # Skip namespaces like File:, Category:, Help:
            if ":" in href[len("/wiki/") :]:
                continue
            out.append(canonicalize_page_key(href))
        return list(dict.fromkeys(out))

    def fetch_page(self, page: str) -> tuple[str, list[str], int]:
        key = canonicalize_page_key(page)
        url = wiki_url(key, self.base_url)
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        status = int(response.status_code)
        if status != 200:
            return "", [], status

        soup = BeautifulSoup(response.content, "html.parser")

        hrefs = [a.get("href") for a in soup.find_all("a", href=True)]
        outlinks = self._clean_outlinks(hrefs)

        # Remove noisy blocks before collecting paragraph text.
        for element in soup(["table", "ul", "ol", "dl", "sup", "span"]):
            element.decompose()
        body = soup.find("div", {"id": "bodyContent"})
        if body:
            content = " ".join(p.get_text(" ", strip=True) for p in body.find_all("p"))
        else:
            content = ""

        return content, outlinks, status


class FakeWikipediaScraper:
    """Deterministic offline scraper for quick testing."""

    def __init__(self, n_pages: int = 5000, out_degree: int = 10, seed: int = 7):
        self.n_pages = int(n_pages)
        self.out_degree = int(out_degree)
        self.seed = int(seed)
        self.vocab = [f"w{i}" for i in range(500)]

    def fetch_page(self, page: str) -> tuple[str, list[str], int]:
        key = canonicalize_page_key(page)
        h = int(hashlib.sha256((key + str(self.seed)).encode("utf-8")).hexdigest(), 16)
        rng = random.Random(h)
        content = " ".join(rng.choices(self.vocab, k=900))
        outlinks = [f"Page_{rng.randrange(self.n_pages)}" for _ in range(self.out_degree)]
        return content, list(dict.fromkeys(outlinks)), 200


def load_or_fetch_page(
    page: str,
    store: SimpleWikiStore,
    scraper: WikipediaScraper | FakeWikipediaScraper,
) -> tuple[str, list[str], int, bool]:
    """Return content/outlinks/status and whether it came from cache."""
    key = canonicalize_page_key(page)
    row = store.get_page(key)
    if row is not None and row["content"]:
        outlinks = store.neighbors(key)
        return str(row["content"]), outlinks, int(row["status_code"] or 200), True

    content, outlinks, status = scraper.fetch_page(key)
    record = PageRecord(
        page=key,
        url=wiki_url(key, store.base_url),
        content=content,
        status_code=status,
        fetched_at=utc_now_iso(),
    )
    store.write_page_and_edges(record, outlinks)
    return content, outlinks, status, False


def crawl(
    start_page: str,
    store: SimpleWikiStore,
    scraper: WikipediaScraper | FakeWikipediaScraper,
    depth: int = 2,
    max_connections: int = 8,
    seed: int = 0,
) -> dict[str, int | str]:
    """Simple bounded BFS crawl."""
    rng = random.Random(seed)
    start = canonicalize_page_key(start_page)
    visited: set[str] = set()
    frontier = [start]
    fetched = 0

    for _ in range(depth):
        next_frontier: list[str] = []
        for page in frontier:
            if page in visited:
                continue
            visited.add(page)
            _, outlinks, _, from_cache = load_or_fetch_page(page, store, scraper)
            if not from_cache:
                fetched += 1
            if len(outlinks) > max_connections:
                outlinks = rng.sample(outlinks, k=max_connections)
            next_frontier.extend(outlinks)
        frontier = next_frontier

    return {
        "start": start,
        "depth": depth,
        "visited_pages": len(visited),
        "fresh_fetches": fetched,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple siteHopper3 crawl demo")
    parser.add_argument("--mode", choices=["live", "fake"], default="fake")
    parser.add_argument("--start-page", default="Philosophy")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--max-connections", type=int, default=8)
    parser.add_argument("--db-path", default="sitehopper_basic.db")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--show-links", type=int, default=10)
    args = parser.parse_args()

    store = SimpleWikiStore(db_path=args.db_path)
    scraper: WikipediaScraper | FakeWikipediaScraper
    if args.mode == "live":
        scraper = WikipediaScraper()
    else:
        scraper = FakeWikipediaScraper(seed=args.seed)

    try:
        stats = crawl(
            start_page=args.start_page,
            store=store,
            scraper=scraper,
            depth=args.depth,
            max_connections=args.max_connections,
            seed=args.seed,
        )
        start_key = canonicalize_page_key(args.start_page)
        start_links = store.neighbors(start_key, limit=args.show_links)

        print("\n=== Crawl Summary ===")
        print(f"Mode: {args.mode}")
        print(f"Start key:   {start_key}")
        print(f"Start title: {pretty_title(start_key)}")
        print(f"Stats: {stats}")
        print(f"Store counts: {store.counts()}")

        print(f"\nTop {len(start_links)} outlinks from {pretty_title(start_key)}:")
        for i, key in enumerate(start_links, start=1):
            print(f"{i:>2}. {pretty_title(key)} ({key})")

        if args.mode == "live":
            print("\nTip: run again with the same db path to reuse cache.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
