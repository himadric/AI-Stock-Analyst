import json
import os
import re
from collections import Counter

# Configuration
INPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw_reddit_onon.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sentiment_onon.json")

# Mini-Lexicon for Sentiment
POSITIVE_WORDS = {
    "love", "best", "great", "moon", "impressive", "beat", "buy", "fire", "cool", 
    "growth", "backed", "profit", "bullish", "strong", "high", "performance", "up"
}
NEGATIVE_WORDS = {
    "terrible", "ripping", "rip", "overvalued", "short", "shorting", "drying", 
    "concern", "down", "bad", "average", "hype", "fail", "sell", "debt", "risk"
}

EMOTIONS = {
    "Admiration": ["love", "impressive", "best", "fire", "cool"],
    "Trust": ["backed", "buy", "strong", "growth"],
    "Frustration": ["terrible", "ripping", "bad", "fail"],
    "Sarcasm": ["moon", "hype"] # Conceptual mapping
}

def clean_text(text):
    return re.sub(r'[^\w\s]', '', text.lower())

def analyze_sentiment():
    print("Loading data...")
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r") as f:
        comments = json.load(f)

    print(f"Analyzing {len(comments)} comments...")

    total_score = 0
    pos_count = 0
    neg_count = 0
    neu_count = 0
    
    all_words = []
    emotion_counts = {k: 0 for k in EMOTIONS.keys()}

    processed_comments = []

    for comment in comments:
        text = comment.get("body", "")
        cleaned = clean_text(text)
        words = cleaned.split()
        all_words.extend(words)

        # Simple scoring
        score = 0
        detected_emotions = set()
        
        for word in words:
            if word in POSITIVE_WORDS:
                score += 1
            elif word in NEGATIVE_WORDS:
                score -= 1
            
            # Check emotions
            for emotion, keywords in EMOTIONS.items():
                if word in keywords:
                    detected_emotions.add(emotion)

        for e in detected_emotions:
            emotion_counts[e] += 1

        label = "Neutral"
        if score > 0:
            label = "Positive"
            pos_count += 1
        elif score < 0:
            label = "Negative"
            neg_count += 1
        else:
            neu_count += 1
            
        total_score += score
        processed_comments.append({
            "text": text,
            "score": score,
            "label": label,
            "emotions": list(detected_emotions)
        })

    # Calculations
    total = len(comments)
    nss = ((pos_count - neg_count) / total) * 100 if total > 0 else 0
    
    # Trends (Keywords)
    # Filter common stop words
    stop_words = {"the", "and", "a", "to", "of", "in", "is", "it", "my", "on", "for", "with", "this", "that", "but", "are", "be", "onon"}
    filtered_words = [w for w in all_words if w not in stop_words and len(w) > 2]
    top_keywords = Counter(filtered_words).most_common(10)

    results = {
        "nss": round(nss, 2),
        "distribution": {
            "positive": pos_count,
            "negative": neg_count,
            "neutral": neu_count,
            "total": total
        },
        "emotions": emotion_counts,
        "keywords": top_keywords,
        "comments": processed_comments
    }

    # Save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Analysis complete. NSS: {nss}. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    analyze_sentiment()
