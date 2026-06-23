from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, render_template, request

from constants import PROJECT_HERO_NAME, PROJECT_HERO_SUBTITLE, PROJECT_TAGLINE, PROJECT_TITLE, TICKERS
from search_service import resolve_ticker, search_tickers
from web.data_bridge import (
    build_stock_payload,
    get_dashboard_data,
    write_cache,
)

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


@app.route("/")
def index():
    return render_template(
        "index.html",
        tickers=TICKERS,
        project_title=PROJECT_TITLE,
        project_hero_name=PROJECT_HERO_NAME,
        project_hero_subtitle=PROJECT_HERO_SUBTITLE,
        project_tagline=PROJECT_TAGLINE,
    )


@app.route("/api/dashboard-data")
def api_dashboard_data():
    refresh = request.args.get("refresh", "").lower() in {"1", "true", "yes"}
    return jsonify(get_dashboard_data(refresh=refresh))


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "")
    return jsonify({"results": search_tickers(query)})


@app.route("/api/stock/<ticker>")
def api_stock(ticker: str):
    resolved = resolve_ticker(ticker) or ticker.upper()
    if resolved not in TICKERS:
        return jsonify({"error": f"Stock not found: {ticker}. Try Apple, Amazon, Google, Microsoft, or Tesla."}), 404
    return jsonify(build_stock_payload(resolved))


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    from web.data_bridge import _trained_model

    _trained_model.cache_clear()
    payload = write_cache()
    return jsonify(payload)


if __name__ == "__main__":
    print("Starting TFMS dashboard at http://localhost:5000")
    write_cache()
    app.run(debug=True, port=5000)
