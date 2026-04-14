from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import requests

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


class OllamaError(RuntimeError):
    pass


def ollama_generate(
    *,
    model: str,
    prompt: str,
    json_mode: bool = False,
    temperature: float = 0.0,
    num_predict: Optional[int] = None,
) -> str:
    """
    Call Ollama's /api/generate endpoint.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if json_mode:
        payload["format"] = "json"
    if num_predict is not None:
        payload["options"]["num_predict"] = num_predict

    try:
        resp = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=180)
    except requests.RequestException as e:
        raise OllamaError(f"Could not reach Ollama at {OLLAMA_BASE_URL}: {e}") from e

    if resp.status_code != 200:
        raise OllamaError(f"Ollama error HTTP {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    return (data.get("response") or "").strip()


def ollama_generate_json(
    *,
    model: str,
    prompt: str,
    temperature: float = 0.0,
    num_predict: Optional[int] = None,
) -> Any:
    """
    Generate and parse JSON output via Ollama JSON mode.
    """
    text = ollama_generate(
        model=model,
        prompt=prompt,
        json_mode=True,
        temperature=temperature,
        num_predict=num_predict,
    )
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise OllamaError(f"Ollama did not return valid JSON. Output: {text[:500]}") from e
