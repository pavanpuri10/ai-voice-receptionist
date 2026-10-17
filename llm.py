"""
Thin wrapper around a local Ollama model.
Ollama must be running (`ollama serve`, usually started automatically)
with the model pulled (`ollama pull llama3.2`).
"""

import json
import re
import requests

from config import OLLAMA_URL, OLLAMA_MODEL


def _call_ollama(prompt: str, system: str = "") -> str:
    """Send a prompt to the local Ollama server and return the raw text response."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0.3},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Could not reach Ollama at "
            f"{OLLAMA_URL}. Is Ollama installed and running? "
            "Start it with `ollama serve` and make sure you've run "
            f"`ollama pull {OLLAMA_MODEL}`."
        )


def generate_reply(system_prompt: str, user_text: str) -> str:
    """General purpose: get a natural-language reply from the LLM."""
    return _call_ollama(prompt=user_text, system=system_prompt)


def extract_json(system_prompt: str, user_text: str, retries: int = 2) -> dict:
    """
    Ask the LLM to return ONLY a JSON object, then parse it.
    Retries once or twice if the model adds stray text around the JSON.
    """
    full_system = (
        system_prompt
        + "\n\nIMPORTANT: Respond with ONLY a valid JSON object. "
        "No explanations, no markdown fences, no extra text."
    )
    last_error = None
    for _ in range(retries + 1):
        raw = _call_ollama(prompt=user_text, system=full_system)
        # Try to pull out the first {...} block in case the model added extra text
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        candidate = match.group(0) if match else raw
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            last_error = e
            continue
    raise ValueError(f"LLM did not return valid JSON after retries. Last output error: {last_error}")
