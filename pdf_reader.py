from typing import Tuple

from PyPDF2 import PdfReader


def extract_text_from_pdf(path: str) -> Tuple[str, int]:
    """
    Read a PDF file and return (text, num_pages).

    Raises ValueError for empty documents.
    """
    reader = PdfReader(path)
    num_pages = len(reader.pages)

    if num_pages == 0:
        raise ValueError("The PDF document has no pages.")

    texts = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        texts.append(page_text)

    full_text = "\n".join(texts).strip()

    if not full_text:
        raise ValueError("Could not extract any text from the PDF.")

    return full_text, num_pages

