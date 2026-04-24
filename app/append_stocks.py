import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os

# --- Config ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stocksdb")
DB_USER = os.getenv("DB_USER", "stocksuser")
DB_PASS = os.getenv("DB_PASS", "stockspass")

tickers    = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN"]
start_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
end_date   = datetime.today().strftime("%Y-%m-%d")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

print("=" * 50)
print(f"Appending stock prices for {start_date}...")
print("=" * 50)

all_df = pd.DataFrame()

for ticker in tickers:
    print(f"  Downloading {ticker} ...")
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    df = df.rename(columns={
        "Date":   "date",
        "Open":   "open",
        "High":   "high",
        "Low":    "low",
        "Close":  "close",
        "Volume": "volume"
    })

    # Remove duplicate columns if any
    df = df.loc[:, ~df.columns.duplicated()]

    df["ticker"] = ticker
    df = df[["date", "ticker", "open", "high", "low", "close", "volume"]]

    all_df = pd.concat([all_df, df], ignore_index=True)

if all_df.empty:
    print("⚠️  No new data fetched. Market may be closed today.")
else:
    print(f"\nRows fetched: {len(all_df)}")
    print(all_df.to_string(index=False))

    all_df.to_sql(
        "stock_prices",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500
    )
    print(f"\n✅ stock_prices appended for {start_date}.")
