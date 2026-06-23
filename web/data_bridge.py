from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from explainability import explain_prediction
from fundamentals import fetch_fundamental_display
from news_insights import generate_news_insights
from news_service import fetch_all_news, fetch_company_news, fetch_sentiment_features
from constants import COMPANY_NAMES, TICKERS
from stock_analysis import (
    FEATURE_COLUMNS,
    get_90day_actual_vs_predicted,
    get_price_snapshot,
    train_random_forest,
)

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_FILE = CACHE_DIR / "dashboard_data.json"


@lru_cache(maxsize=len(TICKERS))
def _trained_model(ticker: str):
    result, evaluation, model, df = train_random_forest(ticker)
    return result, evaluation, model, df


def build_ticker_summary(ticker: str) -> dict:
    snapshot = get_price_snapshot(ticker)
    result, _, _, _ = _trained_model(ticker)
    sentiment = fetch_sentiment_features(ticker)
    return {
        "ticker": ticker,
        "company": COMPANY_NAMES[ticker],
        "price": round(snapshot.price, 2),
        "previous_close": round(snapshot.previous_close, 2),
        "change": round(snapshot.change, 2),
        "change_pct": round(snapshot.change_pct, 2),
        "last_date": snapshot.last_date.isoformat(),
        "predicted_next_close": round(result.predicted_next_close, 2),
        "mae": round(result.mae, 2),
        "r2": round(result.r2, 3),
        "sentiment_score": sentiment["Sentiment_Score"],
    }


def build_chart_payload(ticker: str) -> dict:
    result, _, model, df = _trained_model(ticker)
    chart = get_90day_actual_vs_predicted(ticker, model_df=df)
    chart["metrics"] = {
        "mae": round(result.mae, 2),
        "r2": round(result.r2, 3),
        "mse": round(result.mse, 2),
        "latest_close": round(result.latest_close, 2),
        "predicted_next_close": round(result.predicted_next_close, 2),
    }
    return chart


def build_news_payload(ticker: str) -> dict:
    summary = build_ticker_summary(ticker)
    articles = fetch_company_news(ticker)
    article_dicts = [asdict(a) for a in articles]
    insights = generate_news_insights(
        ticker=ticker,
        company=summary["company"],
        articles=article_dicts,
        price_change=summary["change"],
        price_change_pct=summary["change_pct"],
    )
    return {
        "articles": article_dicts,
        "insights": insights,
    }


def build_explanation(ticker: str) -> dict:
    result, _, model, df = _trained_model(ticker)
    latest_features = df[FEATURE_COLUMNS].iloc[[-1]]
    fundamentals = fetch_fundamental_display(ticker)
    sentiment = fetch_sentiment_features(ticker)
    explanation = explain_prediction(
        model=model,
        feature_columns=FEATURE_COLUMNS,
        latest_features=latest_features,
        model_df=df,
        ticker=ticker,
        latest_close=result.latest_close,
        predicted_next_close=result.predicted_next_close,
        fundamentals=fundamentals,
        sentiment=sentiment,
    )
    explanation["fundamentals"] = fundamentals
    explanation["sentiment"] = sentiment
    return explanation


def build_stock_payload(ticker: str) -> dict:
    ticker = ticker.upper()
    return {
        "summary": build_ticker_summary(ticker),
        "chart": build_chart_payload(ticker),
        "explanation": build_explanation(ticker),
        "news": build_news_payload(ticker),
    }


def build_dashboard_payload() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tickers": list(TICKERS),
    }


def write_cache(payload: dict | None = None) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = payload or build_dashboard_payload()
    CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def read_cache() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    return json.loads(CACHE_FILE.read_text(encoding="utf-8"))


def get_dashboard_data(refresh: bool = False) -> dict:
    if refresh:
        _trained_model.cache_clear()
        return write_cache(build_dashboard_payload())
    cached = read_cache()
    if cached:
        return cached
    return write_cache()


def snapshot_to_dict(obj) -> dict:
    return asdict(obj)
