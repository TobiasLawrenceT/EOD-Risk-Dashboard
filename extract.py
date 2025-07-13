from pathlib import Path
from zoneinfo import ZoneInfo 
import datetime as dt
import pandas as pd
import yfinance as yf
from setup import portofolio, data_path, benchmarks

HKT = ZoneInfo("Asia/Hong_Kong")

def is_market_closed(now):
    close_bell = now.replace(hour=18, minute=0, second=0, microsecond=0)
    return now >= close_bell

def fetch_price_matrix(tickers, start_date, end_date):
    frames = pd.DataFrame()
    errors = []
    
    print(f"Getting data for {len(tickers)} tickers from {start_date} to {end_date}...")

    for tkr in tickers:
        try:
            df = yf.download(
                tkr,
                start=start_date,
                end=end_date,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            if df.empty:
                raise ValueError("no data")
            price_series = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]
            frames[tkr] = price_series
            print(f"Success: {tkr:<8} {price_series.shape[0]} rows")
        except Exception as e:
            errors.append((tkr, str(e)))
            print(f"Fail: {tkr:<8} {e}")
    
    frames = frames.sort_index().ffill()
    frames.index.name = "date"
    return frames, errors

def main():
    now_hk = dt.datetime.now(HKT)
    if not is_market_closed(now_hk):
        print("Too early – markets not closed yet")
        raise SystemExit

    tickers = list(portofolio.keys()) + list(benchmarks.values())
    end_date = now_hk.date() + dt.timedelta(days=1)  # yfinance non-inclusive
    start_date = end_date - dt.timedelta(days=750)

    output_file = Path(data_path)/"prices.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    frames, errors = fetch_price_matrix(tickers, start_date, end_date)
    frames.to_csv(output_file)
    print(f"\nSaved price matrix {frames.shape} to {output_file}")

    if errors:
        print(f"\n{len(errors)} errors occurred:")
        for tkr, msg in errors:
            print(f"  {tkr}: {msg}")

if __name__ == "__main__":
    main()