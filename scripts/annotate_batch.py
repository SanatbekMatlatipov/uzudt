"""
annotate_batch.py

Run Phase 6 annotation pipeline, with resume support:

- Reads sentences from data/raw/uz_sentences.txt
- Infers how many have already been annotated from data/gold/uzudt_auto.conllu
- Starts from the next sentence (or from --start-from if given)
- For each sentence:
    * call GPT-5-mini (or chosen model) with Uzbek UD prompt
    * get JSON token list
    * convert to CoNLL-U
    * validate with UD validate.py
    * if valid: append to data/gold/uzudt_auto.conllu
    * if invalid or exception: log and STOP (no further sentences)

You can then fix the problem (prompt / code) and rerun; the script
will resume from the first sentence that is not yet in the gold file,
or from a custom --start-from if you wish.
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Optional

# --- ensure project root is on sys.path ---
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from uzudt.openai_client import annotate_sentence_with_llm
from uzudt.annotator import tokens_to_conllu
from uzudt.validator import validate_conllu

# If you use .env with OPENAI_API_KEY, uncomment these two lines:
# from dotenv import load_dotenv
# load_dotenv()

RAW_SENTENCES = REPO_ROOT / "data" / "raw" / "uz_sentences.txt"
GOLD_PATH = REPO_ROOT / "data" / "gold" / "uzudt_auto.conllu"
LOG_DIR = REPO_ROOT / "data" / "logs"

def ensure_dirs():
    GOLD_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def read_sentences(path: Path):
    text = path.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def get_last_processed_index() -> int:
    """
    Look into data/gold/uzudt_auto.conllu and find the maximum auto-N in lines like:
      # sent_id = auto-7

    Returns:
      0 if file does not exist or no such lines,
      max_N otherwise.
    """
    if not GOLD_PATH.exists():
        return 0

    last = 0
    with GOLD_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# sent_id = auto-"):
                try:
                    n_str = line.split("auto-")[-1]
                    n = int(n_str)
                    if n > last:
                        last = n
                except ValueError:
                    continue
    return last


def annotate_one_sentence(
    sentence: str,
    idx: int,
    model: Optional[str] = None,
):
    """
    Annotate a single sentence and return:
       ok, conllu_str, tokens_json, validate_log
    """
    tokens = annotate_sentence_with_llm(
        sentence,
        model=model or "gpt-5-mini",
        prompt_path=REPO_ROOT / "prompts" / "uz_prompt.txt",
    )

    conllu_str = tokens_to_conllu(tokens)
    ok, log = validate_conllu(conllu_str, lang="uz", level=2)

    return ok, conllu_str, tokens, log


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--start-from",
        type=int,
        default=None,
        help=(
            "1-based index of sentence in uz_sentences.txt to start from. "
            "If not given, it is inferred from uzudt_auto.conllu (last auto-N + 1)."
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5-mini",
        help="OpenAI model name to use (default: gpt-5-mini).",
    )
    args = parser.parse_args()

    ensure_dirs()

    if not RAW_SENTENCES.exists():
        raise FileNotFoundError(
            f"Missing {RAW_SENTENCES}. Make sure Phase 5 created uz_sentences.txt."
        )

    sentences = read_sentences(RAW_SENTENCES)
    total = len(sentences)

    # Determine starting index
    inferred_start = get_last_processed_index() + 1
    start_from = args.start_from if args.start_from is not None else inferred_start

    if start_from < 1:
        start_from = 1
    if start_from > total:
        print(
            f"Nothing to do: start_from={start_from} > total sentences={total}. "
            f"Check uz_sentences.txt and uzudt_auto.conllu."
        )
        return

    print(f"Total sentences in {RAW_SENTENCES}: {total}")
    print(f"Last processed (from gold): {inferred_start - 1}")
    print(f"Starting from sentence index: {start_from}")
    print(f"Using model: {args.model}")
    print()

    # Open gold file in append mode
    with GOLD_PATH.open("a", encoding="utf-8") as gold_out:
        for i, sent in enumerate(sentences, start=1):
            if i < start_from:
                continue  # skip sentences already processed

            print(f"[{i}/{total}] {sent}")

            try:
                ok, conllu_str, tokens, v_log = annotate_one_sentence(
                    sent, i, model=args.model
                )
            except Exception as e:
                # Hard failure (API error, JSON parse, etc.) → log and STOP
                err_path = LOG_DIR / f"sentence_{i:04d}_exception.txt"
                err_path.write_text(
                    f"Sentence index: {i}\nSentence: {sent}\n\nError: {e}\n",
                    encoding="utf-8",
                )
                print(f"   ✗ EXCEPTION, logged to {err_path}")
                print("   Stopping so you can inspect and fix the problem.")
                break

            if ok:
                # Valid → append to gold
                gold_out.write(f"# sent_id = auto-{i}\n")
                gold_out.write(f"# text = {sent}\n")
                gold_out.write(conllu_str)
                gold_out.write("\n")
                print("   ✓ VALID")
            else:
                # Invalid → log and STOP
                base = LOG_DIR / f"sentence_{i:04d}"
                json_path = base.with_suffix(".json")
                conllu_path = base.with_suffix(".conllu")
                val_path = base.with_suffix(".val.log")

                json_path.write_text(
                    json.dumps(tokens, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                conllu_path.write_text(conllu_str, encoding="utf-8")
                val_path.write_text(v_log, encoding="utf-8")

                print(f"   ✗ INVALID, see:")
                print(f"       {json_path}")
                print(f"       {conllu_path}")
                print(f"       {val_path}")
                print("   Stopping so you can inspect and fix the problem.")
                break

    print("\nRun finished. If it stopped on a failing sentence,")
    print("fix the issue (prompt, code, etc.), then rerun this script.")
    print("It will resume from the first sentence that is not yet in the gold file,")
    print("or from --start-from if you specify it explicitly.")


if __name__ == "__main__":
    main()
