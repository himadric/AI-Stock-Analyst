from youtubesearchpython import Comments
import json

def check_comments(video_id):
    print(f"Fetching comments for video: {video_id}")
    try:
        comments = Comments(video_id)
        # Getting the first batch of comments
        results = comments.result()
        
        if 'result' in results:
            print(f"Found {len(results['result'])} comments.")
            print(json.dumps(results['result'][:3], indent=2))
        else:
            print("No comments found or structure changed.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Using a known safe video ID (e.g. from On Running or a popular stock video)
    # This is a random On Holding stock analysis video ID for testing
    check_comments("1AnTYiUFiXM") 
