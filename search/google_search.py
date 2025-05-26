# search/google_search.py
from googleapiclient.discovery import build
from config import GOOGLE_API_KEY, GOOGLE_CX

def google_search(query: str, num: int = 2) -> list[str]:
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        return ["Chybí Google API klíč nebo CX v prostředí."]
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    resp = service.cse().list(q=query, cx=GOOGLE_CX, num=num).execute()
    items = resp.get("items", [])
    return [item["snippet"] for item in items]
