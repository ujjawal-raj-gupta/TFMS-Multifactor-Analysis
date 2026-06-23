from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline

TECHNICAL_FEATURES = (
    "Close_to_MA20",
    "Open_to_MA20",
    "High_to_MA20",
    "Low_to_MA20",
    "Daily_Return",
    "MA5_to_MA20",
    "Volume_Change",
    "Volume",
)

FUNDAMENTAL_FEATURES = (
    "PE_Ratio",
    "Forward_PE",
    "Profit_Margin",
    "Revenue_Growth",
    "Debt_To_Equity",
    "ROE",
    "Market_Cap_Log",
)

SENTIMENT_FEATURES = (
    "Sentiment_Score",
    "Sentiment_Positive_Ratio",
)

FEATURE_GROUPS = {
    "technical": TECHNICAL_FEATURES,
    "fundamental": FUNDAMENTAL_FEATURES,
    "sentiment": SENTIMENT_FEATURES,
}

FUNDAMENTAL_LABELS = {
    "PE_Ratio": "P/E Ratio",
    "Forward_PE": "Forward P/E",
    "Profit_Margin": "Profit Margin",
    "Revenue_Growth": "Revenue Growth",
    "Debt_To_Equity": "Debt/Equity",
    "ROE": "Return on Equity",
    "Market_Cap_Log": "Market Cap (log)",
}


def _group_for_feature(name: str) -> str:
    for group, features in FEATURE_GROUPS.items():
        if name in features:
            return group
    return "technical"


def _hybrid_fundamental_impact(
    fundamentals: dict | None,
) -> tuple[float, list[dict]]:
    fundamentals = fundamentals or {}
    benchmarks = {
        "pe_ratio": (25.0, "P/E Ratio", lambda v, b: -0.012 if v > b * 1.3 else 0.008 if v < b * 0.8 else 0.0),
        "forward_pe": (22.0, "Forward P/E", lambda v, b: -0.01 if v > b * 1.3 else 0.007 if v < b * 0.85 else 0.0),
        "profit_margin": (0.15, "Profit Margin", lambda v, b: 0.015 if v > b else -0.01 if v < b * 0.5 else 0.0),
        "revenue_growth": (0.10, "Revenue Growth", lambda v, b: 0.012 if v > b else -0.008 if v < 0 else 0.0),
        "roe": (0.15, "ROE", lambda v, b: 0.01 if v > b else -0.006 if v < b * 0.5 else 0.0),
        "debt_to_equity": (80.0, "Debt/Equity", lambda v, b: -0.008 if v > b else 0.004 if v < b * 0.5 else 0.0),
    }
    top_features: list[dict] = []
    total = 0.0
    for key, (benchmark, label, scorer) in benchmarks.items():
        value = float(fundamentals.get(key, 0) or 0)
        if not value:
            continue
        impact = float(scorer(value, benchmark))
        total += abs(impact)
        top_features.append(
            {
                "name": label,
                "impact": round(impact, 6),
                "value": round(value, 4),
                "baseline": round(benchmark, 4),
            }
        )
    top = sorted(top_features, key=lambda x: abs(x["impact"]), reverse=True)[:3]
    return total, top


def _hybrid_sentiment_impact(
    sentiment: dict | None,
    model: Pipeline,
    latest_features: pd.DataFrame,
    model_df: pd.DataFrame,
) -> tuple[float, list[dict]]:
    sentiment = sentiment or {}
    score = float(sentiment.get("Sentiment_Score", 0))
    ratio = float(sentiment.get("Sentiment_Positive_Ratio", 0))

    cf_row = latest_features.copy()
    for name in SENTIMENT_FEATURES:
        if name in cf_row.columns:
            cf_row[name] = float(model_df[name].median())

    model_delta = abs(
        float(model.predict(cf_row)[0] - model.predict(latest_features)[0])
    )
    heuristic = abs(score) * 0.015 + abs(ratio - 0.5) * 0.01
    total = max(model_delta, heuristic)

    top_features = [
        {
            "name": "Sentiment Score",
            "impact": round(score * 0.015 if score else -0.001, 6),
            "value": round(score, 4),
            "baseline": 0.0,
        },
        {
            "name": "Positive News Ratio",
            "impact": round((ratio - 0.5) * 0.02, 6),
            "value": round(ratio, 4),
            "baseline": 0.5,
        },
    ]
    return total, top_features


