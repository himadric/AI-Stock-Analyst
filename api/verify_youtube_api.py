import os
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

api_key = os.getenv("YOUTUBE_API_KEY")

def check_youtube_api():
    if not api_key:
        print("Error: YOUTUBE_API_KEY not found in environment.")
        return

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # 1. Search for a video
        print("Searching for 'ONON stock'...")
        search_response = youtube.search().list(
            q="ONON stock",
            part="id,snippet",
            maxResults=1,
            type="video"
        ).execute()
        
        items = search_response.get("items", [])
        if not items:
            print("No videos found.")
            return

        video_id = items[0]["id"]["videoId"]
        video_title = items[0]["snippet"]["title"]
        print(f"Found video: {video_title} (ID: {video_id})")

        # 2. Fetch comments for this video
        print(f"Fetching comments for {video_id}...")
        comment_response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=3,
            textFormat="plainText"
        ).execute()
        
        comments = []
        for item in comment_response.get("items", []):
            comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(comment)
            
        print(f"Found {len(comments)} comments:")
        print(json.dumps(comments, indent=2))
        
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    check_youtube_api()
