"""
crawling.py:
===================
Web crawling and content extraction module.

Uses Trafilatura to fetch and clean web pages, extracting only the main
article content (removes menus, ads, footers). Results are stored in JSONL
format, preserving the URL-to-text mapping for downstream NER and KG building.

Used by:
  - scripts/run_crawling.py

Functions:
  - is_useful()           : filters out pages with fewer than 500 words
  - extract_main_content(): fetches a URL and extracts clean text
  - save_to_jsonl()       : appends a record to the JSONL output file
  - process_url()         : full pipeline for a single URL
"""

import trafilatura
import json


def is_useful(text, min_words=500):
    """Checks if the extracted text is useful based on a minimum word count."""
    if not text:
        return False
    return len(text.split()) >= min_words


def extract_main_content(url):
    """Fetches the URL and extracts the main content using trafilatura."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None

    return trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False
    )


def save_to_jsonl(url, text, output_file="data/raw/crawler_output.jsonl"):
    """Saves the URL and extracted text to a JSONL file."""
    record = {"url": url, "text": text}
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_url(url):
    """Processes a single URL: extracts content, checks usefulness, and saves if valid."""
    text = extract_main_content(url)

    if not is_useful(text):
        print(f"!!!! Ignored: {url}")
        return

    save_to_jsonl(url, text)
    print(f"✅ Saved: {url}")