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


DATA_DIR = Path(__file__).resolve().parent
TICKERS = ("AAPL", "AMZN", "GOOG", "MSFT", "TSLA")
COMPANY_NAMES = {
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "GOOG": "Alphabet",
    "MSFT": "Microsoft",
    "TSLA": "Tesla",
}
CSV_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
DEFAULT_START_DATE = "2020-01-02"


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


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    featured = df.copy()
    featured["DateOrdinal"] = featured["Date"].map(pd.Timestamp.toordinal)
    featured["Daily_Return"] = featured["Adj Close"].pct_change()
    featured["MA_5"] = featured["Adj Close"].rolling(window=5).mean()
    featured["MA_20"] = featured["Adj Close"].rolling(window=20).mean()
    featured["Volume_Change"] = featured["Volume"].pct_change()
    return featured


def train_random_forest(ticker: str) -> tuple[StockResult, pd.DataFrame, Pipeline]:
    df = add_features(load_stock_data(ticker))
    feature_columns = [
        "DateOrdinal",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Daily_Return",
        "MA_5",
        "MA_20",
        "Volume_Change",
    ]

    X = df[feature_columns]
    y = df["Adj Close"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = Pipeline(
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
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    latest_features = X.iloc[[-1]]
    next_close = float(model.predict(latest_features)[0])
    latest_close = float(y.iloc[-1])

    evaluation = pd.DataFrame(
        {
            "Date": df.loc[X_test.index, "Date"],
            "Actual": y_test.to_numpy(),
            "Predicted": predictions,
        }
    )

    result = StockResult(
        ticker=ticker.upper(),
        latest_close=latest_close,
        predicted_next_close=next_close,
        mse=float(mean_squared_error(y_test, predictions)),
        mae=float(mean_absolute_error(y_test, predictions)),
        r2=float(r2_score(y_test, predictions)),
    )
    return result, evaluation, model


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
