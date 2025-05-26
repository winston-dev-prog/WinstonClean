from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import time, random, uuid, re, os
from datetime import datetime, timezone
import openai
from pinecone import Pinecone, ServerlessSpec
from memory.kv_store import load_kv, save_kv
from memory.vector_memory import retrieve_memories, store_memory
from search.google_search import google_search
from search.youtube_search import youtube_search

# --- Načtení klíčů z prostředí ---
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_ENV = os.environ.get("PINECONE_ENVIRONMENT", "us-east-1")
INDEX_NAME = os.environ.get("INDEX_NAME", "winston-memory")
INDEX_DIMENSION = int(os.environ.get("INDEX_DIMENSION", 1536))
INDEX_METRIC = os.environ.get("INDEX_METRIC", "cosine")
# (volitelné Twilio/Google/YouTube proměnné, nech prázdné pokud je zatím nepoužíváš)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# --- Flask + CORS + static ---
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# --- Inicializace OpenAI klienta ---
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- Inicializace Pinecone ---
pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
# pokud index neexistuje, vytvoříme ho
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=INDEX_DIMENSION,
        metric=INDEX_METRIC,
        spec=ServerlessSpec(cloud="aws", region=PINECONE_ENV)
    )
memory_index = pc.Index(INDEX_NAME)

# --- KV paměť (soubor) ---
KV_PATH = os.path.join(os.path.dirname(__file__), 'kv_memory.json')

# --- Serve PWA ---
@app.route('/', methods=['GET'])
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:filename>', methods=['GET'])
def serve_static(filename):
    return send_from_directory('static', filename)

# --- Chat endpoint ---
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    msg = data.get('message', '').strip()

    # 1) Klíč–hodnota paměť
    kv = load_kv()
    likes = kv.get('likes', [])

    # --- Uložení jména ---
    m = re.match(r'^Jmenuji se\s+(.+)$', msg, re.IGNORECASE)
    if m:
        kv['name'] = m.group(1).strip().rstrip('.')
        save_kv(kv)
        return jsonify({'reply': f"Uloženo: jméno = {kv['name']}"})

    # --- Uložení jména přítelkyně ---
    m = re.match(r'^(?:Moje přítelkyně se jmenuje|Přítelkyně se jmenuje)\s+(.+)$', msg, re.IGNORECASE)
    if m:
        kv['girlfriend'] = m.group(1).strip().rstrip('.')
        save_kv(kv)
        return jsonify({'reply': f"Uloženo: přítelkyně = {kv['girlfriend']}"})

    # --- Uložení oblíbených věcí ---
    m = re.match(r'^(?:Mám rád|Rád piju)\s+(.+)$', msg, re.IGNORECASE)
    if m:
        item = m.group(1).strip().rstrip('.')
        if item not in likes:
            likes.append(item)
            kv['likes'] = likes
            save_kv(kv)
        return jsonify({'reply': f"Uloženo: máš rád {item}"})

    # --- Dotazy na KV paměť ---
    if re.search(r'^Jak se jmenuji\?*$', msg, re.IGNORECASE):
        name = kv.get('name')
        reply = f"Jmenujete se {name}." if name else "Ještě nevím, jak se jmenujete."
        return jsonify({'reply': reply})
    if re.search(r'^(?:Jak se jmenuje přítelkyně|Jak se jmenuje moje přítelkyně)\?*$', msg, re.IGNORECASE):
        gf = kv.get('girlfriend')
        reply = f"Vaše přítelkyně se jmenuje {gf}." if gf else "Ještě nevím jméno vaší přítelkyně."
        return jsonify({'reply': reply})
    if re.search(r'^Co mám rád\?*$', msg, re.IGNORECASE):
        if likes:
            reply = f"Máš rád: {', '.join(likes)}."
        else:
            reply = "Ještě nevím, co máš rád."
        return jsonify({'reply': reply})

    # --- Přímá odpověď prezident USA přes Google snippet ---
    if re.search(r'kdo je prezident(?: usa| spoje[ných]* států)?\??', msg, re.IGNORECASE):
        try:
            prez = google_search(msg, num=1)[0]
            return jsonify({'reply': prez})
        except Exception as e:
            app.logger.error("google_search selhalo u prezidenta USA: %s", e)

    # --- Aktuální datum ---
    today = datetime.now().strftime("%d. %m. %Y")
    system_date = f"Aktuální datum je {today}."

    # --- Živé vyhledávání Google + YouTube ---
    snippets = []
    try:
        snippets += google_search(msg, num=2)
    except Exception as e:
        app.logger.error("google_search selhalo: %s", e)
    try:
        snippets += youtube_search(msg, max_results=2)
    except Exception as e:
        app.logger.error("youtube_search selhalo: %s", e)
    system_live = ("Aktuální informace z webu:\n" + "\n".join(snippets)) if snippets else "Žádná čerstvá data nenalezena."

    # --- Kontext z Pinecone ---
    try:
        memories = retrieve_memories(msg)
    except Exception as e:
        app.logger.error("retrieve_memories selhalo: %s", e)
        memories = []
    system_vect = "Pamatuj si předchozí konverzaci:\n" + "\n".join(memories)

    # --- Volání OpenAI ---
    messages = [
        {"role": "system", "content": system_date},
        {"role": "system", "content": system_live},
        {"role": "system", "content": system_vect},
        {"role": "user", "content": msg}
    ]
    r = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
    reply = r.choices[0].message.content

    # --- Uložení do Pinecone ---
    try:
        now = datetime.now(timezone.utc).isoformat()
        store_memory(msg, {"id": str(uuid.uuid4()), "text": msg, "timestamp": now})
        store_memory(reply, {"id": str(uuid.uuid4()), "text": reply, "timestamp": now})
    except Exception as e:
        app.logger.error("store_memory selhalo: %s", e)

    return jsonify({'reply': reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    