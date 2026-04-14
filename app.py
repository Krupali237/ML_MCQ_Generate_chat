from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, stream_with_context
import random
import concurrent.futures
import json
from werkzeug.utils import secure_filename
import os
import uuid
from db import init_db, save_chat_message, get_chat_history, save_mcq_set, get_recent_chat_sessions, get_recent_mcq_sets, get_mcqs_by_set, delete_chat_session, delete_mcq_set, save_quiz_attempt
from processing import process_document, retrieve_context, get_all_chunks
from llm import chat_with_context, generate_mcqs

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_smart_study_assistant_secret")
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_doc', methods=['POST'])
def upload_doc():
    if 'document' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and (file.filename.endswith('.pdf') or file.filename.endswith('.pptx')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        doc_id, error = process_document(filepath)
        if error:
            return jsonify({'error': error}), 500
        
        # Start a new chat session linked to this doc
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        session['doc_id'] = doc_id
        session['doc_name'] = filename
        
        return jsonify({'doc_id': doc_id, 'session_id': session_id, 'doc_name': filename}), 200
    return jsonify({'error': 'Unsupported format. Only PDF and PPTX allowed.'}), 400

@app.route('/chat')
def chat_page():
    doc_id = request.args.get('doc_id') or session.get('doc_id')
    curr_session_id = request.args.get('session_id') or session.get('session_id')
    if not doc_id:
        return redirect(url_for('index'))
        
    history = []
    if curr_session_id:
        history = get_chat_history(curr_session_id)
        
    return render_template('chat.html', doc_id=doc_id, history=history)

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    data = request.json
    query = data.get('query')
    doc_id = data.get('doc_id')
    curr_session_id = session.get('session_id')
    
    if not curr_session_id:
        curr_session_id = str(uuid.uuid4())
        session['session_id'] = curr_session_id
    
    doc_name = session.get('doc_name', 'Unknown Document')
    
    # Save User message
    save_chat_message(curr_session_id, 'user', query, doc_name=doc_name)
    
    # Retrieve Context
    context = retrieve_context(doc_id, query)
    history = get_chat_history(curr_session_id)
    # Exclude the latest user message from history sent to model as it's passed as query
    model_history = history[:-1] if history else []
    
    # Generate Response
    response_text = chat_with_context(query, context, model_history)
    
    # Save AI message
    save_chat_message(curr_session_id, 'assistant', response_text, doc_name=doc_name)
    
    return jsonify({'response': response_text, 'context_used': bool(context)})

@app.route('/mcq_setup')
def mcq_setup():
    doc_id = request.args.get('doc_id') or session.get('doc_id')
    if not doc_id:
        return redirect(url_for('index'))
    return render_template('mcq_gen.html', doc_id=doc_id)

@app.route('/api/generate_mcq', methods=['POST'])
def generate_mcq_api():
    data = request.json
    doc_id = data.get('doc_id')
    count = int(data.get('count', 5))
    difficulty = data.get('difficulty', 'Medium')
    q_type = data.get('q_type', 'Standard')
    doc_name = session.get('doc_name', 'Unknown Document')
    
    chunks = get_all_chunks(doc_id, limit=200)
    if not chunks:
        return jsonify({'error': 'No content to generate MCQs from'}), 400

    def generate():
        valid_mcqs = []
        seen_questions = set()
        attempts = 0
        mcqs_per_chunk = 3
        max_workers = 4 # Speed up with parallel processing
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # We enforce exactly 'count' questions by running until we hit it or hit the max attempt limit
            while len(valid_mcqs) < count and attempts < 15:
                needed = count - len(valid_mcqs)
                batch_size = min(max_workers, (needed + mcqs_per_chunk - 1) // mcqs_per_chunk)
                futures = []
                
                for _ in range(batch_size):
                    ask_count = min(mcqs_per_chunk, count - len(valid_mcqs))
                    # Pick 1-3 random chunks and keep context size small (under 1200 chars) for speed
                    sampled_chunks = random.sample(chunks, min(3, len(chunks)))
                    combined_text = " ".join(sampled_chunks)[:1200]
                    futures.append(executor.submit(generate_mcqs, combined_text, ask_count, difficulty, q_type))
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        part_mcqs = future.result()
                        if part_mcqs:
                            for mcq in part_mcqs:
                                if len(valid_mcqs) >= count:
                                    break
                                q_text = mcq.get('question', '').strip().lower()
                                has_all_keys = all(k in mcq for k in ['question', 'A', 'B', 'C', 'D', 'correct_answer'])
                                if q_text and q_text not in seen_questions and has_all_keys:
                                    if mcq['correct_answer'] in ['A', 'B', 'C', 'D']:
                                        seen_questions.add(q_text)
                                        valid_mcqs.append(mcq)
                                        # Yield progress periodically
                                        yield json.dumps({"status": "progress", "generated": len(valid_mcqs)}) + "\n"
                    except Exception as e:
                        print(f"Error during parallel generation chunk: {e}")
                attempts += 1

        if len(valid_mcqs) == count:
            set_id = save_mcq_set(doc_id, doc_name, difficulty, valid_mcqs)
            yield json.dumps({"status": "complete", "set_id": set_id}) + "\n"
        elif len(valid_mcqs) > 0:
            set_id = save_mcq_set(doc_id, doc_name, difficulty, valid_mcqs)
            # User wants exactly the requested amount, but we might hit effort limits. 
            # Send what we have but strictly we aimed for 'count'
            yield json.dumps({"status": "complete", "set_id": set_id}) + "\n"
        else:
            yield json.dumps({"status": "error", "error": "Failed to generate valid MCQs."}) + "\n"

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson')

@app.route('/quiz/<int:set_id>')
def quiz_page(set_id):
    mcqs = get_mcqs_by_set(set_id)
    if not mcqs:
        return redirect(url_for('history_page'))
    return render_template('quiz.html', set_id=set_id, mcqs=mcqs)

@app.route('/view_quiz/<int:set_id>')
def view_quiz_page(set_id):
    mcqs = get_mcqs_by_set(set_id)
    if not mcqs:
        return redirect(url_for('history_page'))
    return render_template('view_quiz.html', set_id=set_id, mcqs=mcqs)

@app.route('/history')
def history_page():
    chats = get_recent_chat_sessions()
    mcq_sets = get_recent_mcq_sets()
    return render_template('history.html', chats=chats, mcqs=mcq_sets)

@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/api/delete_chat/<session_id>', methods=['DELETE'])
def api_delete_chat(session_id):
    delete_chat_session(session_id)
    return jsonify({"success": True})

@app.route('/api/delete_mcq/<int:set_id>', methods=['DELETE'])
def api_delete_mcq(set_id):
    delete_mcq_set(set_id)
    return jsonify({"success": True})

@app.route('/api/save_attempt', methods=['POST'])
def api_save_attempt():
    data = request.json
    save_quiz_attempt(data.get('set_id'), data.get('score'), data.get('total'))
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
