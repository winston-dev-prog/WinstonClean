from googleapiclient.discovery import build
import config

def google_search(query: str, num: int = 3) -> list[str]:
    service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
    res = service.cse().list(q=query, cx=config.GOOGLE_CX, num=num).execute()
    return [item["snippet"] for item in res.get("items", [])]
