from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY

def youtube_search(query: str, max_results: int = 2) -> list[str]:
    """
    Provede vyhledání na YouTube a vrátí seznam titulků videí.
    """
    if not YOUTUBE_API_KEY:
        return ["Chybí YouTube API klíč v prostředí."]
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    resp = (
        youtube
        .search()
        .list(q=query, part="snippet", maxResults=max_results)
        .execute()
    )
    items = resp.get("items", [])
    # z každé položky vezmeme snippet.title
    return [item["snippet"]["title"] for item in items]
