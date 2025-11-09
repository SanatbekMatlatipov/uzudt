from typing import List, Dict, Any


def tokens_to_conllu(tokens: List[Dict[str, Any]]) -> str:
    """
    Convert a list of token dicts (from LLM) into a single-sentence CoNLL-U string.

    Expected keys per token:
      "ID" (int)
      "FORM" (str)
      "LEMMA" (str)
      "UPOS" (str)
      "HEAD ID" (int)
      "HEAD" (str)        # not used in CoNLL-U, but useful for debugging
      "DEPREL" (str)

    We fill unused CoNLL-U columns with "_":
      ID  FORM  LEMMA  UPOS  XPOS  FEATS  HEAD  DEPREL  DEPS  MISC
    """
    lines: List[str] = []

    for t in tokens:
        # Basic sanity
        if "ID" not in t or "FORM" not in t:
            raise ValueError(f"Token missing ID or FORM: {t}")

        tid = int(t["ID"])
        form = str(t["FORM"])

        lemma = str(t.get("LEMMA", form.lower()))
        upos = str(t.get("UPOS", "X"))
        xpos = "_"  # not used for now
        feats = "_"

        head_id = int(t.get("HEAD ID", 0))
        deprel = str(t.get("DEPREL", "dep"))
        deps = "_"
        misc = "_"

        line = "\t".join(
            [
                str(tid),
                form,
                lemma,
                upos,
                xpos,
                feats,
                str(head_id),
                deprel,
                deps,
                misc,
            ]
        )
        lines.append(line)

    return "\n".join(lines) + "\n"
