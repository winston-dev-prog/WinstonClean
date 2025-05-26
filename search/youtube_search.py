from googleapiclient.discovery import build
import config

def youtube_search(query: str, max_results: int = 3) -> list[str]:
    """
    Vrátí seznam řetězců ve formátu:
      Název videa (https://youtu.be/…Id>)
    pro prvních max_results videí z YouTube.
    """
    # vytvoří client pro YouTube Data API
    yt = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)

    # požadavek na vyhledání videí
    req = yt.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_results
    )
    res = req.execute()

    # sestavíme seznam titulků + url
    videos = []
    for item in res.get("items", []):
        title = item["snippet"]["title"]
        video_id = item["id"]["videoId"]
        url = f"https://youtu.be/…id"
        videos.append(f"{title} ({url})")

    return videos
