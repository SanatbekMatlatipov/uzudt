"""
download_uzwiki_dump.py

Downloads the latest Uzbek Wikipedia dump snapshot (2025-11-01)
for building the UzUDT dataset. It fetches:
  1. pages-articles.xml.bz2   → all article text
  2. page.sql.gz              → page ID ↔ title mapping
  3. categorylinks.sql.gz     → page ID ↔ category mapping

Usage:
    python scripts/download_uzwiki_dump.py
"""

import requests
from pathlib import Path

# Fixed snapshot for reproducibility
BASE_URL = "https://dumps.wikimedia.org/uzwiki/20251101"
FILES = [
    "uzwiki-20251101-pages-articles.xml.bz2",
    "uzwiki-20251101-page.sql.gz",
    "uzwiki-20251101-categorylinks.sql.gz",
]

def download_file(url: str, dest: Path):
    """Stream download a file with progress."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"✅ Already exists: {dest.name}")
        return

    print(f"⬇️  Downloading {url}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 8192
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = (downloaded / total) * 100
                    print(f"\r  {downloaded/1e6:6.1f} MB / {total/1e6:6.1f} MB  ({pct:5.1f}%)", end="")
        print()
    print(f"✅ Done: {dest.name}")

def main():
    repo_root = Path(__file__).resolve().parents[1]
    raw_dir = repo_root / "data" / "wiki" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for fname in FILES:
        url = f"{BASE_URL}/{fname}"
        dest = raw_dir / fname
        download_file(url, dest)

    print("\nAll downloads complete.")
    print(f"Files saved to: {raw_dir.resolve()}")

if __name__ == "__main__":
    main()