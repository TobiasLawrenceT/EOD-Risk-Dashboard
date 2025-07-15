# End-of-Day Risk Dashboard 📊

This project is an automated risk monitoring tool for a cross-country, multi-asset investment portfolio. It calculates key risk metrics and presents them in a front-office-friendly Excel dashboard.

## 🚀 Features
- Pulls daily price data using **Yahoo Finance** via Python
- Calculates risk metrics:  
  - Rolling **Beta**, **Volatility**, **Covariance**, **Correlation**
  - **Value at Risk (VaR)** and **Expected Shortfall (ES)**
  - **Stress Testing** with predefined market shock scenarios
- Outputs metrics to `.csv` files
- **Excel dashboard** powered by Power Query for one-click refresh

## 🧰 Tech Stack
- Python (Pandas, NumPy, yFinance)
- Excel with Power Query
- Git/GitHub for version control

## ✅ How to Use
1. Clone this repo  
2. Activate your virtual environment
3. Install all necessary libraries in python 
4. Run 'extract.py' to fetch prices  
5. Run 'calc_metrics.py', 'calc_var_es.py', and 'calc_stress.py'
6. Check whether csv files have been saved to the "data" folder
7. Open Excel and refresh Power Query links for the dashboard
