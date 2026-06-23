from __future__ import annotations

from constants import COMPANY_NAMES, SEARCH_ALIASES, TICKERS


def search_tickers(query: str) -> list[dict]:
    query = query.strip().lower()
    if not query:
        return [
            {"ticker": t, "company": COMPANY_NAMES[t], "label": f"{COMPANY_NAMES[t]} ({t})"}
            for t in TICKERS
        ]

    matches: list[dict] = []
    seen: set[str] = set()

    for alias, ticker in SEARCH_ALIASES.items():
        if query in alias or alias.startswith(query):
            if ticker not in seen:
                seen.add(ticker)
                matches.append(
                    {
                        "ticker": ticker,
                        "company": COMPANY_NAMES[ticker],
                        "label": f"{COMPANY_NAMES[ticker]} ({ticker})",
                    }
                )

    for ticker in TICKERS:
        company = COMPANY_NAMES[ticker].lower()
        if query in ticker.lower() or query in company:
            if ticker not in seen:
                seen.add(ticker)
                matches.append(
                    {
                        "ticker": ticker,
                        "company": COMPANY_NAMES[ticker],
                        "label": f"{COMPANY_NAMES[ticker]} ({ticker})",
                    }
                )

    return matches


def resolve_ticker(query: str) -> str | None:
    matches = search_tickers(query)
    if not matches:
        return None
    exact = query.strip().upper()
    for match in matches:
        if match["ticker"] == exact:
            return match["ticker"]
    alias = SEARCH_ALIASES.get(query.strip().lower())
    if alias:
        return alias
    return matches[0]["ticker"]
