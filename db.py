import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'history.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check and add columns for backward compatibility
    c.execute("PRAGMA table_info(mcq_sets)")
    columns_mcq = [info['name'] for info in c.fetchall()]
    if columns_mcq and 'doc_name' not in columns_mcq:
        c.execute("ALTER TABLE mcq_sets ADD COLUMN doc_name TEXT DEFAULT 'Unknown Document'")
    if columns_mcq and 'num_questions' not in columns_mcq:
        c.execute("ALTER TABLE mcq_sets ADD COLUMN num_questions INTEGER DEFAULT 0")

    c.execute("PRAGMA table_info(chat_sessions)")
    columns_chat = [info['name'] for info in c.fetchall()]
    if columns_chat and 'doc_name' not in columns_chat:
        c.execute("ALTER TABLE chat_sessions ADD COLUMN doc_name TEXT DEFAULT 'Unknown Document'")

    c.executescript('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            doc_name TEXT DEFAULT 'Unknown Document',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id)
        );
        CREATE TABLE IF NOT EXISTS mcq_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            doc_name TEXT DEFAULT 'Unknown Document',
            num_questions INTEGER DEFAULT 0,
            difficulty TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS mcqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT NOT NULL,
            FOREIGN KEY (set_id) REFERENCES mcq_sets (id)
        );
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (set_id) REFERENCES mcq_sets (id)
        );
    ''')
    conn.commit()
    conn.close()

def save_chat_message(session_id, role, content, doc_name="Unknown Document"):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO chat_sessions (session_id, doc_name) VALUES (?, ?)', (session_id, doc_name))
    c.execute('INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)',
              (session_id, role, content))
    conn.commit()
    conn.close()

def get_chat_history(session_id):
    conn = get_db_connection()
    messages = conn.execute('SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY id ASC',
                            (session_id,)).fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in messages]

def save_mcq_set(doc_id, doc_name, difficulty, mcqs_list):
    conn = get_db_connection()
    c = conn.cursor()
    num_questions = len(mcqs_list)
    c.execute('INSERT INTO mcq_sets (doc_id, doc_name, num_questions, difficulty) VALUES (?, ?, ?, ?)', 
              (doc_id, doc_name, num_questions, difficulty))
    set_id = c.lastrowid
    
    for mcq in mcqs_list:
        c.execute('''
            INSERT INTO mcqs (set_id, question, option_a, option_b, option_c, option_d, correct_answer, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            set_id,
            mcq.get('question', ''),
            mcq.get('A', ''),
            mcq.get('B', ''),
            mcq.get('C', ''),
            mcq.get('D', ''),
            mcq.get('correct_answer', ''),
            mcq.get('explanation', '')
        ))
    
    conn.commit()
    conn.close()
    return set_id

def get_recent_chat_sessions():
    conn = get_db_connection()
    sessions = conn.execute('''
        SELECT session_id, doc_name, created_at,
        (SELECT content FROM chat_messages WHERE session_id = chat_sessions.session_id ORDER BY id ASC LIMIT 1) as first_message
        FROM chat_sessions ORDER BY created_at DESC LIMIT 20
    ''').fetchall()
    conn.close()
    return [dict(row) for row in sessions]

def get_recent_mcq_sets():
    conn = get_db_connection()
    sets = conn.execute('SELECT id, doc_id, doc_name, num_questions, difficulty, created_at FROM mcq_sets ORDER BY created_at DESC LIMIT 20').fetchall()
    conn.close()
    result = []
    for row in sets:
        result.append(dict(row))
    return result

def get_mcqs_by_set(set_id):
    conn = get_db_connection()
    mcqs = conn.execute('SELECT * FROM mcqs WHERE set_id = ? ORDER BY id ASC', (set_id,)).fetchall()
    conn.close()
    return [dict(row) for row in mcqs]

def delete_chat_session(session_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
    conn.execute('DELETE FROM chat_sessions WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()

def delete_mcq_set(set_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM quiz_attempts WHERE set_id = ?', (set_id,))
    conn.execute('DELETE FROM mcqs WHERE set_id = ?', (set_id,))
    conn.execute('DELETE FROM mcq_sets WHERE id = ?', (set_id,))
    conn.commit()
    conn.close()

def save_quiz_attempt(set_id, score, total):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO quiz_attempts (set_id, score, total) VALUES (?, ?, ?)', (set_id, score, total))
    conn.commit()
    conn.close()

def get_attempts_for_set(set_id):
    conn = get_db_connection()
    attempts = conn.execute('SELECT score, total, created_at FROM quiz_attempts WHERE set_id = ? ORDER BY created_at DESC', (set_id,)).fetchall()
    conn.close()
    return [dict(row) for row in attempts]

