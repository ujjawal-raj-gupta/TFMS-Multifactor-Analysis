from __future__ import annotations

import argparse

from stock_analysis import (
    TICKERS,
    correlation_summary,
    run_all_random_forests,
    update_all_stock_data,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run multifactor stock analysis on the local CSV data."
    )
    parser.add_argument(
        "--ticker",
        choices=TICKERS,
        help="Limit printed results to a single ticker.",
    )
    parser.add_argument(
        "--update-data",
        action="store_true",
        help="Download the latest Yahoo Finance data into the local CSV files.",
    )
    args = parser.parse_args()

    if args.update_data:
        updated = update_all_stock_data()
        print("\nUpdated stock data")
        for ticker, df in updated.items():
            last_date = df["Date"].max().date()
            print(f"  {ticker}: {len(df)} rows, latest {last_date}")
        if not args.ticker:
            return

    results = run_all_random_forests()
    if args.ticker:
        results = results[results["ticker"] == args.ticker]

    print("\nRandom Forest prediction summary")
    print(results.round(4).to_string(index=False))

    if not args.ticker:
        print("\nCorrelation summary")
        print(correlation_summary(results).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
