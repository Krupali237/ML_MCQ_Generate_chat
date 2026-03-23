# Smart Study Assistant

A full-stack AI-powered web application using Flask, Ollama, ChromaDB, and Tailwind CSS.
Upload your PDFs or PPTXs, chat with your document in a ChatGPT-like interface, and automatically generate Multiple Choice Questions (MCQs) mapped directly to your study material.

## Features
- **Document Processing**: PDF & PPTX support with sentence-based intelligent chunking.
- **RAG Chatbot**: Chat naturally with your study materials with fast context retrieval.
- **AI MCQ Generation**: Dynamically craft Easy, Medium, or Hard difficulty questions.
- **Interactive Quiz Interface**: Take quizzes, track progress, view performance, and see detailed explanations.
- **History Logs**: Seamlessly revisit past conversations or previously generated quizzes.
- **Modern UI**: Polished glassmorphism styles, fluid animations, and a responsive Tailwind layout.

## Prerequisites
- **Python 3.8+**
- **Ollama** installed locally (or accessible remote)
  - You must pull the required models into your Ollama instance before running the app.
  ```bash
  ollama pull llama3
  ollama pull nomic-embed-text
  ```

## Setup Instructions
1. **Navigate to the application folder:**
   ```bash
   cd c:\Users\krupali\Desktop\sem 6\MLDL\DLp\smart-study-assistant
   ```

2. **Install the dependencies:**
   It is recommended to use a virtual environment, but installing globally with the `requirements.txt` is fine:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Ollama is running:**
   Make sure Ollama is active on `http://localhost:11434`. (Usually running in the system tray or via terminal).

4. **Run the Flask App:**
   ```bash
   python app.py
   ```

5. **Open your Browser:**
   Go to `http://127.0.0.1:5000/` to start using your Smart Study Assistant!

## Architecture Breakdown
- **Frontend**: HTML5 + Vanilla JS + Tailwind CSS (via CDN to avoid Node overhead).
- **Backend / Routing**: Flask (`app.py`), connected to SQLite for history tracking.
- **Database**: 
   - SQLite (`db.py`) tracks active chat sessions, stored messages, and raw generated MCQs.
   - ChromaDB is used locally as an embedded vector database for fast Context Retrieval (`chroma_db/`).
- **LLM/Embedder**: `llm.py` natively communicates with the local Ollama API, parsing JSON outputs directly for robust structure mapping.
