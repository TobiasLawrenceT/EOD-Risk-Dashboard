import sys, numpy as np, pandas as pd, datetime as dt, pathlib

base= pathlib.Path(__file__).resolve().parents[1]
data = base/"data"
sys.path.append(str(base))

# load dictionaries
from setup import portofolio, beta_map      # keeps single source-of-truth

# load price history
px = pd.read_csv(data/"prices.csv",
                 index_col="date", parse_dates=True).sort_index()
rets = px.pct_change().dropna()

# ---- 1. 20-day rolling volatility ---------------
for w in (20, 60, 120):
    vol = rets.rolling(w).std() * np.sqrt(252)
    vol.iloc[-1].to_frame(f"vol{w}").T.to_csv(data/f"vol{w}_snapshot.csv", index_label="date")

#vol_window = 20
#vol20 = rets.rolling(vol_window).std() * np.sqrt(252)
#vol20.iloc[-1].to_frame("vol20").T.to_csv(DATA / "vol_snapshot.csv", index_label="date")

# ---- 2. 60-day rolling beta ---------------------
beta_window = 60
beta = {}
for asset, bench in beta_map.items():
    cov = rets[asset].rolling(beta_window).cov(rets[bench])
    var = rets[bench].rolling(beta_window).var()
    beta[asset] = (cov / var).iloc[-1]
pd.Series(beta, name="beta60").to_csv(data/"beta_snapshot.csv", index_label="ticker")

# ---- 3. cov / corr matrices ---------------------
cov = rets.cov() * 252
cov.to_csv(data/"cov_matrix.csv")
rets.corr().to_csv(data/"corr_matrix.csv")

# ---- 4. portfolio σ & variance–cov VaR ----------
weights = pd.Series(portofolio) * px.iloc[-1]
NAV     = weights.sum()
w       = weights / NAV

sigma_p   = np.sqrt(w.T @ cov @ w)
z_99      = 2.326    # 99% one-sided z-score
var_1d    = z_99 * sigma_p * NAV

(pd.DataFrame({"NAV":[NAV],
               "sigma_p":[sigma_p],
               "VaR_99":[var_1d]})
   .to_csv(data/"var_snapshot.csv", index=False))

print("✓ metrics written to /data")
