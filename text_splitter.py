from typing import List

def split_text_into_chunks(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> List[str]:
    """
    Clean the text and split into overlapping chunks for embedding.
    """
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    # Lightweight local chunker to avoid heavy deps (torch/transformers).
    chunks: List[str] = []
    step = max(1, chunk_size - chunk_overlap)
    for start in range(0, len(cleaned), step):
        chunk = cleaned[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks

