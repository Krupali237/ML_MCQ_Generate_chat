import os
import requests
import json

OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api")

def get_embedding(text):
    url = f"{OLLAMA_API_URL}/embeddings"
    payload = {
        "model": "nomic-embed-text",
        "prompt": text
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get('embedding', [])
    except Exception as e:
        print(f"Error getting embedding: {e}. Ensure 'nomic-embed-text' model is installed via 'ollama pull nomic-embed-text'")
        return [0.0] * 768  # Return zero vector with matching dimension to prevent ChromaDB crash

def generate_text(prompt, system_prompt="", stream=False, temperature=0.2, num_predict=600):
    url = f"{OLLAMA_API_URL}/generate"
    payload = {
        "model": "llama3.2",
        "prompt": prompt,
        "system": system_prompt,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        if not stream:
            return response.json().get('response', '')
        return response
    except Exception as e:
        print(f"Error generating text: {e}")
        return ""

def chat_with_context(query, context, history_messages=None):
    if history_messages is None:
        history_messages = []
    
    # Simple formatting of history into text as Llama3 api/generate only takes prompt. 
    # Or, we could use api/chat for the chat completion API which natively supports messages.
    url = f"{OLLAMA_API_URL}/chat"
    
    system_message = {
        "role": "system",
        "content": (
            "You are 'Smart Study Assistant', a highly intelligent and highly detailed AI tutor. "
            "You are 'Smart Study Assistant'. Your primary goal is to provide concise, accurate, and highly relevant "
            "answers to the user based ON THE PROVIDED CONTEXT ONLY. "
            "Be direct, conversational, and simple. DO NOT output massive walls of text or textbook-like dumps unless the user explicitly requests a long explanation. "
            "Use markdown (bolding, short bullet points) effectively to make your answers easy to read. "
            "If the answer is not in the context, do not guess, just clearly state that it is not covered in the document.\n\n"
            f"Context:\n{context}"
        )
    }
    
    messages = [system_message] + history_messages + [{"role": "user", "content": query}]
    payload = {
        "model": "llama3.2",
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.4}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=240)
        response.raise_for_status()
        data = response.json()
        return data.get('message', {}).get('content', '')
    except Exception as e:
        print(f"Error in chat completion: {e}")
        return "Sorry, I encountered an error while trying to generate a response. Your system might be taking too long to process."

def generate_mcqs(text_chunk, count=3, difficulty="Medium", q_type="Standard"):
    type_instruction = ""
    if q_type.lower() == "unique":
        type_instruction = "Ensure the questions are highly unique, analytical, and test deep understanding rather than just factual recall.\n"
    
    diff_instruction = f"with {difficulty} difficulty"
    if difficulty.lower() == "mix":
        diff_instruction = "with a mix of Easy, Medium, and Hard difficulties"

    system_prompt = (
        "You are an expert educational content creator. Your task is to generate Multiple Choice Questions (MCQs) "
        "based strictly on the provided text. Never include information not in the text.\n"
        f"Generate exactly {count} MCQs {diff_instruction}.\n"
        f"{type_instruction}"
        "You MUST return the output ONLY as a valid JSON array of objects, with no other text, markdown blocks, or greetings. "
        "Each object MUST have the following keys: 'question', 'A', 'B', 'C', 'D', 'correct_answer' (must be one of 'A', 'B', 'C', 'D'), and 'explanation'. "
        "Example output format:\n"
        "[\n  {\n    \"question\": \"What is X?\",\n    \"A\": \"Option 1\",\n    \"B\": \"Option 2\",\n    \"C\": \"Option 3\",\n    \"D\": \"Option 4\",\n    \"correct_answer\": \"B\",\n    \"explanation\": \"Because Y.\"\n  }\n]"
    )
    
    response_text = generate_text(prompt=f"Text to use: {text_chunk}", system_prompt=system_prompt, temperature=0.2, num_predict=800)
    
    # Try to parse the json
    try:
        # Check if the model wrapped it in markdown code block
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        parsed = json.loads(response_text)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict) and "mcqs" in parsed:
            return parsed["mcqs"]
        else:
            return []
    except Exception as e:
        print(f"Failed direct JSON parsing: {e}. Attempting regex extraction.")
        import re
        try:
            # Look for an array pattern [ { ... } ]
            match = re.search(r'\[\s*\{.*?\}\s*\]', response_text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                return parsed
        except Exception as e2:
            print(f"Regex parsing also failed: {e2}")
        print(f"Raw Response: {response_text}")
        return []
