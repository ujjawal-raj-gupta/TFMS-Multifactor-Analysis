from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from explainability import (
    FUNDAMENTAL_FEATURES,
    SENTIMENT_FEATURES,
    TECHNICAL_FEATURES,
)
from constants import COMPANY_NAMES, TICKERS
from fundamentals import fetch_fundamental_metrics
from news_service import fetch_sentiment_features


DATA_DIR = Path(__file__).resolve().parent
CSV_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
DEFAULT_START_DATE = "2020-01-02"
CHART_DAYS = 90

FEATURE_COLUMNS = list(TECHNICAL_FEATURES) + list(FUNDAMENTAL_FEATURES) + list(SENTIMENT_FEATURES)


@dataclass(frozen=True)
class StockResult:
    ticker: str
    latest_close: float
    predicted_next_close: float
    mse: float
    mae: float
    r2: float


@dataclass(frozen=True)
class PriceSnapshot:
    ticker: str
    company: str
    price: float
    previous_close: float
    change: float
    change_pct: float
    last_date: date


def _normalize_history(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.reset_index()
    if "Datetime" in normalized.columns:
        normalized = normalized.rename(columns={"Datetime": "Date"})
    elif "Date" not in normalized.columns and normalized.columns[0] != "Date":
        normalized = normalized.rename(columns={normalized.columns[0]: "Date"})

    if "Adj Close" not in normalized.columns:
        normalized["Adj Close"] = normalized["Close"]

    normalized["Date"] = pd.to_datetime(normalized["Date"]).dt.normalize()
    return normalized[CSV_COLUMNS].sort_values("Date").reset_index(drop=True)


def fetch_stock_history(
    ticker: str, start: str | date, end: str | date | None = None
) -> pd.DataFrame:
    end_date = end or (date.today() + timedelta(days=1))
    history = yf.download(
        ticker,
        start=str(start),
        end=str(end_date),
        auto_adjust=False,
        progress=False,
    )
    if history.empty:
        raise ValueError(f"No Yahoo Finance data returned for {ticker}")

    if isinstance(history.columns, pd.MultiIndex):
        history.columns = history.columns.get_level_values(0)

    return _normalize_history(history)


def update_stock_csv(ticker: str) -> pd.DataFrame:
    ticker = ticker.upper()
    path = DATA_DIR / f"{ticker}.csv"

    if path.exists():
        existing = load_stock_data(ticker)
        start = (existing["Date"].max().date() + timedelta(days=1)).isoformat()
        if start > date.today().isoformat():
            return existing
        new_rows = fetch_stock_history(ticker, start=start)
        combined = (
            pd.concat([existing, new_rows], ignore_index=True)
            .drop_duplicates(subset=["Date"], keep="last")
            .sort_values("Date")
            .reset_index(drop=True)
        )
    else:
        combined = fetch_stock_history(ticker, start=DEFAULT_START_DATE)

    combined["Date"] = combined["Date"].dt.strftime("%Y-%m-%d")
    combined.to_csv(path, index=False)
    combined["Date"] = pd.to_datetime(combined["Date"])
    return combined


def update_all_stock_data() -> dict[str, pd.DataFrame]:
    return {ticker: update_stock_csv(ticker) for ticker in TICKERS}


def get_price_snapshot(ticker: str) -> PriceSnapshot:
    df = load_stock_data(ticker)
    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else latest
    price = float(latest["Adj Close"])
    previous_close = float(previous["Adj Close"])
    change = price - previous_close
    change_pct = (change / previous_close * 100) if previous_close else 0.0
    return PriceSnapshot(
        ticker=ticker.upper(),
        company=COMPANY_NAMES[ticker.upper()],
        price=price,
        previous_close=previous_close,
        change=change,
        change_pct=change_pct,
        last_date=latest["Date"].date(),
    )


def load_stock_data(ticker: str) -> pd.DataFrame:
    ticker = ticker.upper()
    path = DATA_DIR / f"{ticker}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No CSV data found for ticker {ticker}")

    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def add_features(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    featured = df.copy()
    featured["Daily_Return"] = featured["Adj Close"].pct_change()
    featured["MA_5"] = featured["Adj Close"].rolling(window=5).mean()
    featured["MA_20"] = featured["Adj Close"].rolling(window=20).mean()
    featured["Volume_Change"] = featured["Volume"].pct_change()

    ma20 = featured["MA_20"].replace(0, np.nan)
    featured["Close_to_MA20"] = featured["Close"] / ma20
    featured["Open_to_MA20"] = featured["Open"] / ma20
    featured["High_to_MA20"] = featured["High"] / ma20
    featured["Low_to_MA20"] = featured["Low"] / ma20
    featured["MA5_to_MA20"] = featured["MA_5"] / ma20

    fundamentals = fetch_fundamental_metrics(ticker)
    for key, value in fundamentals.items():
        featured[key] = value

    sentiment = fetch_sentiment_features(ticker)
    featured["Sentiment_Score"] = sentiment["Sentiment_Score"]
    featured["Sentiment_Positive_Ratio"] = sentiment["Sentiment_Positive_Ratio"]

    featured["Next_Close"] = featured["Adj Close"].shift(-1)
    featured["Next_Date"] = featured["Date"].shift(-1)
    return featured


def _prepare_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    working = df.iloc[:-1].copy()
    base_close = df.loc[working.index, "Adj Close"].to_numpy(dtype=float)
    working["Base_Close"] = base_close
    working["Next_Return"] = working["Next_Close"].to_numpy(dtype=float) / base_close - 1.0
    working = working.dropna(subset=FEATURE_COLUMNS + ["Next_Close", "Next_Date", "Next_Return"])
    return working.reset_index(drop=True)


def _returns_to_prices(base_close: np.ndarray, pred_returns: np.ndarray) -> np.ndarray:
    return base_close * (1.0 + pred_returns)


def _build_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=200,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def train_random_forest(
    ticker: str,
) -> tuple[StockResult, pd.DataFrame, Pipeline, pd.DataFrame]:
    ticker = ticker.upper()
    raw = add_features(load_stock_data(ticker), ticker)
    model_df = _prepare_model_frame(raw)

    X = model_df[FEATURE_COLUMNS]
    y_return = model_df["Next_Return"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_return, test_size=0.2, shuffle=False
    )

    model = _build_model()
    model.fit(X_train, y_train)

    pred_returns = model.predict(X_test)
    test_base = model_df.loc[y_test.index, "Base_Close"].to_numpy(dtype=float)
    pred_prices = _returns_to_prices(test_base, pred_returns)
    actual_prices = model_df.loc[y_test.index, "Next_Close"].to_numpy(dtype=float)

    latest_features = X.iloc[[-1]]
    latest_base = float(model_df["Base_Close"].iloc[-1])
    latest_return = float(model.predict(latest_features)[0])
    next_close = float(latest_base * (1.0 + latest_return))
    latest_close = float(raw["Adj Close"].iloc[-1])

    evaluation = pd.DataFrame(
        {
            "Date": model_df.loc[y_test.index, "Next_Date"].to_numpy(),
            "Actual": actual_prices,
            "Predicted": pred_prices,
        }
    )

    result = StockResult(
        ticker=ticker,
        latest_close=latest_close,
        predicted_next_close=next_close,
        mse=float(mean_squared_error(actual_prices, pred_prices)),
        mae=float(mean_absolute_error(actual_prices, pred_prices)),
        r2=float(r2_score(actual_prices, pred_prices)),
    )
    return result, evaluation, model, model_df


def get_90day_actual_vs_predicted(
    ticker: str,
    model: Pipeline | None = None,
    model_df: pd.DataFrame | None = None,
) -> dict:
    ticker = ticker.upper()
    if model_df is None:
        _, _, model, model_df = train_random_forest(ticker)

    split = max(len(model_df) - CHART_DAYS, int(len(model_df) * 0.6))
    chart_model = _build_model()
    chart_model.fit(
        model_df.iloc[:split][FEATURE_COLUMNS],
        model_df.iloc[:split]["Next_Return"],
    )

    window = model_df.iloc[split:].tail(CHART_DAYS)
    pred_returns = chart_model.predict(window[FEATURE_COLUMNS])
    base_close = window["Base_Close"].to_numpy(dtype=float)
    predicted = _returns_to_prices(base_close, pred_returns)
    actual = window["Next_Close"].to_numpy(dtype=float)

    return {
        "ticker": ticker,
        "dates": [pd.Timestamp(d).strftime("%Y-%m-%d") for d in window["Next_Date"]],
        "actual": [round(float(v), 2) for v in actual],
        "predicted": [round(float(v), 2) for v in predicted],
    }


def run_all_random_forests() -> pd.DataFrame:
    results = [train_random_forest(ticker)[0] for ticker in TICKERS]
    return pd.DataFrame([result.__dict__ for result in results])


def correlation_summary(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame(columns=["Metric", "Correlation With Latest Close"])

    metrics = ["predicted_next_close", "mse", "mae", "r2"]
    rows = []
    for metric in metrics:
        correlation = np.nan
        if results[metric].nunique(dropna=True) > 1:
            correlation = results[metric].corr(results["latest_close"])
        rows.append(
            {
                "Metric": metric,
                "Correlation With Latest Close": correlation,
            }
        )
    return pd.DataFrame(rows)
