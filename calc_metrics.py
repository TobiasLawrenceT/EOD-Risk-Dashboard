import numpy as np
import pandas as pd
from pathlib import Path
from setup import portofolio, beta_map  # user‑maintained dicts

# ── parameters you might tweak ──────────────────────────────────────────
DATA_DIR   = Path(__file__).resolve().parents[0] / "data"
OUT_XLSX   = DATA_DIR / "metrics_dashboard.xlsx"
VOL_WINS   = (20, 60, 120)        # trading‑day windows
BETA_WIN   = 60                   # for rolling β
COV_SCALE  = 252                  # daily → annual
CONF       = 0.99                 # VaR / ES level (z≈2.326)
STRESS_SCN = {"^GSPC": -0.05,     # toy 1‑factor scenario
              "TLT":   -0.08}

DATA_DIR.mkdir(exist_ok=True)

# ── 1. load prices & returns ───────────────────────────────────────────
prices = (
    pd.read_csv(DATA_DIR / "prices.csv",
                index_col="date", parse_dates=True)
      .sort_index()
)
returns = prices.pct_change().dropna()

# ── 2. rolling vols (latest point only) ─────────────────────────
vol_tabs = {}
for w in VOL_WINS:
    vol_ann = returns.rolling(w).std().iloc[-1] * np.sqrt(COV_SCALE)
    vol_tabs[f"vol{w}"] = vol_ann.to_frame(name="vol_ann")   # 1-col DF

# ── 2a. stack to long: (asset , window , vol_ann) ──────────────
vol_long = (
    pd.concat(vol_tabs, names=["window"])   # outer key becomes 'window'
      .reset_index()                        # window, asset, vol_ann
)

# turn 'vol20' → 20, etc.
vol_long["window"] = (
    vol_long["window"].str.extract(r"(\d+)", expand=False).astype(int)
)

vol_long.to_csv(DATA_DIR / "vol_long.csv", index=False)
vol_long.to_csv(DATA_DIR / "vol_long.csv", index=False)

breach_long = (
    returns[["breach_hs", "breach_fhs"]]
        .stack()                     # turns 2 columns → 1
        .reset_index()
        .rename(columns={"level_1": "metric", 0: "flag"})
)
breach_long.to_csv(DATA_DIR / "breach_long.csv", index=False)


# ── 3. rolling β against chosen benchmarks ─────────────────────────────

def last_beta(asset: str, bench: str, win: int = BETA_WIN) -> float:
    cov = returns[asset].rolling(win).cov(returns[bench])
    var = returns[bench].rolling(win).var()
    return (cov / var).iloc[-1]

beta_tab = pd.Series(
    {a: last_beta(a, b) for a, b in beta_map.items()},
    name=f"beta{BETA_WIN}"
).to_frame()

beta_long = beta_tab.reset_index().rename(columns={"index": "asset"})
beta_long.to_csv(DATA_DIR / "beta_long.csv", index=False)

# ── 4. covariance & correlation (annualised) ───────────────────────────
cov_252  = returns.cov() * COV_SCALE
corr_mat = returns.corr()

cov_long = (
    cov_252.stack()
           .reset_index()
           .rename(columns={"level_0": "asset_i", "level_1": "asset_j", 0: "cov_ann"})
)
cov_long.to_csv(DATA_DIR / "cov_long.csv", index=False)

corr_long = (
    corr_mat.stack()
             .reset_index()
             .rename(columns={"level_0": "asset_i", "level_1": "asset_j", 0: "corr"})
)
corr_long.to_csv(DATA_DIR / "corr_long.csv", index=False)

# ── 5. portfolio weights, exposures & Delta‑normal VaR ─────────────────
px_today   = prices.iloc[-1]
pos_value  = pd.Series(portofolio) * px_today  # align by index
nav        = pos_value.sum()
weights    = pos_value / nav

exposure_long = (
    pd.DataFrame({
        "asset": pos_value.index,
        "position_value": pos_value.values,
        "weight": weights.values,
    })
)
exposure_long.to_csv(DATA_DIR / "exposure.csv", index=False)

sigma_p_a  = np.sqrt(weights.T @ cov_252 @ weights)
z          = 2.326  # hard‑code for 99 %
var_99     = -z * sigma_p_a * nav        # negative loss number
var_tab    = pd.DataFrame({
    "NAV": [nav],
    "ann_sigma": [sigma_p_a],
    "VaR_99": [var_99],
})

# ── 6. Excel workbook (snapshot grids) ─────────────────────────────────
with pd.ExcelWriter(OUT_XLSX, engine="xlsxwriter",
                    datetime_format="yyyy-mm-dd") as xw:

    for name, df in vol_tabs.items():
        df.to_excel(xw, sheet_name=name)

    beta_tab .to_excel(xw, sheet_name="beta")
    cov_252  .to_excel(xw, sheet_name="cov_252")
    corr_mat .to_excel(xw, sheet_name="corr")
    var_tab  .to_excel(xw, sheet_name="VaR")
    exposure_long.to_excel(xw, sheet_name="exposure", index=False)

print("✓  metrics_dashboard.xlsx + long CSVs written to", DATA_DIR)
