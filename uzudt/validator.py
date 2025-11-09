import subprocess
import tempfile
from pathlib import Path
from typing import Tuple


def get_validate_script_path() -> Path:
    """
    Return path to UD validate.py script.
    Adjust if your tools folder is different.
    """
    # Assume this file lives in uzudt/ and repo root is parents[1]
    repo_root = Path(__file__).resolve().parents[1]
    validate_py = repo_root / "tools" / "ud-tools" / "validate.py"
    if not validate_py.exists():
        raise FileNotFoundError(
            f"Could not find validate.py at {validate_py}. "
            f"Clone UD tools under tools/ud-tools/validate.py"
        )
    return validate_py


def validate_conllu(
    conllu_str: str,
    lang: str = "uz",
    level: int = 2,
) -> Tuple[bool, str]:
    """
    Run UD validate.py on a single-sentence CoNLL-U string.

    Returns: (ok, log)
      ok  : True if returncode == 0
      log : stdout + stderr from validate.py
    """
    validate_py = get_validate_script_path()

    with tempfile.NamedTemporaryFile(
        suffix=".conllu", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(conllu_str)
        tmp_path = Path(tmp.name)

    cmd = [
        "python",
        str(validate_py),
        f"--lang={lang}",
        f"--level={level}",
        str(tmp_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    ok = result.returncode == 0
    log = (result.stdout or "") + "\n" + (result.stderr or "")

    # You can delete tmp_path here if you want; leaving it is useful for debugging
    # tmp_path.unlink(missing_ok=True)

    return ok, log
