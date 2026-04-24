import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- Config (matches your other scripts) ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stocksdb")
DB_USER = os.getenv("DB_USER", "stocksuser")
DB_PASS = os.getenv("DB_PASS", "stockspass")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

print("=" * 60)
print("Analyzing transactions (price diff & days held)...")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Load transactions table
# ─────────────────────────────────────────────────────────────
df = pd.read_sql("""
    SELECT
        date,
        ticker,
        signal,
        strategy,
        price,
        transaction_pair_id
    FROM transactions
    WHERE transaction_pair_id IS NOT NULL
    ORDER BY transaction_pair_id, date
""", engine)

if df.empty:
    print("⚠️  No transactions found. Run generate_signals.py first.")
    exit()

print(f"Loaded {len(df)} transaction rows.\n")

# ─────────────────────────────────────────────────────────────
# Pair up BUY and SELL rows using transaction_pair_id
# ─────────────────────────────────────────────────────────────
buy_rows  = df[df["signal"] == "BUY"].set_index("transaction_pair_id")
sell_rows = df[df["signal"] == "SELL"].set_index("transaction_pair_id")

# Inner join on pair id — only completed pairs (BUY + SELL)
pairs = buy_rows.join(sell_rows, lsuffix="_buy", rsuffix="_sell", how="inner")

# ─────────────────────────────────────────────────────────────
# Compute price difference and days held
# ─────────────────────────────────────────────────────────────
pairs["price_diff"]  = pairs["price_sell"] - pairs["price_buy"]
pairs["pct_change"]  = (pairs["price_diff"] / pairs["price_buy"] * 100).round(4)
pairs["days_held"]   = (
    pd.to_datetime(pairs["date_sell"]) - pd.to_datetime(pairs["date_buy"])
).dt.days
pairs["outcome"]     = pairs["price_diff"].apply(
    lambda x: "Profit" if x > 0 else ("Loss" if x < 0 else "Break-even")
)

result = pairs[[
    "ticker_buy", "strategy_buy",
    "date_buy", "price_buy",
    "date_sell", "price_sell",
    "price_diff", "pct_change",
    "days_held", "outcome"
]].rename(columns={
    "ticker_buy":   "ticker",
    "strategy_buy": "strategy",
    "date_buy":     "buy_date",
    "price_buy":    "buy_price",
    "date_sell":    "sell_date",
    "price_sell":   "sell_price",
})

result.index.name = "transaction_pair_id"
result = result.reset_index()

# ─────────────────────────────────────────────────────────────
# Save results to a new table: transaction_results
# ─────────────────────────────────────────────────────────────
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS transaction_results"))
    conn.execute(text("""
        CREATE TABLE transaction_results (
            transaction_pair_id VARCHAR(50) PRIMARY KEY,
            ticker              VARCHAR(10),
            strategy            VARCHAR(20),
            buy_date            DATE,
            buy_price           NUMERIC,
            sell_date           DATE,
            sell_price          NUMERIC,
            price_diff          NUMERIC,
            pct_change          NUMERIC,
            days_held           INTEGER,
            outcome             VARCHAR(15)
        )
    """))

result.to_sql(
    "transaction_results", engine,
    if_exists="append", index=False,
    method="multi", chunksize=500
)

# ─────────────────────────────────────────────────────────────
# Print summary
# ─────────────────────────────────────────────────────────────
print(result[[
    "transaction_pair_id", "ticker", "strategy",
    "buy_date", "buy_price", "sell_date", "sell_price",
    "price_diff", "pct_change", "days_held", "outcome"
]].to_string(index=False))

print(f"\n{'─' * 60}")
print(f"  Total pairs analyzed : {len(result)}")
print(f"  Profitable trades    : {(result['outcome'] == 'Profit').sum()}")
print(f"  Losing trades        : {(result['outcome'] == 'Loss').sum()}")
print(f"  Avg days held        : {result['days_held'].mean():.1f} days")
print(f"  Avg price diff       : ${result['price_diff'].mean():.4f}")
print(f"  Avg % change         : {result['pct_change'].mean():.2f}%")
print(f"{'─' * 60}")
print("✅ Results saved to 'transaction_results' table.")
