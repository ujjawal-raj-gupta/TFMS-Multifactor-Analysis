from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime

from dotenv import load_dotenv
from newsapi import NewsApiClient
from textblob import TextBlob
import yfinance as yf

from constants import TICKERS

load_dotenv()

TICKER_QUERY = {
    "AAPL": "Apple stock OR AAPL",
    "AMZN": "Amazon stock OR AMZN",
    "GOOG": "Alphabet OR Google stock OR GOOG",
    "MSFT": "Microsoft stock OR MSFT",
    "TSLA": "Tesla stock OR TSLA",
}


@dataclass(frozen=True)
class NewsArticle:
    title: str
    source: str
    published_at: str
    url: str
    sentiment: str
    polarity: float


def _sentiment_label(polarity: float) -> str:
    if polarity > 0:
        return "positive"
    if polarity < 0:
        return "negative"
    return "neutral"


def _analyze_sentiment(text: str) -> tuple[str, float]:
    polarity = float(TextBlob(text).sentiment.polarity)
    return _sentiment_label(polarity), polarity


def _format_published_at(value: str | None) -> str:
    if not value:
        return "Unknown date"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime(
            "%b %d, %Y"
        )
    except ValueError:
        return value


def _format_timestamp(value: int | float | str | None) -> str:
    if value is None:
        return "Unknown date"
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value).strftime("%b %d, %Y")
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime(
                "%b %d, %Y"
            )
        return "Unknown date"
    except (ValueError, OSError, OverflowError):
        return "Unknown date"


def _fetch_newsapi_articles(ticker: str, page_size: int) -> list[NewsArticle]:
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key or api_key == "your_key_here":
        return []

    newsapi = NewsApiClient(api_key=api_key)
    response = newsapi.get_everything(
        q=TICKER_QUERY[ticker],
        language="en",
        sort_by="publishedAt",
        page_size=page_size,
    )
    articles = response.get("articles", [])
    results: list[NewsArticle] = []
    for article in articles:
        title = article.get("title") or ""
        if not title:
            continue
        sentiment, polarity = _analyze_sentiment(title)
        results.append(
            NewsArticle(
                title=title,
                source=(article.get("source") or {}).get("name") or "Unknown",
                published_at=_format_published_at(article.get("publishedAt")),
                url=article.get("url") or "",
                sentiment=sentiment,
                polarity=round(polarity, 4),
            )
        )
    return results


def _fetch_yfinance_articles(ticker: str, page_size: int) -> list[NewsArticle]:
    raw_articles = yf.Ticker(ticker).news or []
    results: list[NewsArticle] = []
    for item in raw_articles[:page_size]:
        article = item.get("content", item)
        title = article.get("title") or article.get("headline") or ""
        if not title:
            continue

        summary = article.get("summary") or article.get("description") or title
        provider = article.get("provider") or {}
        source = provider.get("displayName") or article.get("publisher") or "Yahoo Finance"

        canonical = article.get("canonicalUrl") or {}
        url = (
            canonical.get("url")
            or article.get("link")
            or article.get("url")
            or ""
        )

        published = (
            article.get("pubDate")
            or article.get("displayTime")
            or article.get("providerPublishTime")
        )
        sentiment, polarity = _analyze_sentiment(summary)

        results.append(
            NewsArticle(
                title=title,
                source=source,
                published_at=_format_timestamp(published),
                url=url,
                sentiment=sentiment,
                polarity=round(polarity, 4),
            )
        )
    return results


def fetch_company_news(ticker: str, page_size: int = 8) -> list[NewsArticle]:
    ticker = ticker.upper()
    if ticker not in TICKERS:
        raise ValueError(f"Unsupported ticker: {ticker}")

    articles = _fetch_newsapi_articles(ticker, page_size)
    if articles:
        return articles

    articles = _fetch_yfinance_articles(ticker, page_size)
    if articles:
        return articles

    return []


def fetch_sentiment_features(ticker: str) -> dict[str, float]:
    articles = fetch_company_news(ticker, page_size=8)
    if not articles:
        return {"Sentiment_Score": 0.0, "Sentiment_Positive_Ratio": 0.0}

    polarities = [article.polarity for article in articles]
    positive_count = sum(1 for article in articles if article.sentiment == "positive")
    return {
        "Sentiment_Score": round(float(sum(polarities) / len(polarities)), 4),
        "Sentiment_Positive_Ratio": round(positive_count / len(articles), 4),
    }


def fetch_all_news(page_size: int = 6) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for ticker in TICKERS:
        articles = fetch_company_news(ticker, page_size=page_size)
        grouped[ticker] = [asdict(article) for article in articles]
    return grouped


def article_to_dict(article: NewsArticle) -> dict:
    return asdict(article)
