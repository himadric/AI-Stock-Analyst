import json
import os
from datetime import datetime

INPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sentiment_onon.json")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "report_content.md")

def generate_report():
    if not os.path.exists(INPUT_FILE):
        print("Input file not found.")
        return

    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    nss = data.get("nss", 0)
    keywords = data.get("keywords", [])
    emotions = data.get("emotions", {})
    distribution = data.get("distribution", {})

    md = f"""# Brand Sentiment Report: On Holding (ONON)
**Date**: {datetime.now().strftime('%Y-%m-%d')}
**Data Source**: Reddit (r/ONON, r/investing, etc.)

## Executive Summary
The Net Sentiment Score (NSS) for On Holding is **{nss}%**.
Based on recent discussions, the sentiment is leaning **{'Positive' if nss > 0 else 'Negative' if nss < 0 else 'Neutral'}**.

## Key Metrics
- **Net Sentiment Score**: {nss}
- **Volume**: {distribution.get('total', 0)} analyzed comments
- **Distribution**: {distribution.get('positive')} Positive, {distribution.get('neutral')} Neutral, {distribution.get('negative')} Negative

## Emotional Analysis
Top emotions detected in the conversation:
"""
    
    # Sort emotions
    sorted_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
    for emotion, count in sorted_emotions:
        md += f"- **{emotion}**: {count} mentions\n"

    md += "\n## Trending Keywords\nWhat people are talking about:\n"
    for word, count in keywords:
        md += f"- **{word}**: {count}\n"

    md += "\n## Sample Verbatims\n"
    comments = data.get("comments", [])
    # Get top 3 positive and top 3 negative
    pos = [c for c in comments if c['score'] > 0][:3]
    neg = [c for c in comments if c['score'] < 0][:3]

    if pos:
        md += "### Positive\n"
        for c in pos:
            md += f"> \"{c['text']}\"\n\n"
            
    if neg:
        md += "### Negative\n"
        for c in neg:
            md += f"> \"{c['text']}\"\n\n"

    with open(OUTPUT_FILE, "w") as f:
        f.write(md)
        
    print(f"Report content generated at {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_report()
