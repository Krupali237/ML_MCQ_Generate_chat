from __future__ import annotations

import random
from typing import List, Dict, Any

from ollama_utils import ollama_generate_json, OllamaError


MCQ_SYSTEM_PROMPT = """
You are a study assistant that generates multiple-choice questions (MCQs) strictly from the provided document content.

Rules:
- Use ONLY the given context text; do not invent facts.
- For each question, create:
  - question
  - 4 options (A, B, C, D)
  - answer (must be exactly one of A, B, C, or D)
  - explanation (why the correct option is right, using the document)
- Questions must be factual and clearly answerable from the context.
- Difficulty level: {difficulty}.

Output JSON ONLY as a list of objects with this exact schema:
[
  {{
    "question": "",
    "options": ["", "", "", ""],
    "answer": "",
    "explanation": ""
  }}
]
"""


def _pick_context(chunks: List[str], max_chars: int = 5500) -> str:
    """
    Pick a representative subset of chunks so the prompt stays small and relevant.
    """
    if not chunks:
        return ""

    # Sample evenly from the document to cover more topics.
    n = min(10, len(chunks))
    if len(chunks) <= n:
        picked = chunks
    else:
        step = max(1, len(chunks) // n)
        picked = [chunks[i] for i in range(0, len(chunks), step)][:n]

    # Small shuffle to reduce repeated patterns
    random.shuffle(picked)
    text = " ".join(picked)
    return text[:max_chars]


def _build_mcq_prompt(chunks: List[str], num_questions: int, difficulty: str) -> str:
    context = _pick_context(chunks)
    system = MCQ_SYSTEM_PROMPT.format(difficulty=difficulty)
    return (
        f"{system}\n\n"
        f"Number of questions to generate: {num_questions}\n\n"
        f"Document context:\n{context}\n\n"
        "Return ONLY valid JSON, no extra text."
    )


def generate_mcqs_from_chunks(chunks: List[str], num_questions: int, difficulty: str) -> List[Dict[str, Any]]:
    if not chunks:
        return []

    prompt = _build_mcq_prompt(chunks, num_questions, difficulty)
    try:
        data = ollama_generate_json(
            model="llama3.2:latest",
            prompt=prompt,
            temperature=0.0,
            num_predict=1400,
        )
    except OllamaError as e:
        raise RuntimeError(f"MCQ generation failed (Ollama): {e}") from e

    # Accept either a direct list or a wrapped object like {"mcqs": [...]}
    if isinstance(data, dict):
        if isinstance(data.get("mcqs"), list):
            data = data["mcqs"]
        elif isinstance(data.get("questions"), list):
            data = data["questions"]

    if not isinstance(data, list):
        raise RuntimeError("MCQ generation returned an unexpected JSON format (expected a list).")

    normalized: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        options = item.get("options", [])
        answer = str(item.get("answer", "")).strip()
        explanation = str(item.get("explanation", "")).strip()

        if not question or not isinstance(options, list) or len(options) != 4:
            continue

        try:
            options = [str(o).strip() for o in options]
        except Exception:
            continue

        if answer not in {"A", "B", "C", "D"}:
            continue

        normalized.append(
            {
                "question": question,
                "options": options,
                "answer": answer,
                "explanation": explanation,
            }
        )

    return normalized[:num_questions]

