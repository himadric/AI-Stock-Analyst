import os
import yfinance as yf
from googleapiclient.discovery import build
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from collections import Counter
import re
from datetime import datetime, timedelta

class SentimentService:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        self.youtube = None
        if self.youtube_api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
            except Exception as e:
                print(f"Failed to init YouTube API: {e}")

    def get_brand_sentiment(self, ticker: str):
        """
        Orchestrates fetching data and analyzing it.
        Uses Yahoo Finance News and YouTube (Official API).
        """
        stock = yf.Ticker(ticker)
        brand_name = self._get_brand_name(ticker, stock)
        
        # Pass brand name to youtube fetcher, stock object to news
        news_items = self._fetch_news(stock)
        youtube_items = self._fetch_youtube(brand_name)
        
        # Combine and sort by date desc
        all_items = news_items + youtube_items
        all_items.sort(key=lambda x: x['created_utc'], reverse=True)
        
        analysis = self._analyze_sentiment(all_items)
        
        return {
            "ticker": ticker,
            "query": f"News ({ticker}) & YouTube ({brand_name})",
            "analysis": analysis,
            "recent_posts": all_items[:20] 
        }

    def _get_brand_name(self, ticker: str, stock_obj) -> str:
        """
        Maps ticker to a search-friendly brand name.
        Check manual map first, then fetch from Yahoo Finance.
        """
        # 1. Check manual overrides (for known tricky ones)
        mapping = {
            "ONON": "On Running",
            "DECK": "Hoka One One", 
            "ADDYY": "Adidas",
        }
        if ticker.upper() in mapping:
            return mapping[ticker.upper()]

        # 2. Fetch from Yahoo Finance
        try:
            info = stock_obj.info
            # Try shortName first, then longName
            name = info.get('shortName') or info.get('longName')
            
            if name:
                # Clean up legal suffixes
                suffixes = [", Inc.", " Inc.", ", Inc", " Inc", " Corporation", " Corp.", " Corp", ", Ltd.", " Ltd.", " Ltd", " PLC", " plc", " N.V.", " S.A."]
                for suffix in suffixes:
                    if name.endswith(suffix):
                        name = name[:-len(suffix)]
                    # Also handle case-insensitive check if needed, but usually YF is title case
                
                return name
        except Exception as e:
            print(f"Error fetching brand name for {ticker}: {e}")
        
        # 3. Fallback to ticker
        return ticker

    def _fetch_news(self, stock_obj):
        """
        Fetches news from Yahoo Finance.
        """
        try:
            news = stock_obj.news
            
            formatted_items = []
            
            for item in news:
                content = item.get('content', item)
                title = content.get('title', 'No Title')
                if title == 'No Title': continue

                publisher = content.get('provider', {}).get('displayName', 'Yahoo Finance')
                link = content.get('clickThroughUrl', {}).get('url') or \
                       content.get('canonicalUrl', {}).get('url') or \
                       content.get('link')
                
                pub_time = content.get('providerPublishTime')
                if not pub_time:
                     pub_date = content.get('pubDate')
                     if pub_date:
                         try:
                             pub_time = int(datetime.fromisoformat(pub_date.replace('Z', '+00:00')).timestamp())
                         except:
                             pub_time = int(datetime.now().timestamp())
                     else:
                         pub_time = int(datetime.now().timestamp())

                summary = content.get('summary', title)

                formatted_items.append({
                    "id": content.get('uuid', str(hash(title))),
                    "title": title,
                    "text": summary,
                    "full_text": f"{title} {summary}",
                    "score": 0,
                    "url": link,
                    "created_utc": pub_time,
                    "subreddit": publisher,
                    "author": "News",
                    "source": "news",
                    "sentiment_label": "Neutral"
                })
            
            return formatted_items

        except Exception as e:
            print(f"Error fetching news: {e}")
            return []

    def _fetch_youtube(self, brand_name: str):
        """
        Fetches videos AND comments using Official API.
        Search Criteria: Brand Name, Last Month, Most Viewed.
        """
        if not self.youtube:
            return []
            
        try:
            # Calculate date 30 days ago (RFC 3339 format)
            published_after = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"
            
            # 1. Search for videos
            # Use quotes for exact phrase match as requested
            search_query = f'"{brand_name} Review"'
            
            search_response = self.youtube.search().list(
                q=search_query,
                part="id,snippet",
                maxResults=5,
                type="video",
                order="viewCount",  # Most viewed
                publishedAfter=published_after, # Last month
                relevanceLanguage='en' # Restrict to English
            ).execute()
            
            formatted_items = []
            
            for item in search_response.get("items", []):
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]
                desc = item["snippet"]["description"]
                channel = item["snippet"]["channelTitle"]
                published_at = item["snippet"]["publishedAt"]
                
                # Parse time
                try:
                    dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                    created_utc = int(dt.timestamp())
                except:
                    created_utc = int(datetime.now().timestamp())

                # 2. Fetch top comments for this video
                comments_text = ""
                comments_list = []
                try:
                    comment_response = self.youtube.commentThreads().list(
                        part="snippet",
                        videoId=video_id,
                        maxResults=5, # Top 5 comments
                        textFormat="plainText",
                        order="relevance"
                    ).execute()
                    
                    for c_item in comment_response.get("items", []):
                        comment = c_item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                        comments_list.append(comment)
                    
                    comments_text = " ".join(comments_list)
                except Exception:
                    pass

                # Combine for full text analysis
                full_text = f"{title} {desc} {comments_text}"
                
                formatted_items.append({
                    "id": video_id,
                    "title": title,
                    "text": desc or f"Video by {channel}",
                    "full_text": full_text,
                    "score": 0,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "created_utc": created_utc,
                    "subreddit": "YouTube",
                    "author": channel,
                    "source": "youtube",
                    "sentiment_label": "Neutral",
                    "comments": comments_list
                })
                
            return formatted_items
            
        except Exception as e:
            print(f"Error fetching YouTube API for {brand_name}: {e}")
            return []

    def _analyze_sentiment(self, items):
        """
        Analyzes a list of items (news/posts) to compute NSS, emotions, and trends.
        """
        total = len(items)
        if total == 0:
            return {
                "nss": 0,
                "distribution": {"positive": 0, "neutral": 0, "negative": 0, "total": 0},
                "emotions": {},
                "keywords": []
            }
            
        pos_count = 0
        neg_count = 0
        neu_count = 0
        
        all_text = ""
        emotions_counter = Counter()
        
        # Simple emotion lexicon
        emotion_keywords = {
            "Admiration": ["good", "great", "impressive", "best", "amazing", "upgrade", "buy", "outperform", "bull", "bullish"],
            "Trust": ["strong", "solid", "reliable", "growth", "beat", "profit", "stable", "moat"],
            "Frustration": ["bad", "terrible", "worst", "miss", "loss", "down", "sell", "debt", "risk", "lawsuit", "crash", "bear", "bearish"],
            "Excitement": ["soar", "surge", "jump", "record", "high", "rally", "rocket", "moon"],
            "Uncertainty": ["volatile", "unknown", "uncertain", "maybe", "could", "pending", "wait"]
        }

        for item in items:
            text = item["full_text"]
            all_text += " " + text
            
            # VADER Score
            scores = self.analyzer.polarity_scores(text)
            compound = scores['compound']
            
            if compound >= 0.05:
                pos_count += 1
                item["sentiment_label"] = "Positive"
            elif compound <= -0.05:
                neg_count += 1
                item["sentiment_label"] = "Negative"
            else:
                neu_count += 1
                item["sentiment_label"] = "Neutral"
                
            item["sentiment_score"] = compound
            
            # Emotion detection
            words = re.findall(r'\w+', text.lower())
            for emotion, keywords in emotion_keywords.items():
                if any(k in words for k in keywords):
                    emotions_counter[emotion] += 1

        nss = ((pos_count - neg_count) / total) * 100
        
        # Trends (Keywords)
        words = re.findall(r'\w+', all_text.lower())
        stop_words = {"the", "and", "a", "to", "of", "in", "is", "it", "my", "on", "for", "with", "this", "that", "but", "are", "be", "so", "or", "at", "as", "if", "not", "just", "have", "you", "i", "me", "stock", "shares", "market", "news", "finance", "video", "channel", "watch", "analysis", "price", "vs"}
        filtered_words = [w for w in words if w not in stop_words and len(w) > 3 and not w.isdigit()]
        
        common_words = Counter(filtered_words).most_common(10)
        keywords_list = [{"text": w, "value": c} for w, c in common_words]

        return {
            "nss": round(nss, 2),
            "distribution": {
                "positive": pos_count,
                "neutral": neu_count,
                "negative": neg_count,
                "total": total
            },
            "emotions": dict(emotions_counter),
            "keywords": keywords_list
        }
