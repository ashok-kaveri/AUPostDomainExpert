from __future__ import annotations
import logging
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

logger = logging.getLogger(__name__)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 AUPostDomainExpert/1.0"})
    return session


def _fetch_page(url: str, session: requests.Session) -> BeautifulSoup | None:
    """Fetch a URL and return a BeautifulSoup object, or None on error."""
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def _extract_text(soup: BeautifulSoup) -> str:
    """Extract cleaned plain text from a BeautifulSoup object."""
    for tag in soup.find_all(["nav", "footer", "script", "style", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _extract_links(soup: BeautifulSoup, base_url: str, base_domain: str) -> list[str]:
    """Extract same-domain links from an already-fetched BeautifulSoup object."""
    links = []
    for a in soup.find_all("a", href=True):
        full = urljoin(base_url, a["href"]).split("?")[0].split("#")[0]
        if urlparse(full).netloc == base_domain:
            links.append(full)
    return list(set(links))


def _chunk_text(text: str, source_url: str, source_type: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )
    chunks = splitter.split_text(text)
    return [
        Document(
            page_content=chunk,
            metadata={
                "source": source_url,
                "source_url": source_url,
                "source_type": source_type,
                "chunk_index": i,
            },
        )
        for i, chunk in enumerate(chunks)
    ]


def _is_aupost_url(url: str) -> bool:
    """Return True only for PluginHive pages that are Australia Post-related."""
    lower = url.lower()
    return "australia-post" in lower or "aupost" in lower or "au-post" in lower


def scrape_pluginhive_docs() -> list[Document]:
    """Recursively crawl PluginHive AU Post docs and return chunked Documents.

    Seeds from PLUGINHIVE_SEED_URLS (guaranteed high-value pages) then expands
    BFS-style following AU Post-only links up to PLUGINHIVE_MAX_PAGES.
    """
    logger.info("Scraping PluginHive AU Post docs...")
    session = _make_session()
    base_domain = urlparse(config.PLUGINHIVE_BASE_URL).netloc
    visited: set[str] = set()

    seed_urls = list(dict.fromkeys(
        config.PLUGINHIVE_SEED_URLS + [config.PLUGINHIVE_BASE_URL]
    ))
    to_visit: deque = deque(seed_urls)
    documents: list[Document] = []
    max_pages = config.PLUGINHIVE_MAX_PAGES

    while to_visit:
        if len(visited) >= max_pages:
            logger.warning("Reached max page limit (%d) — stopping crawl", max_pages)
            break

        url = to_visit.popleft()
        if url in visited:
            continue
        visited.add(url)

        soup = _fetch_page(url, session)
        if soup is None:
            continue

        text = _extract_text(soup)
        if text and len(text) > 100:
            documents.extend(_chunk_text(text, url, "pluginhive_docs"))

        for link in _extract_links(soup, url, base_domain):
            if link not in visited and _is_aupost_url(link):
                to_visit.append(link)

        time.sleep(0.5)

    logger.info("PluginHive: %d chunks from %d pages", len(documents), len(visited))
    return documents


def scrape_pluginhive_seeds_only() -> list[Document]:
    """Scrape only the pre-configured PLUGINHIVE_SEED_URLS — no BFS expansion.

    Recommended default source: covers all configured high-value PluginHive AU Post
    pages (knowledge base, guides) in seconds without crawling thousands of pages.
    """
    logger.info(
        "Scraping PluginHive seed URLs only (%d pages)…",
        len(config.PLUGINHIVE_SEED_URLS),
    )
    session = _make_session()
    documents: list[Document] = []

    for url in config.PLUGINHIVE_SEED_URLS:
        soup = _fetch_page(url, session)
        if soup is None:
            continue
        text = _extract_text(soup)
        if text and len(text) > 100:
            documents.extend(_chunk_text(text, url, "pluginhive_seeds"))
        time.sleep(0.3)

    logger.info(
        "PluginHive seeds: %d chunks from %d seed URLs",
        len(documents),
        len(config.PLUGINHIVE_SEED_URLS),
    )
    return documents


def scrape_shopify_app_store() -> list[Document]:
    """Scrape the Shopify App Store listing for the AU Post app."""
    logger.info("Scraping Shopify App Store listing...")
    session = _make_session()
    url = config.SHOPIFY_APP_STORE_URL
    soup = _fetch_page(url, session)
    if soup is None:
        return []
    text = _extract_text(soup)
    documents = _chunk_text(text, url, "shopify_app_store") if text and len(text) > 100 else []
    logger.info("Shopify App Store: %d chunks", len(documents))
    return documents
