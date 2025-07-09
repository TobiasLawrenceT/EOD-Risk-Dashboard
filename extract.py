from pathlib import Path
from zoneinfo import ZoneInfo 
import datetime as dt
import pandas as pd
import yfinance as yf
from setup import portofolio, data_path, benchmarks

#Tracking current date and time
HKT = ZoneInfo("Asia/Hong_Kong")
now_hk   = dt.datetime.now(HKT)           # aware timestamp
risk_cut = now_hk.replace(hour=18, minute=0, second=0, microsecond=0)
if dt.datetime.now(HKT) < risk_cut:
    print("Too early – markets not closed yet")
    raise SystemExit
risk_date = dt.datetime.now(HKT).date()

tickers = list(portofolio.keys()) + list(benchmarks.values())
end_date = dt.date.today() + dt.timedelta(days=1)   # yfinance end is non-inclusive
start_date = end_date - dt.timedelta(days=750)      # 1-year back-fill
output_file = Path(data_path)/"prices.csv"

def main():
    # Usage (ensure end_date is defined)
    end_date = dt.datetime.now()  # Or your specific end date

    frames = pd.DataFrame()
    errors = []
    
    print(f"Fetching data for {len(tickers)} tickers from {start_date} to {end_date}...")
    
    for tkr in tickers:
        try:
            df = yf.download(
                tkr,
                start=start_date,
                end=end_date,
                auto_adjust=False,        # <- raw + adj cols
                progress=False,
                threads=False,
            )
            if df.empty:
                raise ValueError("no data")

            # choose Adj Close if present, otherwise Close
            price_series = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]
            price_series.name = tkr 
            frames[tkr] = price_series
            print(f"✓ {tkr:<8} {price_series.shape[0]} rows")
        except Exception as e:
            errors.append((tkr, str(e)))
            print(f"✗ {tkr:<8} {e}")
        
    #forward fill
    frames = frames.sort_index().ffill()
    frames.index.name = "date"
    # Save to CSV
    output_file.parent.mkdir(parents=True, exist_ok=True)
    frames.to_csv(output_file)
    print(f"\nSaved price matrix {frames.shape} to {output_file}")

    if errors:
        print(f"\n{len(errors)} errors occurred:")
        for tkr, msg in errors:
            print(f"  {tkr}: {msg}")

if __name__ == "__main__":
    main()