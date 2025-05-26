import requests
import config

def yahoo_search(query: str, count: int = 3) -> list[str]:
    url = "https://api.search.yahoo.com/…web"
    params = {"q": query, "format": "json", "count": count}
    auth = (config.YAHOO_APP_ID, config.YAHOO_APP_KEY)
    resp = requests.get(url, params=params, auth=auth)
    data = resp.json()
    results = data.get("bossresponse", {}).get("web", {}).get("results", [])
    return [f"{r['title']}: {r['abstract']} ({r['clickurl']})" for r in results]
