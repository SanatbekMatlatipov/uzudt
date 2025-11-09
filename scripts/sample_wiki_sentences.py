"""
sample_wiki_sentences.py

Phase 5 helper: sample sentences from Uzbek Wikipedia by category.

Inputs:
  - data/wiki/extracted/**.json        (WikiExtractor --json output)
  - data/wiki/metadata/category_to_articles.json

Outputs:
  - data/wiki/sentences/<category_slug>.txt   (one sentence per line)
  - data/raw/uz_sentences.txt                 (all sampled sentences concatenated)

Configuration:
  - TARGET_CATEGORIES: list of category names to sample from.
  - SENTENCES_PER_CATEGORY: how many sentences per category.
"""

import json
import random
import re
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

# Adjust this list after inspecting data/wiki/metadata/category_stats.tsv
TARGET_CATEGORIES = [
    "ADOLAT SOTSIAL-DEMOKRATIK PARTIYASI",        # Example: "Tarix"
    "OʻZBEKISTON XALQ BIRLIGI JAMOATCHILIK HARAKATI",        # Example: "Sport"
    "OʻZBEKISTON TARIXI",          # Example: "Fan"
    "BUYUK IPAK YOʻLI",     # Example: "Adabiyot"
    "TURKIY TILLAR",    # Example: "Madaniyat"
    "TARIX",  # Example: "Texnologiya"
    "BOLALAR ADABIYOTI"
]

SENTENCES_PER_CATEGORY = 20

# Sentence length constraints (you can tweak):
MIN_TOKENS = 5      # avoid too short fragments
MAX_TOKENS = 35     # avoid super long monsters

# Directories
EXTRACTED_DIR = Path("data/wiki/extracted")  # WikiExtractor --json output
META_DIR = Path("data/wiki/metadata")
OUT_SENT_DIR = Path("data/wiki/sentences")
RAW_DIR = Path("data/raw")

CATEGORY_TO_ARTICLES_JSON = META_DIR / "category_to_articles.json"


# ---------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------

def slugify_category(name: str) -> str:
    """
    Convert category name to a filename-friendly slug:
      "Oʻzbekiston tarixi" -> "ozbekiston_tarixi"
    """
    name = name.strip().lower()
    # Replace spaces with underscores
    name = re.sub(r"\s+", "_", name)
    # Remove/normalize non-alphanumeric/underscore
    name = re.sub(r"[^a-z0-9_ʻ’'əöüğşıçāīū\-]+", "", name)
    if not name:
        name = "category"
    return name


def split_into_sentences(text: str) -> list[str]:
    """
    Very simple sentence splitter based on punctuation.
    This is language-agnostic and not perfect, but OK for sampling.
    """
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    # Split on ., ?, ! (keep punctuation attached)
    parts = re.split(r"(?<=[\.\?\!])\s+", text)
    # Clean up parts
    sentences = [p.strip() for p in parts if p.strip()]
    return sentences


def sentence_ok(sent: str) -> bool:
    tokens = sent.split()
    n = len(tokens)
    if n < MIN_TOKENS or n > MAX_TOKENS:
        return False
    # Skip if mostly punctuation or weird
    if re.match(r"^[\.\,\!\?\:\;\-\(\)]+$", sent):
        return False
    return True


# ---------------------------------------------------------------------
# MAIN LOGIC
# ---------------------------------------------------------------------

def load_category_to_articles():
    if not CATEGORY_TO_ARTICLES_JSON.exists():
        raise FileNotFoundError(f"Missing {CATEGORY_TO_ARTICLES_JSON}. "
                                f"Run build_wiki_metadata.py first.")
    with CATEGORY_TO_ARTICLES_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def build_title_to_categories(cat_to_articles: dict[str, list[str]],
                              target_categories: list[str]):
    """
    Create mapping: title -> set of target categories it belongs to.
    """
    title_to_cats: dict[str, set[str]] = defaultdict(set)
    for cat in target_categories:
        articles = cat_to_articles.get(cat, [])
        for title in articles:
            title_to_cats[title].add(cat)
    return title_to_cats


def sample_sentences():
    random.seed(42)  # reproducibility

    OUT_SENT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Load category → [article_titles]
    print("[5.1] Loading category_to_articles.json ...")
    cat_to_articles = load_category_to_articles()

    # 2) Build title → {categories} mapping for our target categories
    print("[5.2] Building title → categories mapping for target categories ...")
    title_to_cats = build_title_to_categories(cat_to_articles, TARGET_CATEGORIES)

    # Track sentences we collect
    cat_sentences: dict[str, list[str]] = {cat: [] for cat in TARGET_CATEGORIES}

    # Helper to see if we're done
    def all_done():
        return all(len(cat_sentences[cat]) >= SENTENCES_PER_CATEGORY
                   for cat in TARGET_CATEGORIES)

    # 3) Iterate over extracted JSON articles
    print("[5.3] Scanning WikiExtractor JSON files ...")

    # WikiExtractor with --json writes files named wiki_00, wiki_01, ... with NO extension.
    # So we look for any files starting with "wiki_" under data/wiki/extracted/**.
    json_files = [p for p in EXTRACTED_DIR.rglob("wiki_*") if p.is_file()]

    if not json_files:
        raise FileNotFoundError(
            f"No WikiExtractor output files found under {EXTRACTED_DIR}. "
            f"Expected files like AA/wiki_00, AB/wiki_01, etc."
        )

    processed_articles = 0

    for jf in json_files:
        with jf.open(encoding="utf-8") as f:
            for line in f:
                try:
                    art = json.loads(line)
                except json.JSONDecodeError:
                    continue

                title = art.get("title")
                text = art.get("text") or ""
                if not title or not text:
                    continue

                # Only interested in articles whose title is in our mapping
                cats_for_title = title_to_cats.get(title)
                if not cats_for_title:
                    continue

                processed_articles += 1
                if processed_articles % 500 == 0:
                    print(f"    Processed {processed_articles} matching articles so far...")

                # Split and filter sentences
                sentences = split_into_sentences(text)
                for sent in sentences:
                    if not sentence_ok(sent):
                        continue

                    for cat in cats_for_title:
                        if len(cat_sentences[cat]) < SENTENCES_PER_CATEGORY:
                            cat_sentences[cat].append(sent)

                if all_done():
                    break  # stop reading this file
        if all_done():
            break  # stop scanning files

    # Report summary
    print("\n[5.4] Sampling summary:")
    for cat in TARGET_CATEGORIES:
        print(f"  {cat}: {len(cat_sentences[cat])} sentences collected "
              f"(target: {SENTENCES_PER_CATEGORY})")

    # 4) Write per-category files
    print("\n[5.5] Writing per-category sentence files ...")
    all_sentences = []
    for cat in TARGET_CATEGORIES:
        slug = slugify_category(cat)
        out_path = OUT_SENT_DIR / f"{slug}.txt"
        sentences = cat_sentences[cat]
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for s in sentences:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
        sentences = deduped

        with out_path.open("w", encoding="utf-8") as f:
            for s in sentences:
                f.write(s + "\n")

        all_sentences.extend(sentences)
        print(f"  Wrote {len(sentences)} sentences to {out_path}")

    # 5) Write combined file for LLM annotation
    combined_path = RAW_DIR / "uz_sentences.txt"
    with combined_path.open("w", encoding="utf-8") as f:
        for s in all_sentences:
            f.write(s + "\n")

    print(f"\n[5.6] Wrote combined {len(all_sentences)} sentences to {combined_path}")
    print("[Phase 5] Done.")


if __name__ == "__main__":
    sample_sentences()
