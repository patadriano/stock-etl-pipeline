import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import os

# --- Config ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stocksdb")
DB_USER = os.getenv("DB_USER", "stocksuser")
DB_PASS = os.getenv("DB_PASS", "stockspass")

# Set process date — today by default, or override manually
process_date = datetime.today().strftime("%Y-%m-%d")
# process_date = "2026-02-05"  # ← uncomment to backfill a specific date

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

print("=" * 50)
print(f"Appending indicators up to {process_date}...")
print("=" * 50)

# Load all prices up to process_date (need full history for rolling windows)
prices_df = pd.read_sql(
    f"SELECT * FROM stock_prices WHERE date <= '{process_date}' ORDER BY ticker, date",
    engine
)
print(f"Loaded {len(prices_df)} rows from stock_prices.")

prices_df["date"] = pd.to_datetime(prices_df["date"])
prices_df = prices_df.sort_values(["ticker", "date"]).reset_index(drop=True)

# Moving averages
prices_df["ma_20"] = (
    prices_df.groupby("ticker")["close"]
    .rolling(window=20).mean()
    .reset_index(level=0, drop=True)
)
prices_df["ma_50"] = (
    prices_df.groupby("ticker")["close"]
    .rolling(window=50).mean()
    .reset_index(level=0, drop=True)
)

# RSI 14
price_diff = prices_df.groupby("ticker")["close"].diff()
gain = price_diff.clip(lower=0)
loss = -price_diff.clip(upper=0)

avg_gain = (
    gain.groupby(prices_df["ticker"])
    .rolling(window=14).mean()
    .reset_index(level=0, drop=True)
)
avg_loss = (
    loss.groupby(prices_df["ticker"])
    .rolling(window=14).mean()
    .reset_index(level=0, drop=True)
)
prices_df["rsi_14"] = 100 - (100 / (1 + (avg_gain / avg_loss)))

# Only keep the new process_date rows to append
indicator_df = prices_df[prices_df["date"] == process_date][
    ["date", "ticker", "ma_20", "ma_50", "rsi_14"]
].copy()

if indicator_df.empty:
    print(f"⚠️  No indicator rows for {process_date}. Market may be closed or date not in stock_prices.")
else:
    print(f"\nRows to append:\n{indicator_df.to_string(index=False)}\n")

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_indicators (
                date    DATE,
                ticker  VARCHAR(10),
                ma_20   NUMERIC,
                ma_50   NUMERIC,
                rsi_14  NUMERIC,
                PRIMARY KEY (date, ticker)
            )
        """))

    indicator_df.to_sql(
        "stock_indicators",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500
    )
    print(f"✅ stock_indicators appended for {process_date}.")
