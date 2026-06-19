from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv
from newsapi import NewsApiClient
from textblob import TextBlob
import yfinance as yf

from stock_analysis import TICKERS

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


def _analyze_sentiment(text: str) -> str:
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0:
        return "positive"
    if polarity < 0:
        return "negative"
    return "neutral"


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
    return [
        NewsArticle(
            title=article.get("title") or "Untitled",
            source=(article.get("source") or {}).get("name") or "Unknown",
            published_at=_format_published_at(article.get("publishedAt")),
            url=article.get("url") or "",
            sentiment=_analyze_sentiment(article.get("title") or ""),
        )
        for article in articles
        if article.get("title")
    ]


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

        results.append(
            NewsArticle(
                title=title,
                source=source,
                published_at=_format_timestamp(published),
                url=url,
                sentiment=_analyze_sentiment(summary),
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

    raise RuntimeError(f"No news articles found for {ticker}.")
