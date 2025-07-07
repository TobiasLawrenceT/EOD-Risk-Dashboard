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
start_date = end_date - dt.timedelta(days=365)      # 1-year back-fill
output_file = Path(data_path)/"prices.csv"

def fetch_close(tkr: str, start_date: dt.date, end_date: dt.date) -> pd.Series:
    """Fetch closing prices for a single ticker"""
    try:
        df = yf.download(
            tkr,
            start=start_date,
            end=end_date,
            interval="1d",
            auto_adjust=True,  # Use adjusted prices
            progress=False,
            threads=True,      # Enable parallel downloads
        )
        
        if df.empty or "Close" not in df.columns:
            raise ValueError(f"No data or Close column for {tkr}")
            
        s = df["Close"].copy()
        s.name = tkr  # Set series name to ticker
        return s
        
    except Exception as e:
        raise ValueError(f"Failed to download {tkr}: {str(e)}")

def main():
    frames = []
    errors = []
    
    print(f"Fetching data for {len(tickers)} tickers from {start_date} to {end_date}...")
    
    for tkr in tickers:
        try:
            series = fetch_close(tkr, start_date, end_date)
            frames.append(series)
            print(f"✓ {tkr:5} fetched ({series.shape[0]} rows)")
        except Exception as e:
            errors.append((tkr, str(e)))
            print(f"✗ {tkr:5} failed: {e}")

    if not frames:
        print("No data pulled — aborting.")
        return

    # Combine all series into a DataFrame
    close_df = pd.concat(frames, axis=1).sort_index()
    close_df.index.name = "date"
    
    # Handle weekends/missing data
    close_df = close_df.ffill()  # Forward fill missing values
    
    # Save to CSV
    output_file.parent.mkdir(parents=True, exist_ok=True)
    close_df.to_csv(output_file)
    print(f"\nSaved price matrix {close_df.shape} to {output_file}")

    if errors:
        print(f"\n{len(errors)} errors occurred:")
        for tkr, msg in errors:
            print(f"  {tkr}: {msg}")

if __name__ == "__main__":
    main()