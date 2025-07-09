import pandas as pd
import numpy as np
import xlsxwriter
from pathlib import Path
from setup import portofolio, ticker_currency, HKD_USD,JPY_USD

# Load prices data
try:
    base = Path(__file__).resolve().parents[0]
except NameError:
    base = Path.cwd()
data = base/"data"
prices = pd.read_csv(data/"prices.csv", index_col="date", parse_dates=True).sort_index()
# Clean column names (remove any whitespace or BOM characters)
prices.columns = prices.columns.str.strip().str.lstrip('\ufeff')
# Filter to only include portfolio tickers
valid_tickers = [t for t in prices.columns if t in portofolio]
prices = prices[valid_tickers]

def compute_weights(prices, portofolio, ticker_currency, fx_rates):
    latest_prices = prices.iloc[-1]  # Get last available prices
    
    converted = {}
    for ticker, qty in portofolio.items():
        if ticker not in latest_prices:
            print(f"Warning: {ticker} not found in price data")
            converted[ticker] = 0.0
            continue
            
        # Get the price (ensure it's a scalar value)
        price = float(latest_prices[ticker])
        ccy = ticker_currency.get(ticker, "USD")

        # Convert to USD if needed
        if ccy == "HKD":
            price *= float(fx_rates["HKD"])
        elif ccy == "JPY":
            price *= float(fx_rates["JPY"])

        converted[ticker] = price

    # Calculate position values and weights
    pos_val = {t: qty * converted[t] for t, qty in portofolio.items()}
    total = sum(pos_val.values())
    return {t: float(val / total) for t, val in pos_val.items()}

# Calculate weights and create weight vector
fx_rates = {"HKD": HKD_USD, "JPY": JPY_USD}
weights = compute_weights(prices, portofolio, ticker_currency, fx_rates)

returns = prices.pct_change().dropna()
# Create weight vector (ensure 1D!)
w_vec = np.array([weights.get(ticker, 0.0) for ticker in prices.columns if ticker in weights])

# Debug shapes
print("returns.shape:", returns.shape)
print("w_vec.shape:", w_vec.shape)

# Calculate portfolio returns (now guaranteed 1D)
portfolio_returns = returns.values @ w_vec
returns['portfolio'] = portfolio_returns  # Assign

# ROLLING VAR SERIES (PLAIN HS + FILTERED HS)
lookback = 250       # 1‑year window
alpha    = 0.99
lam      = 0.94      # EWMA lambda for vol filtering

port = returns['portfolio'].values
n = len(port)

# EWMA volatility
sigma = np.zeros_like(port)
sigma[0] = np.std(port[:20])
for t in range(1, n):
    sigma[t] = np.sqrt(lam*sigma[t-1]**2 + (1-lam)*port[t-1]**2)

hs_var = np.full(n, np.nan)
fhs_var = np.full(n, np.nan)

for i in range(lookback, n):
    window = port[i-lookback:i]
    hs_var[i] = -np.quantile(window, 1-alpha)

    z_window = window / sigma[i-lookback:i]
    z_alpha  = -np.quantile(z_window, 1-alpha)
    fhs_var[i] = z_alpha * sigma[i]

returns['hs_var']  = hs_var
returns['fhs_var'] = fhs_var
returns['hs_var_neg']  = -hs_var
returns['fhs_var_neg'] = -fhs_var

# shift VaR forward one day so today's VaR predicts tomorrow's loss
returns['hs_var_pred']  = returns['hs_var'].shift(1)
returns['fhs_var_pred'] = returns['fhs_var'].shift(1)
# Breach count
returns['breach_hs']  = (returns['portfolio'] < (-returns['hs_var'])).astype(int)
returns['breach_fhs'] = (returns['portfolio'] < (-returns['fhs_var'])).astype(int)
# 250-day rolling exception count 
ROLL = 250
returns['n_breach_hs']  = returns['breach_hs'].rolling(ROLL).sum()
returns['n_breach_fhs'] = returns['breach_fhs'].rolling(ROLL).sum()


print("Returns preview:")
print(returns[['portfolio', 'hs_var', 'fhs_var']].tail())
print("\nExceptions preview:")
print(returns[['breach_hs', 'breach_fhs']].tail())
print(f"Total days of data: {len(prices)}")
print(f"Minimum required: {lookback} days")
print("Final weights:")
print({k: f"{v:.4f}" for k, v in weights.items()})


# ===============================================================
# WRITE TO EXCEL  +  EMBED CHARTS  +  BACK-TEST SHEET
out_path = data / "var_dashboard.xlsx"        # <-- keep inside project

with pd.ExcelWriter(out_path,
                    engine="xlsxwriter",
                    datetime_format="yyyy-mm-dd") as writer:

    # ------------- Sheet 1 : VaR & P/L (negative-signed VaR) -----
    sheet_var = returns[['portfolio',
                         'hs_var_neg', 'fhs_var_neg']].dropna()
    sheet_var.to_excel(writer, sheet_name="VaR", index_label="Date")

    workbook  = writer.book
    worksheet = writer.sheets["VaR"]

    max_row = len(sheet_var) + 1            # +1 for header row (Excel rows start at 1)

    chart = workbook.add_chart({'type': 'line'})

    chart.add_series({
        'name':       'Portfolio Return',
        'categories': f"=VaR!$A$2:$A${max_row}",
        'values':     f"=VaR!$B$2:$B${max_row}",
        'line':       {'color': 'blue'},
    })
    chart.add_series({
        'name':   'HS VaR (99%)',
        'values': f"=VaR!$C$2:$C${max_row}",
        'line':   {'color': 'red', 'dash_type': 'dash'},
    })
    chart.add_series({
        'name':   'FHS VaR (99%)',
        'values': f"=VaR!$D$2:$D${max_row}",
        'line':   {'color': 'green', 'dash_type': 'dot'},
    })
    chart.set_title({'name': 'Portfolio P/L vs. 99 % VaR'})
    chart.set_x_axis({'name': 'Date', 'date_axis': True})
    chart.set_y_axis({'name': 'Return / VaR'})
    chart.set_legend({'position': 'top'})
    worksheet.insert_chart('F2', chart, {'x_scale': 2, 'y_scale': 1.3})

    # ------------- Sheet 2 : Exceptions flags only ---------------
    exc_cols  = ['breach_hs', 'breach_fhs']
    exc_df    = returns[exc_cols].dropna()
    exc_df.to_excel(writer, sheet_name="Exceptions", index_label="Date")

    exc_ws = writer.sheets["Exceptions"]
    header_fmt = workbook.add_format({'bold': True,
                                      'border': 1,
                                      'bg_color': '#D7E4BC'})
    for col, name in enumerate(exc_cols, start=1):
        exc_ws.write(0, col, name, header_fmt)

    red_fmt = workbook.add_format({'bg_color': '#FFC7CE'})
    exc_ws.conditional_format(
        f'B2:C{len(exc_df)+1}',
        {'type': 'cell', 'criteria': '==', 'value': 1, 'format': red_fmt}
    )


print("Dashboard saved →", out_path.resolve())
