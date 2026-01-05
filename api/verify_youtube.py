from youtubesearchpython import VideosSearch
import json

def check_youtube(query):
    print(f"Searching for: {query}")
    videosSearch = VideosSearch(query, limit=5)
    results = videosSearch.result()
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    check_youtube("ONON stock vs HOKA")
