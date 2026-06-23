from __future__ import annotations

from news_service import NewsArticle


def generate_news_insights(
    ticker: str,
    company: str,
    articles: list[NewsArticle] | list[dict],
    price_change: float,
    price_change_pct: float,
) -> dict:
    if not articles:
        return {
            "summary": f"No recent news found for {company}. Price moved {price_change_pct:+.2f}% without identifiable headline drivers in our feed.",
            "bullets": [
                "News data is unavailable or limited for this ticker right now.",
                f"The stock still moved {price_change:+.2f} USD ({price_change_pct:+.2f}%) on the latest session.",
            ],
        }

    def get(item, key, default=""):
        return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)

    positive = [a for a in articles if get(a, "sentiment") == "positive"]
    negative = [a for a in articles if get(a, "sentiment") == "negative"]
    neutral = [a for a in articles if get(a, "sentiment") == "neutral"]
    avg_polarity = sum(float(get(a, "polarity", 0)) for a in articles) / len(articles)

    direction_word = "rose" if price_change >= 0 else "fell"
    bullets: list[str] = []

    if price_change >= 0 and len(positive) >= len(negative):
        bullets.append(
            f"{company} ({ticker}) {direction_word} {abs(price_change_pct):.2f}% with predominantly "
            f"{'bullish' if len(positive) > len(negative) else 'mixed'} news "
            f"({len(positive)} positive, {len(negative)} negative headlines)."
        )
    elif price_change < 0 and len(negative) >= len(positive):
        bullets.append(
            f"{company} ({ticker}) {direction_word} {abs(price_change_pct):.2f}% alongside "
            f"bearish headline flow ({len(negative)} negative vs {len(positive)} positive articles)."
        )
    else:
        bullets.append(
            f"{company} ({ticker}) {direction_word} {abs(price_change_pct):.2f}% while news sentiment "
            f"was mixed — headlines may not fully explain the latest move."
        )

    if avg_polarity > 0.05:
        bullets.append(
            f"Average headline polarity is positive ({avg_polarity:+.2f}), which typically supports "
            "buy-side confidence and can contribute to upward pressure."
        )
    elif avg_polarity < -0.05:
        bullets.append(
            f"Average headline polarity is negative ({avg_polarity:+.2f}), which can increase selling "
            "pressure and weigh on the near-term price."
        )
    else:
        bullets.append(
            f"Headline polarity is near neutral ({avg_polarity:+.2f}), so technical and fundamental "
            "factors likely drove most of the recent price action."
        )

    for article in articles[:4]:
        title = get(article, "title")
        sentiment = get(article, "sentiment", "neutral")
        tone = {"positive": "bullish", "negative": "bearish", "neutral": "neutral"}.get(
            sentiment, "neutral"
        )
        if sentiment == "positive" and price_change >= 0:
            effect = "supporting the gain"
        elif sentiment == "negative" and price_change < 0:
            effect = "consistent with the decline"
        elif sentiment == "positive" and price_change < 0:
            effect = "contrasting with the price drop (other factors may dominate)"
        elif sentiment == "negative" and price_change >= 0:
            effect = "contrasting with the price rise (market may be looking past headlines)"
        else:
            effect = "offering limited directional signal"
        bullets.append(f"\"{title}\" — {tone} tone, {effect}.")

    summary = (
        f"Based on {len(articles)} recent articles, news sentiment is "
        f"{'bullish' if avg_polarity > 0.05 else 'bearish' if avg_polarity < -0.05 else 'neutral'} "
        f"while {company} {direction_word} {abs(price_change_pct):.2f}%."
    )

    return {"summary": summary, "bullets": bullets[:6]}
