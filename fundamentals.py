from __future__ import annotations

import math

import yfinance as yf

FUNDAMENTAL_FIELDS = (
    "PE_Ratio",
    "Forward_PE",
    "Profit_Margin",
    "Revenue_Growth",
    "Debt_To_Equity",
    "ROE",
    "Market_Cap_Log",
)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def fetch_fundamental_metrics(ticker: str) -> dict[str, float]:
    info = yf.Ticker(ticker.upper()).info or {}
    market_cap = _safe_float(info.get("marketCap"))
    return {
        "PE_Ratio": _safe_float(info.get("trailingPE")),
        "Forward_PE": _safe_float(info.get("forwardPE")),
        "Profit_Margin": _safe_float(info.get("profitMargins")),
        "Revenue_Growth": _safe_float(info.get("revenueGrowth")),
        "Debt_To_Equity": _safe_float(info.get("debtToEquity")),
        "ROE": _safe_float(info.get("returnOnEquity")),
        "Market_Cap_Log": math.log(market_cap) if market_cap > 0 else 0.0,
    }


def fetch_fundamental_display(ticker: str) -> dict[str, str | float]:
    metrics = fetch_fundamental_metrics(ticker)
    return {
        "pe_ratio": metrics["PE_Ratio"],
        "forward_pe": metrics["Forward_PE"],
        "profit_margin": metrics["Profit_Margin"],
        "revenue_growth": metrics["Revenue_Growth"],
        "debt_to_equity": metrics["Debt_To_Equity"],
        "roe": metrics["ROE"],
        "market_cap_log": metrics["Market_Cap_Log"],
    }
