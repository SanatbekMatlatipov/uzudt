"""
build_wiki_metadata.py

Phase 4 — Category Metadata Parsing for Uzbek Wikipedia dump.

Inputs (from data/wiki/raw/):
  - uzwiki-20251101-page.sql.gz
  - uzwiki-20251101-categorylinks.sql.gz

Outputs (to data/wiki/metadata/):
  - page_map.json              : {page_id: title}
  - category_links.json        : {page_id: [categories]}
  - category_to_articles.json  : {category: [article_titles]}
  - category_stats.tsv         : category\tarticle_count

We only keep:
  - pages in namespace 0 (main articles)
  - categories as plain text (underscores → spaces, double quotes fixed)
"""

import gzip
import json
import re
from collections import defaultdict
from pathlib import Path


RAW_DIR = Path("data/wiki/raw")
META_DIR = Path("data/wiki/metadata")

PAGE_SQL = RAW_DIR / "uzwiki-20251101-page.sql.gz"
CAT_SQL = RAW_DIR / "uzwiki-20251101-categorylinks.sql.gz"

PAGE_MAP_JSON = META_DIR / "page_map.json"
CAT_LINKS_JSON = META_DIR / "category_links.json"
CAT_TO_ARTICLES_JSON = META_DIR / "category_to_articles.json"
CAT_STATS_TSV = META_DIR / "category_stats.tsv"


def parse_page_sql(path: Path) -> dict[int, str]:
    """
    Parse uzwiki-20251101-page.sql.gz and return {page_id: title}.

    - Uses a regex that captures: (page_id, namespace, title, ...)
    - Only keeps namespace = 0 (main article namespace).
    - Converts underscores in titles to spaces.
    """
    print(f"[4.1] Parsing page SQL: {path}")
    if not path.exists():
        raise FileNotFoundError(path)

    # Matches tuples like: (10,0,'Sun''iy_intellekt','',0,...)
    # Group 1: page_id, Group 2: namespace, Group 3: title
    tuple_re = re.compile(
        r"\((\d+),(\d+),'((?:[^']|'')*)',",
        re.UNICODE
    )

    page_map: dict[int, str] = {}

    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.startswith("INSERT INTO"):
                continue
            for m in tuple_re.finditer(line):
                page_id = int(m.group(1))
                namespace = int(m.group(2))
                raw_title = m.group(3)

                # Only main namespace (0)
                if namespace != 0:
                    continue

                # Unescape doubled single quotes and replace underscores with spaces
                title = raw_title.replace("''", "'").replace("_", " ")
                page_map[page_id] = title

    print(f"      Parsed {len(page_map):,} main-namespace pages.")
    return page_map


def parse_categorylinks_sql(path: Path) -> dict[int, list[str]]:
    """
    Parse uzwiki-20251101-categorylinks.sql.gz and return:
      {page_id: [categories]}

    - Uses regex to capture (cl_from, cl_to, ...).
    - Category names are stored without 'Category:' and use underscores.
    """
    print(f"[4.2] Parsing categorylinks SQL: {path}")
    if not path.exists():
        raise FileNotFoundError(path)

    # Matches tuples like:
    # (12345,'Tarixiy_shaxslar','Tarixiy shaxslar','2025-01-01 00:00:00',...)
    # Group 1: cl_from (page_id), Group 2: cl_to (category name)
    tuple_re = re.compile(
        r"\((\d+),'((?:[^']|'')*)',",
        re.UNICODE
    )

    cat_links: dict[int, list[str]] = defaultdict(list)

    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.startswith("INSERT INTO"):
                continue
            for m in tuple_re.finditer(line):
                page_id = int(m.group(1))
                raw_cat = m.group(2)

                # Unescape doubled single quotes and replace underscores with spaces
                cat_name = raw_cat.replace("''", "'").replace("_", " ")

                cat_links[page_id].append(cat_name)

    print(f"      Parsed categories for {len(cat_links):,} pages.")
    return cat_links


def build_category_to_articles(
    page_map: dict[int, str],
    cat_links: dict[int, list[str]]
) -> dict[str, list[str]]:
    """
    Join page_map and category_links to get:
      {category: [article_titles]}
    """
    print("[4.3] Building category → articles mapping...")
    category_to_articles: dict[str, list[str]] = defaultdict(list)

    missing_pages = 0
    for page_id, cats in cat_links.items():
        title = page_map.get(page_id)
        if not title:
            missing_pages += 1
            continue
        for cat in cats:
            category_to_articles[cat].append(title)

    print(f"      Categories found: {len(category_to_articles):,}")
    print(f"      Pages with categories but missing in page_map: {missing_pages:,}")
    return category_to_articles


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"      Wrote JSON: {path}")


def write_category_stats(path: Path, cat_to_articles: dict[str, list[str]]) -> None:
    """
    Write a TSV with category and article count, sorted by count descending.
    Also print top 20 to console to help manual selection (Phase 4.4).
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    items = sorted(
        ((cat, len(arts)) for cat, arts in cat_to_articles.items()),
        key=lambda x: x[1],
        reverse=True,
    )

    with path.open("w", encoding="utf-8") as f:
        f.write("category\tarticle_count\n")
        for cat, count in items:
            f.write(f"{cat}\t{count}\n")

    print(f"      Wrote category stats TSV: {path}")
    print("      Top 20 categories by article count:")
    for cat, count in items[:20]:
        print(f"        {count:5d}  {cat}")


def main():
    META_DIR.mkdir(parents=True, exist_ok=True)

    # 4.1: page_id → title
    page_map = parse_page_sql(PAGE_SQL)
    write_json(PAGE_MAP_JSON, page_map)

    # 4.2: page_id → [categories]
    cat_links = parse_categorylinks_sql(CAT_SQL)
    write_json(CAT_LINKS_JSON, cat_links)

    # 4.3: category → [article_titles]
    cat_to_articles = build_category_to_articles(page_map, cat_links)
    write_json(CAT_TO_ARTICLES_JSON, cat_to_articles)

    # Also: category_stats.tsv to support 4.4 (manual selection)
    write_category_stats(CAT_STATS_TSV, cat_to_articles)

    print("\n[Phase 4] Done.")
    print("You can now inspect:")
    print(f"  - {PAGE_MAP_JSON}")
    print(f"  - {CAT_LINKS_JSON}")
    print(f"  - {CAT_TO_ARTICLES_JSON}")
    print(f"  - {CAT_STATS_TSV}  (for choosing Tarix, Fan, Sport, etc.)")


if __name__ == "__main__":
    main()
