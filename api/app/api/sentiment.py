from fastapi import APIRouter, HTTPException
from app.services.sentiment_service import SentimentService

router = APIRouter()
sentiment_service = SentimentService()

@router.get("/{ticker}")
def get_brand_sentiment(ticker: str):
    """
    Fetches brand sentiment analysis using Yahoo Finance News.
    """
    try:
        data = sentiment_service.get_brand_sentiment(ticker)
        if not data:
             raise HTTPException(status_code=404, detail="Sentiment data not found")
        return data
    except Exception as e:
        print(f"Error fetching sentiment for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