def _technical_counterfactual_impact(
    model: Pipeline,
    baseline_row: pd.DataFrame,
    model_df: pd.DataFrame,
) -> float:
    modified_row = baseline_row.copy()
    for name in TECHNICAL_FEATURES:
        if name in modified_row.columns:
            modified_row[name] = float(model_df[name].median())
    return abs(
        float(model.predict(modified_row)[0] - model.predict(baseline_row)[0])
    )


def explain_prediction(
    model: Pipeline,
    feature_columns: list[str],
    latest_features: pd.DataFrame,
    model_df: pd.DataFrame,
    ticker: str,
    latest_close: float,
    predicted_next_close: float,
    fundamentals: dict | None = None,
    sentiment: dict | None = None,
) -> dict:
    regressor = model.named_steps["model"]
    imputed = model.named_steps["imputer"].transform(latest_features)
    explainer = shap.TreeExplainer(regressor)
    shap_values = explainer.shap_values(imputed)[0]

    tech_shap: list[dict] = []
    tech_total = 0.0
    for name, impact in zip(feature_columns, shap_values):
        if _group_for_feature(name) != "technical":
            continue
        abs_impact = abs(float(impact))
        tech_total += abs_impact
        tech_shap.append({"name": name, "impact": round(float(impact), 6)})

    fund_impact, fund_top = _hybrid_fundamental_impact(fundamentals)
    sent_impact, sent_top = _hybrid_sentiment_impact(
        sentiment, model, latest_features, model_df
    )

    if tech_total < 1e-6:
        tech_impact = _technical_counterfactual_impact(
            model, latest_features, model_df
        )
    else:
        tech_impact = tech_total

    total = tech_impact + fund_impact + sent_impact
    if total < 1e-9:
        total = 1.0

    groups_output = {
        "technical": {
            "pct": round(tech_impact / total * 100, 1),
            "top_features": sorted(tech_shap, key=lambda x: abs(x["impact"]), reverse=True)[:3],
        },
        "fundamental": {
            "pct": round(fund_impact / total * 100, 1),
            "top_features": fund_top,
        },
        "sentiment": {
            "pct": round(sent_impact / total * 100, 1),
            "top_features": sent_top or [
                {
                    "name": "Sentiment Score",
                    "impact": 0.0,
                    "value": round(float(sentiment.get("Sentiment_Score", 0)), 4)
                    if sentiment
                    else 0.0,
                    "baseline": 0.0,
                }
            ],
        },
    }

    direction = "upward" if predicted_next_close >= latest_close else "downward"
    dominant = max(groups_output, key=lambda g: groups_output[g]["pct"])

    fund_note = ""
    if fundamentals:
        pe = fundamentals.get("pe_ratio", 0)
        margin = fundamentals.get("profit_margin", 0)
        if pe:
            fund_note = f" Valuation (P/E {pe:.1f}) and profitability (margin {margin:.1%}) anchor the fundamental view."
        elif margin:
            fund_note = f" Profitability metrics (margin {margin:.1%}) anchor the fundamental view."

    sent_note = ""
    if sentiment:
        score = sentiment.get("Sentiment_Score", 0)
        sent_note = f" News sentiment score {score:+.2f} {'supports' if score > 0 else 'pressures' if score < 0 else 'neutrally affects'} the outlook."

    narrative = (
        f"The model forecasts ${predicted_next_close:.2f} for {ticker} ({direction} from "
        f"${latest_close:.2f}). {dominant.title()} factors drive {groups_output[dominant]['pct']:.1f}% "
        f"of the expected next-day return — technical {groups_output['technical']['pct']:.1f}%, "
        f"fundamental {groups_output['fundamental']['pct']:.1f}%, sentiment "
        f"{groups_output['sentiment']['pct']:.1f}%."
        f"{fund_note}{sent_note}"
    )

    return {
        "groups": groups_output,
        "narrative": narrative,
        "method": "SHAP for technical indicators; deviation-based scoring for fundamentals and sentiment.",
    }
