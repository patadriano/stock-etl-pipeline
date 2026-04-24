import pandas as pd
from sqlalchemy import create_engine, text
import os

# --- Config ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stocksdb")
DB_USER = os.getenv("DB_USER", "stocksuser")
DB_PASS = os.getenv("DB_PASS", "stockspass")

tickers = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN"]

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

print("=" * 50)
print("Generating trading signals...")
print("=" * 50)

# ─────────────────────────────────────────────
# Drop and recreate transactions table
# ─────────────────────────────────────────────
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS transactions"))
    conn.execute(text("""
        CREATE TABLE transactions (
            date                DATE,
            ticker              VARCHAR(10),
            value               NUMERIC,
            signal              VARCHAR(10),
            strategy            VARCHAR(20),
            price               NUMERIC,
            transaction_pair_id VARCHAR(50),
            PRIMARY KEY (date, ticker, strategy)
        )
    """))

# ─────────────────────────────────────────────
# Signal generation — price is included per row
# ─────────────────────────────────────────────
def generate_signals(pdf: pd.DataFrame) -> pd.DataFrame:
    pdf = pdf.sort_values("date").reset_index(drop=True)
    out = []

    # ===== RSI Strategy =====
    last_signal = None
    for _, r in pdf.iterrows():
        rsi = r["rsi_14"]
        if pd.isna(rsi):
            continue
        signal = None
        if rsi < 30 and last_signal != "BUY":
            signal = "BUY"
            last_signal = "BUY"
        elif rsi > 70 and last_signal == "BUY":
            signal = "SELL"
            last_signal = "SELL"
        if signal:
            out.append({
                "date":     r["date"],
                "ticker":   r["ticker"],
                "value":    round(float(rsi), 4),
                "signal":   signal,
                "strategy": "RSI",
                "price":    r["price"]   # ✅ taken directly from the row
            })

    # ===== MA Crossover Strategy =====
    last_ma_signal = None
    for _, r in pdf.iterrows():
        ma20 = r["ma_20"]
        ma50 = r["ma_50"]
        if pd.isna(ma20) or pd.isna(ma50):
            continue
        signal = None
        if ma20 > ma50 and last_ma_signal != "BUY":
            signal = "BUY"
            last_ma_signal = "BUY"
        elif ma20 < ma50 and last_ma_signal == "BUY":
            signal = "SELL"
            last_ma_signal = "SELL"
        if signal:
            out.append({
                "date":     r["date"],
                "ticker":   r["ticker"],
                "value":    round(float(ma20), 4),
                "signal":   signal,
                "strategy": "MA_CROSS",
                "price":    r["price"]   # ✅ taken directly from the row
            })

    return pd.DataFrame(out, columns=["date", "ticker", "value", "signal", "strategy", "price"])


# ─────────────────────────────────────────────
# Assign transaction_pair_id to BUY/SELL pairs
# ─────────────────────────────────────────────
def assign_pair_ids(signals_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    signals_df = signals_df.sort_values(["strategy", "date"]).reset_index(drop=True)
    pair_ids = []
    pair_counter = {}

    for _, r in signals_df.iterrows():
        strategy = r["strategy"]
        signal   = r["signal"]
        if strategy not in pair_counter:
            pair_counter[strategy] = {"count": 0, "pending": None}
        if signal == "BUY":
            pair_counter[strategy]["count"] += 1
            pair_id = f"{ticker}_{strategy}_PAIR{pair_counter[strategy]['count']}"
            pair_counter[strategy]["pending"] = pair_id
            pair_ids.append(pair_id)
        elif signal == "SELL":
            pair_ids.append(pair_counter[strategy].get("pending"))
            pair_counter[strategy]["pending"] = None
        else:
            pair_ids.append(None)

    signals_df["transaction_pair_id"] = pair_ids
    return signals_df


# ─────────────────────────────────────────────
# Loop over tickers
# ─────────────────────────────────────────────
total_signals = 0

for ticker in tickers:
    print(f"\nProcessing {ticker}...")

    # JOIN stock_indicators with stock_prices to get price on the same date
    pdf = pd.read_sql(f"""
        SELECT
            i.date,
            i.ticker,
            i.rsi_14,
            i.ma_20,
            i.ma_50,
            p.close AS price
        FROM stock_indicators i
        JOIN stock_prices p
            ON i.date = p.date
            AND i.ticker = p.ticker
        WHERE i.ticker = '{ticker}'
        ORDER BY i.date
    """, engine)

    if pdf.empty:
        print(f"  ⚠️  No data for {ticker}.")
        continue

    signals_df = generate_signals(pdf)

    if signals_df.empty:
        print(f"  No signals generated for {ticker}.")
        continue

    signals_df = assign_pair_ids(signals_df, ticker)

    signals_df.to_sql("transactions", engine, if_exists="append", index=False, method="multi", chunksize=500)

    count = len(signals_df)
    total_signals += count
    print(f"  ✅ {count} signals appended.")
    print(signals_df[["date", "ticker", "value", "signal", "strategy", "price", "transaction_pair_id"]].to_string(index=False))

print(f"\n🎉 Done! Total signals written: {total_signals}")