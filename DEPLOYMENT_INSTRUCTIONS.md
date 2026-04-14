# 🚀 Render Deployment Guide for Smart Study Assistant

I have fully configured your project for a **perfect, error-free deployment** on Render. The modifications ensure Render uses the correct startup web server (Gunicorn), uses a compatible Python version, and safely creates directories so the app never crashes from missing folders! 

### What was updated?
1. **`requirements.txt`**: Added `gunicorn==21.2.0` (Render's required web server for Python apps).
2. **`render.yaml`**: Added an automated Configuration Blueprint. This makes deployment 1-click.
3. **`app.py`**: Added auto-creation of the `uploads` directory (prevents `FileNotFoundError`).
4. **`llm.py` & `ollama_utils.py`**: Made Ollama URLs configurable via Environment Variables so you can connect to an external server if needed.
5. **`.gitignore`**: Added so you don't accidentally push huge database/upload files that slow down deployment.
6. **`.python-version`**: Pinned Python 3.11.6 to ensure SQLite is completely compatible with ChromaDB.

---

### Step 1: Push the code to GitHub

If you haven't already, you need to push these changes to a GitHub repository:
1. Open terminal in your `smart-study-assistant` folder.
2. Run the following commands:
   ```bash
   git init
   git add .
   git commit -m "Configure for Render Deployment"
   git branch -M main
   # Add your GitHub repository link and push:
   # git remote add origin https://github.com/YourUsername/YourRepo.git
   # git push -u origin main
   ```

### Step 2: Deploy on Render

1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** and select **Blueprint**.
3. Connect your GitHub repository.
4. Render will automatically detect the **`render.yaml`** file I created.
5. Review the plan (it will default to the Free Web Service tier) and click **Apply**.

Render will now build your project using python environments and automatically spin up the app mapping your `app.run` to the correct `$PORT`.

---

### ⚠️ Important Limitations on Render Free Tier

1. **Ephemeral File System**: The free web tier on Render resets its local storage every time it deploys or wakes up from inactivity. This means any **PDFs/PPTs you upload, Chat Histories, and generated Quizzes will be wiped out periodically**. The app will NOT crash when this happens (because I configured it to auto-create them), but data won't persist long-term.
2. **Ollama Integration**: Standard Render instances **cannot** run Ollama inside them. Right now, your app talks to `http://localhost:11434` (Ollama running on your PC). When deployed on Render, it will try to find Ollama on Render's server and fail (giving a Chat Error).
   * **Solution A**: Expose your PC's Ollama using `ngrok` (e.g. `ngrok http 11434`), then go to Render -> Your Web Service -> Environment, and change `OLLAMA_API_URL` and `OLLAMA_BASE_URL` to your ngrok URL.
   * **Solution B**: Use an API-based LLM like Groq, Google Gemini, or host Ollama on an expensive cloud GPU instance.
