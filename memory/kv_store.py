import json, os

KV_PATH = os.path.join(os.path.dirname(__file__), 'kv_memory.json')

def load_kv():
    if os.path.exists(KV_PATH):
        with open(KV_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_kv(store: dict):
    with open(KV_PATH, 'w', encoding='utf-8') as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
        