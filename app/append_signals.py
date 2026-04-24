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

tickers      = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN"]
process_date = datetime.today().strftime("%Y-%m-%d")
# process_date = "2026-02-05"  # ← uncomment to backfill a specific date

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

print("=" * 50)
print(f"Appending signals for {process_date}...")
print("=" * 50)

# Ensure transactions table exists
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS transactions (
            date        DATE,
            ticker      VARCHAR(10),
            value       NUMERIC,
            signal      VARCHAR(10),
            strategy    VARCHAR(20),
            PRIMARY KEY (date, ticker, strategy)
        )
    """))

# ─────────────────────────────────────────────
# Signal generation — only for process_date
# We still need full history to know last_signal state
# ─────────────────────────────────────────────
def generate_signals_for_date(pdf: pd.DataFrame, target_date: str) -> pd.DataFrame:
    """
    Runs signal logic on full history but only returns
    signals that fall on target_date.
    This ensures last_signal state is correctly carried
    forward from previous days.
    """
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

        if signal and str(r["date"])[:10] == target_date:
            out.append({
                "date":     r["date"],
                "ticker":   r["ticker"],
                "value":    round(float(rsi), 4),
                "signal":   signal,
                "strategy": "RSI"
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

        if signal and str(r["date"])[:10] == target_date:
            out.append({
                "date":     r["date"],
                "ticker":   r["ticker"],
                "value":    round(float(ma20), 4),
                "signal":   signal,
                "strategy": "MA_CROSS"
            })

    return pd.DataFrame(out, columns=["date", "ticker", "value", "signal", "strategy"])


total_signals = 0

for ticker in tickers:
    print(f"\nProcessing {ticker}...")

    # Load full indicator history for correct state tracking
    pdf = pd.read_sql(
        f"SELECT * FROM stock_indicators WHERE ticker = '{ticker}' ORDER BY date",
        engine
    )

    if pdf.empty:
        print(f"  ⚠️  No indicator data for {ticker}. Run append_indicators.py first.")
        continue

    signals_df = generate_signals_for_date(pdf, process_date)

    if signals_df.empty:
        print(f"  No signals on {process_date} for {ticker}.")
        continue

    signals_df.to_sql(
        "transactions",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500
    )

    count = len(signals_df)
    total_signals += count
    print(f"  ✅ {count} signal(s) appended:")
    print(signals_df.to_string(index=False))

print(f"\n🎉 Done! Total new signals appended for {process_date}: {total_signals}")
