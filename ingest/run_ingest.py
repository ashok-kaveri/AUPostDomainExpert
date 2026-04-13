from __future__ import annotations
#!/usr/bin/env python3
"""
Master ingestion pipeline.
Clears the knowledge base and rebuilds it from all configured sources.

Usage:
    python ingest/run_ingest.py                    # Ingest all sources
    python ingest/run_ingest.py --sources codebase # Only index codebase
    python ingest/run_ingest.py --sources pluginhive_seeds sheets
"""
import argparse
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


_DEFAULT_SOURCES = ["pluginhive_docs", "pluginhive_seeds", "sheets", "codebase", "wiki"]
# pluginhive_docs  — Official PluginHive AU Post app setup guide (product docs, UX flows, FAQ)
# pluginhive_seeds — Seed URL scrape of AU Post knowledge base and guide pages
# sheets           — eParcel + MyPost Business test cases (Google Sheets)
# codebase         — Playwright TypeScript automation codebase
# wiki             — Internal AU Post wiki markdown knowledge base
# pluginhive       — Full PluginHive web scrape (excluded by default — large)
# shopify          — Shopify App Store listing


def run_ingest(sources: list[str] | None = None) -> None:
    from rag.vectorstore import clear_collection, add_documents
    from ingest.web_scraper import scrape_pluginhive_docs, scrape_pluginhive_seeds_only, scrape_shopify_app_store
    from ingest.codebase_loader import load_codebase
    from ingest.sheets_loader import load_test_cases
    from ingest.pdf_loader import load_pdf_test_cases
    from ingest.pluginhive_app_docs import load_pluginhive_app_docs
    from ingest.wiki_loader import load_wiki_docs

    active_sources = sources if sources is not None else _DEFAULT_SOURCES
    start = time.time()

    print("=" * 60)
    print("AU Post Domain Expert — Knowledge Base Ingestion")
    print(f"Sources: {', '.join(active_sources)}")
    print("=" * 60)
    logger.info("Clearing existing knowledge base...")
    clear_collection()

    all_documents = []

    if "pluginhive" in active_sources:
        all_documents.extend(scrape_pluginhive_docs())

    if "shopify" in active_sources:
        all_documents.extend(scrape_shopify_app_store())

    if "pluginhive_docs" in active_sources:
        logger.info("Loading PluginHive official AU Post app documentation…")
        all_documents.extend(load_pluginhive_app_docs())

    if "pluginhive_seeds" in active_sources:
        logger.info("Scraping PluginHive seed URLs (knowledge base, guides)…")
        all_documents.extend(scrape_pluginhive_seeds_only())

    if "codebase" in active_sources:
        all_documents.extend(load_codebase())

    if "sheets" in active_sources:
        logger.info("Loading AU Post test cases (eParcel + MyPost Business sheets)…")
        all_documents.extend(load_test_cases())

    if "pdf" in active_sources:
        all_documents.extend(load_pdf_test_cases())

    if "wiki" in active_sources:
        logger.info("Loading internal AU Post wiki documentation…")
        all_documents.extend(load_wiki_docs())

    if not all_documents:
        logger.error("No documents loaded. Check your sources and try again.")
        sys.exit(1)

    logger.info("Embedding and storing %d chunks in ChromaDB...", len(all_documents))
    add_documents(all_documents)

    elapsed = time.time() - start
    print(f"\n✅ Done: {len(all_documents)} chunks indexed in {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rebuild AU Post Domain Expert knowledge base")
    parser.add_argument(
        "--sources",
        nargs="*",
        choices=["pluginhive", "pluginhive_seeds", "shopify", "pluginhive_docs", "codebase", "sheets", "pdf", "wiki"],
        help="Which sources to ingest (default: all)",
    )
    args = parser.parse_args()
    run_ingest(args.sources)
