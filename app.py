import os
import uuid
import re
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS 
app = Flask(__name__, static_folder='static', static_url_path='') 
CORS(app)

import openai
from pinecone import Pinecone, ServerlessSpec

from memory.kv_store import load_kv, save_kv
# vypnuto: pinecone paměť
# from memory.vector_memory import retrieve_memories, store_memory
from search.google_search import google_search
from search.youtube_search import youtube_search

# --- Načtení klíčů z config.py ---
from config import (
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    INDEX_NAME,
    INDEX_DIMENSION,
    INDEX_METRIC
)

# --- Inicializace Flask + CORS ---
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# --- Inicializace OpenAI klienta ---
openai.api_key = OPENAI_API_KEY

# --- Inicializace Pinecone ---
pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
try:
    pc.create_index(
        name=INDEX_NAME,
        dimension=INDEX_DIMENSION,
        metric=INDEX_METRIC,
        spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT)
    )
except Exception:
    pass # ignore if already exists
memory_index = pc.Index(INDEX_NAME)

# --- KV paměť souboru ---
KV_PATH = os.path.join(os.path.dirname(__file__), 'kv_memory.json')

# --- Serve PWA front-end ---
@app.route('/', methods=['GET'])
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:filename>', methods=['GET'])
def serve_static(filename):
    return send_from_directory('static', filename)

# --- API endpoint pro chat ---
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    msg = data.get('message', '').strip()

    # 1) KV paměť
    kv = load_kv(KV_PATH)
    likes = kv.get('likes', [])

    # Uložení jména
    if m := re.match(r'^Jmenuji se\s+(.+)$', msg, re.IGNORECASE):
        kv['name'] = m.group(1).strip().rstrip('.')
        save_kv(KV_PATH, kv)
        return jsonify({'reply': f"Uloženo: jméno = {kv['name']}"})

    # Uložení přítelkyně
    if m := re.match(r'^(?:Moje přítelkyně se jmenuje|Přítelkyně se jmenuje)\s+(.+)$', msg, re.IGNORECASE):
        kv['girlfriend'] = m.group(1).strip().rstrip('.')
        save_kv(KV_PATH, kv)
        return jsonify({'reply': f"Uloženo: přítelkyně = {kv['girlfriend']}"})

    # Uložení likes
    if m := re.match(r'^(?:Mám rád|Rád piju)\s+(.+)$', msg, re.IGNORECASE):
        item = m.group(1).strip().rstrip('.')
        if item not in likes:
            likes.append(item)
            kv['likes'] = likes
            save_kv(KV_PATH, kv)
        return jsonify({'reply': f"Uloženo: máš rád {item}"})

    # Dotazy na KV
    if re.search(r'^Jak se jmenuji\?*$', msg, re.IGNORECASE):
        name = kv.get('name')
        return jsonify({'reply': f"Jmenujete se {name}." if name else "Nevím."})

    if re.search(r'^(?:Jak se jmenuje přítelkyně)\?*$', msg, re.IGNORECASE):
        gf = kv.get('girlfriend')
        return jsonify({'reply': f"Přítelkyně se jmenuje {gf}." if gf else "Nevím."})

    if re.search(r'^Co mám rád\?*$', msg, re.IGNORECASE):
        return jsonify({'reply': f"Máš rád: {', '.join(likes)}." if likes else "Nevím."})

    # 2) Datum a live vyhledávání
    today = datetime.now().strftime("%d. %m. %Y")
    system_date = f"Aktuální datum je {today}."

    snippets = []
    for fn in (lambda: google_search(msg, num=2), lambda: youtube_search(msg, max_results=2)):
        try:
            snippets.extend(fn())
        except Exception:
            pass
    system_live = ("Aktuální informace:\n" + "\n".join(snippets)) if snippets else "Žádná data."

    # 3) Chat s OpenAI
    r = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_date},
            {"role": "system", "content": system_live},
            {"role": "user", "content": msg}
        ]
    )
    reply = r.choices[0].message.content

    return jsonify({'reply': reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
