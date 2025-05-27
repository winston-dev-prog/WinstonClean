import os
import uuid
import re
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import openai
from pinecone import Pinecone, ServerlessSpec

from memory.kv_store import load_kv, save_kv
from memory.vector_memory import retrieve_memories, store_memory
from search.google_search import google_search
from search.youtube_search import youtube_search

# --- Načtení klíčů z config.py ---
from config import (
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    INDEX_NAME,
    INDEX_DIMENSION,
    INDEX_METRIC,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN
)

# --- Inicializace Flask + CORS ---
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# --- Inicializace OpenAI klienta ---
openai.api_key = OPENAI_API_KEY

# --- Inicializace Pinecone klienta ---
pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)

# Pokusíme se vytvořit index, pokud ještě neexistuje
from pinecone.openapi_support.exceptions import PineconeApiException
try:
    pc.create_index(
        name=INDEX_NAME,
        dimension=INDEX_DIMENSION,
        metric=INDEX_METRIC,
        spec=ServerlessSpec(cloud="aws", region=PINECONE_ENVIRONMENT)
    )
except PineconeApiException as e:
    # Ignorujeme chybu, pokud index již existuje
    if hasattr(e, 'error') and isinstance(e.error, dict) and e.error.get('code') == 'ALREADY_EXISTS':
        pass
    else:
        raise

# Získáme instanci indexu pro čtení a zápis
memory_index = pc.Index(INDEX_NAME)
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

    # 1) Klíč–hodnota paměť
    kv = load_kv(KV_PATH)
    likes = kv.get('likes', [])

    # Uložení jména
    if m := re.match(r'^Jmenuji se\s+(.+)$', msg, re.IGNORECASE):
        kv['name'] = m.group(1).strip().rstrip('.')
        save_kv(KV_PATH, kv)
        return jsonify({'reply': f"Uloženo: jméno = {kv['name']}"})

    # Uložení jména přítelkyně
    if m := re.match(r'^(?:Moje přítelkyně se jmenuje|Přítelkyně se jmenuje)\s+(.+)$', msg, re.IGNORECASE):
        kv['girlfriend'] = m.group(1).strip().rstrip('.')
        save_kv(KV_PATH, kv)
        return jsonify({'reply': f"Uloženo: přítelkyně = {kv['girlfriend']}"})

    # Uložení oblíbených věcí
    if m := re.match(r'^(?:Mám rád|Rád piju)\s+(.+)$', msg, re.IGNORECASE):
        item = m.group(1).strip().rstrip('.')
        if item not in likes:
            likes.append(item)
            kv['likes'] = likes
            save_kv(KV_PATH, kv)
        return jsonify({'reply': f"Uloženo: máš rád {item}"})

    # Dotazy na KV paměť
    if re.search(r'^Jak se jmenuji\?*$', msg, re.IGNORECASE):
        name = kv.get('name')
        return jsonify({'reply': f"Jmenujete se {name}." if name else "Ještě nevím, jak se jmenujete."})

    if re.search(r'^(?:Jak se jmenuje přítelkyně|Jak se jmenuje moje přítelkyně)\?*$', msg, re.IGNORECASE):
        gf = kv.get('girlfriend')
        return jsonify({'reply': f"Vaše přítelkyně se jmenuje {gf}." if gf else "Ještě nevím jméno vaší přítelkyně."})

    if re.search(r'^Co mám rád\?*$', msg, re.IGNORECASE):
        return jsonify({'reply': f"Máš rád: {', '.join(likes)}." if likes else "Ještě nevím, co máš rád."})

    # Přímá odpověď prezidenta USA přes Google snippet
    if re.search(r'kdo je prezident(?: usa| spoje[ných]* států)?\??', msg, re.IGNORECASE):
        try:
            prez = google_search(msg, num=1)[0]
            return jsonify({'reply': prez})
        except Exception:
            pass

    # 3) Aktuální datum
    today = datetime.now().strftime("%d. %m. %Y")
    system_date = f"Aktuální datum je {today}."

    # 4) Živé vyhledávání
    snippets = []
    for fn in (lambda: google_search(msg, num=2), lambda: youtube_search(msg, max_results=2)):
        try:
            snippets.extend(fn())
        except Exception:
            pass
    system_live = ("Aktuální informace z webu:\n" + "\n".join(snippets)) if snippets else "Žádná čerstvá data nenalezena."

    # 5) Pinecone paměť
    try:
        memories = retrieve_memories(msg)
    except Exception:
        memories = []
    system_vect = "Pamatuj si předchozí konverzaci:\n" + "\n".join(memories)

    # 6) Volání OpenAI
    r = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_date},
            {"role": "system", "content": system_live},
            {"role": "system", "content": system_vect},
            {"role": "user", "content": msg}
        ]
    )
    reply = r.choices[0].message.content

    # 7) Uložení do Pinecone
    now = datetime.now(timezone.utc).isoformat()
    try:
        store_memory(msg, {"id": str(uuid.uuid4()), "text": msg, "timestamp": now})
        store_memory(reply, {"id": str(uuid.uuid4()), "text": reply, "timestamp": now})
    except Exception:
        pass

    return jsonify({'reply': reply})


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )
    