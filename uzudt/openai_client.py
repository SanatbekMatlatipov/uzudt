from pathlib import Path
import json
from typing import List, Dict, Any, Union

from openai import OpenAI

DEFAULT_MODEL = "gpt-5-mini"

def load_system_prompt(prompt_path: Union[Path, str] = "prompts/uz_prompt.txt") -> str:
    path = Path(prompt_path)
    return path.read_text(encoding="utf-8")

def annotate_sentence_with_llm(
    sentence: str,
    model: str = DEFAULT_MODEL,
    prompt_path: Union[Path, str] = "prompts/uz_prompt.txt",
) -> List[Dict[str, Any]]:
    """
    Call OpenAI Responses API and return a list of token dicts.

    The model is instructed (via system prompt) to output a JSON array ONLY.
    We then json.loads() it.

    Requires OPENAI_API_KEY in environment or config for OpenAI client.
    """
    client = OpenAI()
    system_prompt = load_system_prompt(prompt_path)

    resp = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": f'Sentence: "{sentence}"\n'
                           f"Return ONLY a JSON array of token objects.",
            },
        ],
    )

    # Responses API: take first output, first content chunk
    text = resp.output[0].content[0].text

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        # Wrap in a clearer error message
        raise ValueError(f"Model did not return valid JSON. Raw text:\n{text}") from e

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array, got: {type(data)}")

    return data
