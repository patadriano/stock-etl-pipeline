import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- Config ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stocksdb")
DB_USER = os.getenv("DB_USER", "stocksuser")
DB_PASS = os.getenv("DB_PASS", "stockspass")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

print("=" * 50)
print("Computing technical indicators...")
print("=" * 50)

# Load stock_prices from PostgreSQL
df = pd.read_sql("SELECT * FROM stock_prices ORDER BY ticker, date", engine)
print(f"Loaded {len(df)} rows from stock_prices.")

# Moving averages
df["ma_20"] = (
    df.groupby("ticker")["close"]
    .rolling(20).mean()
    .reset_index(level=0, drop=True)
)
df["ma_50"] = (
    df.groupby("ticker")["close"]
    .rolling(50).mean()
    .reset_index(level=0, drop=True)
)

# Price changes
delta = df.groupby("ticker")["close"].diff()

# Gains and losses
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

# Average gain/loss for RSI (14-period)
avg_gain = (
    gain.groupby(df["ticker"])
    .rolling(14).mean()
    .reset_index(level=0, drop=True)
)
avg_loss = (
    loss.groupby(df["ticker"])
    .rolling(14).mean()
    .reset_index(level=0, drop=True)
)

# RSI 14
df["rsi_14"] = 100 - (100 / (1 + avg_gain / avg_loss))

indicator_df = df[["date", "ticker", "ma_20", "ma_50", "rsi_14"]].copy()

print(f"\nSample indicators:\n{indicator_df.dropna().head(5).to_string(index=False)}\n")

# Create table & write
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
print("✅ stock_indicators table loaded.")
