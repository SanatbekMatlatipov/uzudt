# 🧾 UzUDT Data Preparation — To-Do / Progress List

## 🟢 Phase 1 — Environment Setup
| Step | Description | Status | Output / Notes |
|------|--------------|--------|----------------|
| 1.1 | Create Python virtual environment (`.venv`) | ✅ Done | `.venv/` created in repo root |
| 1.2 | Activate venv & install dependencies (`requests`, `wikiextractor`, `openai`, `tqdm`) | ✅ Done | Verified with `pip list` |
| 1.3 | Add `requirements.txt` for reproducibility | ✅ Done | Contains four core packages |

---

## 🟢 Phase 2 — Wikipedia Dump Acquisition
| Step | Description | Status | Output / Notes |
|------|--------------|--------|----------------|
| 2.1 | Choose stable snapshot (`20251101`) for reproducibility | ✅ Done | Base URL: `https://dumps.wikimedia.org/uzwiki/20251101/` |
| 2.2 | Implement downloader script `scripts/download_uzwiki_dump.py` | ✅ Done | Uses `requests` with progress bar |
| 2.3 | Download dumps | ✅ Done | Files in `data/wiki/raw/`: <br>• `uzwiki-20251101-pages-articles.xml.bz2` (≈ 284 MB) <br>• `uzwiki-20251101-page.sql.gz` (≈ 33 MB) <br>• `uzwiki-20251101-categorylinks.sql.gz` (≈ 22 MB) |

---

## 🔵 Phase 3 — Wikipedia Text Extraction *(current stage)*
| Planned Step | Description | Expected Output |
|---------------|--------------|----------------|
| 3.1 | Use **WikiExtractor** to extract plain text (JSON mode) | Directory `data/wiki/extracted/AA`, `AB`, … |
| 3.2 | Verify random JSON files (each line = one article) | Each entry has keys `id`, `title`, `text` |
| 3.3 | Clean metadata (remove redirects, very short pages) | Filtered text corpus ready for sentence sampling |

---

## 🔵 Phase 4 — Category Metadata Parsing
| Planned Step | Description | Expected Output |
|---------------|--------------|----------------|
| 4.1 | Parse `page.sql.gz` → mapping `{page_id: title}` | `data/wiki/metadata/page_map.json` |
| 4.2 | Parse `categorylinks.sql.gz` → `{page_id: [categories]}` | `data/wiki/metadata/category_links.json` |
| 4.3 | Join both → `{category: [article_titles]}` | `data/wiki/metadata/category_to_articles.json` |
| 4.4 | Select 5–10 high-level categories (e.g., *Tarix*, *Fan*, *Sport*, *Adabiyot*, *Madaniyat*, *Texnologiya*) | Category list for sampling |

---

## 🟡 Phase 5 — Sentence Sampling
| Planned Step | Description | Expected Output |
|---------------|--------------|----------------|
| 5.1 | Split article text into sentences (regex or Uzbek segmenter) | Sentence lists per article |
| 5.2 | Randomly sample ≈ 20 sentences per selected category | `data/wiki/sentences/tarix.txt`, `sport.txt`, … |
| 5.3 | Store unified file `data/raw/uz_sentences.txt` (for LLM annotation) | 100 sentences total |
| 5.4 | Manual quality check (length balance, correctness) | Log with accepted / rejected samples |

---

## 🟣 Phase 6 — LLM Annotation Pipeline
| Planned Step | Description | Expected Output |
|---------------|--------------|----------------|
| 6.1 | Create `prompts/uz_prompt.txt` (Uzbek-specific UD rules) | Prompt file |
| 6.2 | Implement `openai_client.py` for GPT-5 / GPT-5-mini inference | JSON annotations |
| 6.3 | Convert JSON → CoNLL-U (`annotator.py`) | Temporary `.conllu` files |
| 6.4 | Validate via UD `validate.py` | Accepted / rejected logs |
| 6.5 | Append valid trees to `data/gold/uzudt_auto.conllu` | Verified dataset |
| 6.6 | Log failures under `data/logs/` | Error diagnostics for retraining |

---

## 🟣 Phase 7 — Iterative Improvement
| Planned Step | Description | Expected Output |
|---------------|--------------|----------------|
| 7.1 | Update `uz_prompt.txt` based on validation errors | Prompt versioning |
| 7.2 | Add reinforcement fine-tuning using **Agent-Lightning** | Model learning loop |
| 7.3 | Compare GPT-5 vs GPT-5-mini outputs | Quality report for paper |
