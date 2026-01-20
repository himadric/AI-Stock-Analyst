import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("YOUTUBE_API_KEY")

def check_youtube_api():
    if not api_key:
        print("Error: YOUTUBE_API_KEY not found in environment.")
        return

    try:
        # 1. Search for a video
        print("Searching for 'ONON stock'...")
        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "id,snippet",
            "q": "ONON stock",
            "maxResults": 1,
            "type": "video",
            "key": api_key
        }
        res = requests.get(search_url, params=params)
        res.raise_for_status()
        search_data = res.json()
        
        items = search_data.get("items", [])
        if not items:
            print("No videos found.")
            return

        video_id = items[0]["id"]["videoId"]
        video_title = items[0]["snippet"]["title"]
        print(f"Found video: {video_title} (ID: {video_id})")

        # 2. Fetch comments for this video
        print(f"Fetching comments for {video_id}...")
        comments_url = "https://www.googleapis.com/youtube/v3/commentThreads"
        c_params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": 3,
            "textFormat": "plainText",
            "key": api_key
        }
        c_res = requests.get(comments_url, params=c_params)
        
        comments = []
        if c_res.status_code == 200:
            c_data = c_res.json()
            for item in c_data.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(comment)
            
        print(f"Found {len(comments)} comments:")
        print(json.dumps(comments, indent=2))
        
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    check_youtube_api()
