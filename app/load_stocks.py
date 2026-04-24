import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- Config ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stocksdb")
DB_USER = os.getenv("DB_USER", "stocksuser")
DB_PASS = os.getenv("DB_PASS", "stockspass")

tickers    = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN"]
start_date = "2021-1-1"
end_date   = "2026-4-19"

# 1. Create empty dataframe
all_df = pd.DataFrame()

# 2. Loop through tickers
for ticker in tickers:
    print(f"Downloading {ticker} ...")
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)

    # Fix MultiIndex columns
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

    df["ticker"] = ticker
    df = df[["date", "ticker", "open", "high", "low", "close", "volume"]]

    all_df = pd.concat([all_df, df], ignore_index=True)

print(f"\nTotal rows fetched: {len(all_df)}")
print(all_df.head())

# 3. Write to PostgreSQL
engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS stock_prices (
            date    DATE,
            ticker  VARCHAR(10),
            open    NUMERIC,
            high    NUMERIC,
            low     NUMERIC,
            close   NUMERIC,
            volume  BIGINT,
            PRIMARY KEY (date, ticker)
        )
    """))

# Write rows — skip if already exist (mode='append' + on_conflict via upsert workaround)
all_df.to_sql(
    "stock_prices",
    engine,
    if_exists="append",   # table already created above; append rows
    index=False,
    method="multi",
    chunksize=500
)

print("✅ Data written to PostgreSQL table 'stock_prices'.")
