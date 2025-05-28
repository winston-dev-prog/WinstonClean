import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai
from pinecone import Pinecone, ServerlessSpec
from memory.kv_store import load_kv, save_kv
from search.google_search import google_search
from search.youtube_search import youtube_search

# načteme config
import config

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# OpenAI
openai.api_key = config.OPENAI_API_KEY

# Pinecone
pc = Pinecone(api_key=config.PINECONE_API_KEY, environment=config.PINECONE_ENVIRONMENT)
try:
    pc.create_index(
        name=config.INDEX_NAME,
        dimension=config.INDEX_DIMENSION,
        metric=config.INDEX_METRIC,
        spec=ServerlessSpec(cloud="aws", region=config.PINECONE_ENVIRONMENT)
    )
except Exception:
    pass
memory_index = pc.Index(config.INDEX_NAME)

# Path to key-value JSON
KV_PATH = os.path.join(os.path.dirname(__file__), 'memory', 'kv_memory.json')

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:fp>')
def static_files(fp):
    return send_from_directory('static', fp)

@app.route('/chat', methods=['OPTIONS', 'POST'])
def chat():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.get_json(force=True)
    msg = data.get('message', '').strip()

    # KV store logic (jméno, přítelkyně, likes)
    kv = load_kv(KV_PATH)
    # ... (zachovej dosavadní regexy z app.py) ...

    # System date + live search
    dt = datetime.now().strftime("%d. %m. %Y")
    system_date = f"Aktuální datum je {dt}."
    snippets = []
    for fn in (lambda: google_search(msg, 2), lambda: youtube_search(msg, 2)):
        try:
            snippets += fn()
        except:
            pass
    system_live = "\n".join(snippets) if snippets else "Žádná data."

    # Call OpenAI
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_date},
            {"role": "system", "content": system_live},
            {"role": "user", "content": msg}
        ]
    )
    return jsonify({'reply': resp.choices[0].message.content})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)