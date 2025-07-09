import numpy as np, pandas as pd, datetime as dt
from pathlib import Path
from setup import portofolio, beta_map          # <- your dicts

# ---------- paths -------------------------------------------------
base  = Path(__file__).resolve().parents[1]
data  = base / "data"
px    = pd.read_csv(data / "prices.csv",
                    index_col="date", parse_dates=True).sort_index()
rets  = px.pct_change().dropna()

# ---------- 1. Rolling vols (20/60/120) ---------------------------
vol_sheets = {}
for w in (20, 60, 120):
    vol = rets.rolling(w).std().iloc[-1] * np.sqrt(252)
    vol_sheets[f"vol{w}"] = vol.to_frame(f"vol{w}")

# ---------- 2. Rolling beta (60 d) --------------------------------
beta = {}
for asset, bench in beta_map.items():
    cov = rets[asset].rolling(60).cov(rets[bench])
    var = rets[bench].rolling(60).var()
    beta[asset] = (cov / var).iloc[-1]
beta_sheet = pd.Series(beta, name="beta60").to_frame()

# ---------- 3. Cov / Corr ----------------------------------------
cov_252  = rets.cov() * 252
corr_mat = rets.corr()

# ---------- 4. Variance–cov VaR ----------------------------------
prices_today = px.iloc[-1]
pos_values   = pd.Series(portofolio) * prices_today
NAV          = pos_values.sum()
w_vec        = pos_values / NAV

sigma_p  = np.sqrt(w_vec.T @ cov_252 @ w_vec)
z_99     = 2.326
var_99   = z_99 * sigma_p * NAV
var_df   = pd.DataFrame({"NAV":[NAV],
                         "sigma_p":[sigma_p],
                         "VaR_99":[var_99]})

# ---------- 5. 99 % Expected Shortfall (Historical) --------------
tail = rets.dot(w_vec).dropna().sort_values().iloc[:int(0.01*len(rets))]
es_99 = -tail.mean() * NAV
es_df = pd.DataFrame({"ES_99":[es_99]})

# ---------- 6. (optional) 1-factor stress: -5 % equity, +100 bp rates
stress_move = {"^GSPC": -0.05, "TLT": -0.08}    # toy scenario
stress_pl   = (pd.Series(stress_move) * pos_values.reindex(stress_move)).sum()
stress_df   = pd.DataFrame({"Eqt-5%/Rates+100bp":[stress_pl]}, index=[0])

# ---------- WRITE EVERYTHING IN ONE WORKBOOK ---------------------
out = data / "risk_dashboard.xlsx"
with pd.ExcelWriter(out, engine="xlsxwriter",
                    datetime_format="yyyy-mm-dd") as writer:
    # each .to_excel creates a tab
    for name, df in vol_sheets.items():
        df.to_excel(writer, sheet_name=name)
    beta_sheet.to_excel(writer,     sheet_name="beta60")
    cov_252.to_excel(writer,        sheet_name="cov_252")
    corr_mat.to_excel(writer,       sheet_name="corr")
    var_df.to_excel(writer,         sheet_name="VaR")
    es_df.to_excel(writer,          sheet_name="ES")
    stress_df.to_excel(writer,      sheet_name="stress_1f")

print("✓ risk_dashboard.xlsx written →", out.resolve())
