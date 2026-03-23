from __future__ import annotations

from typing import Optional

from vector_store import VectorStoreManager
from ollama_utils import ollama_generate, OllamaError


SYSTEM_PROMPT = (
    "You are a helpful study assistant. "
    "Answer ONLY using the information provided in the context from the uploaded document. "
    "If the answer is not in the context, say you cannot find it in the document."
)


class DocumentChatbot:
    def __init__(self, vector_manager: VectorStoreManager):
        self.vector_manager = vector_manager
        self._model = "llama3.2:latest"

    def ask(self, question: str) -> str:
        vs = self.vector_manager.get_vectorstore()
        if not vs:
            return "No document is loaded. Please upload a document first."

        try:
            # Avoid retriever API differences across LangChain versions.
            docs = vs.similarity_search(question, k=5)
        except Exception as e:
            return f"Sorry, I could not retrieve relevant parts of the document: {e}"

        if not docs:
            return "I could not find the answer in the document."

        context = "\n\n".join(d.page_content for d in docs)[:5000]
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer using only the context above."
        )
        try:
            return ollama_generate(model=self._model, prompt=prompt, temperature=0.2, num_predict=400)
        except OllamaError as e:
            return f"Sorry, I could not reach the local model: {e}"

    def summarize_document(self) -> Optional[str]:
        """
        Produce a short summary of the whole document using the stored chunks.
        """
        if not self.vector_manager.has_docs():
            return None

        text_chunks = self.vector_manager.get_all_text_chunks()
        snippet = " ".join(text_chunks[:3])
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            "Create a short, high-level summary of the document in 3–5 sentences "
            "based ONLY on the following content:\n\n"
            f"{snippet[:4000]}"
        )
        try:
            return ollama_generate(model=self._model, prompt=prompt, temperature=0.2, num_predict=250)
        except Exception:
            return None

