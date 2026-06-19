from __future__ import annotations

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from news_service import NewsArticle, fetch_company_news
from stock_analysis import (
    COMPANY_NAMES,
    TICKERS,
    PriceSnapshot,
    get_price_snapshot,
    load_stock_data,
    train_random_forest,
    update_all_stock_data,
)

load_dotenv()

st.set_page_config(page_title="TFMS Multifactor Analysis", layout="wide")

SENTIMENT_COLORS = {
    "positive": "#16a34a",
    "neutral": "#64748b",
    "negative": "#dc2626",
}


def _format_change(snapshot: PriceSnapshot) -> str:
    sign = "+" if snapshot.change >= 0 else ""
    return f"{sign}{snapshot.change:.2f} ({sign}{snapshot.change_pct:.2f}%)"


@st.cache_data(show_spinner="Loading news...")
def cached_news(ticker: str) -> list[NewsArticle]:
    return fetch_company_news(ticker)


@st.cache_data(show_spinner="Training model...")
def cached_analysis(ticker: str, data_version: str):
    result, evaluation, _ = train_random_forest(ticker)
    return result, evaluation


def render_news_panel(ticker: str) -> None:
    st.markdown("#### Latest News")
    try:
        articles = cached_news(ticker)
    except RuntimeError as exc:
        st.warning(str(exc))
        st.caption("Copy `.env.example` to `.env` and add your NewsAPI key.")
        return
    except Exception as exc:
        st.error(f"Could not load news for {ticker}: {exc}")
        return

    if not articles:
        st.info("No recent articles found.")
        return

    for article in articles:
        color = SENTIMENT_COLORS.get(article.sentiment, "#64748b")
        st.markdown(
            f"<span style='color:{color}; font-weight:600;'>"
            f"{article.sentiment.title()}</span> · "
            f"**{article.source}** · {article.published_at}",
            unsafe_allow_html=True,
        )
        if article.url:
            st.markdown(f"[{article.title}]({article.url})")
        else:
            st.write(article.title)
        st.divider()


def render_company_section(ticker: str, chart_days: int) -> None:
    snapshot = get_price_snapshot(ticker)
    history = load_stock_data(ticker)
    chart_history = history.tail(chart_days)
    data_version = history["Date"].max().isoformat()

    st.subheader(f"{COMPANY_NAMES[ticker]} ({ticker})")
    st.caption(f"Last updated: {snapshot.last_date.strftime('%b %d, %Y')}")

    left, right = st.columns([2, 1], gap="large")

    with left:
        metric_cols = st.columns(3)
        metric_cols[0].metric("Current Price", f"${snapshot.price:.2f}")
        metric_cols[1].metric("Previous Close", f"${snapshot.previous_close:.2f}")
        metric_cols[2].metric("Daily Change", _format_change(snapshot))

        chart_df = chart_history.set_index("Date")[["Adj Close"]]
        chart_df.index = pd.to_datetime(chart_df.index)
        st.line_chart(chart_df, height=280)

        analyze_key = f"analyze_{ticker}"
        if st.button("Analyze stock price", key=analyze_key, type="primary"):
            st.session_state[f"show_analysis_{ticker}"] = True

        if st.session_state.get(f"show_analysis_{ticker}"):
            result, evaluation = cached_analysis(ticker, data_version)
            pred_change = result.predicted_next_close - result.latest_close
            pred_pct = (
                pred_change / result.latest_close * 100 if result.latest_close else 0
            )
            sign = "+" if pred_change >= 0 else ""

            st.markdown("##### Random Forest Analysis")
            result_cols = st.columns(4)
            result_cols[0].metric("Latest Close", f"${result.latest_close:.2f}")
            result_cols[1].metric(
                "Predicted Next Close", f"${result.predicted_next_close:.2f}"
            )
            result_cols[2].metric("Expected Move", f"{sign}{pred_change:.2f}")
            result_cols[3].metric("Expected Move %", f"{sign}{pred_pct:.2f}%")

            detail_cols = st.columns(2)
            detail_cols[0].metric("MAE", f"{result.mae:.2f}")
            detail_cols[1].metric("R²", f"{result.r2:.3f}")

            comparison = evaluation.set_index("Date")[["Actual", "Predicted"]]
            comparison.index = pd.to_datetime(comparison.index)
            st.caption("Test set: actual vs predicted close")
            st.line_chart(comparison, height=220)

    with right:
        render_news_panel(ticker)


st.title("TFMS Multifactor Stock Analysis")
st.caption("Live prices, news sentiment, and on-demand Random Forest predictions.")

with st.sidebar:
    st.header("Controls")
    chart_days = st.slider("Chart history (days)", min_value=30, max_value=365, value=90)
    if st.button("Refresh market data", use_container_width=True):
        with st.spinner("Downloading latest Yahoo Finance data..."):
            update_all_stock_data()
            st.cache_data.clear()
        st.success("Market data refreshed.")
        st.rerun()
    st.divider()
    st.markdown("**News setup**")
    st.caption(
        "News loads from Yahoo Finance by default. Add a real `NEWS_API_KEY` in `.env` "
        "to use NewsAPI instead."
    )

snapshots = [get_price_snapshot(ticker) for ticker in TICKERS]
summary_cols = st.columns(len(TICKERS))
for col, snapshot in zip(summary_cols, snapshots):
    with col:
        st.metric(
            label=f"{snapshot.ticker}",
            value=f"${snapshot.price:.2f}",
            delta=f"{snapshot.change:.2f} ({snapshot.change_pct:.2f}%)",
        )

st.divider()

for index, ticker in enumerate(TICKERS):
    render_company_section(ticker, chart_days)
    if index < len(TICKERS) - 1:
        st.divider()
