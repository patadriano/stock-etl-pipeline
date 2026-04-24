# Stock ETL Pipeline with Airflow

## Overview

This project demonstrates an end-to-end data pipeline that:

- Extracts historical stock price data from Yahoo Finance for popular US stocks  
- Computes technical indicators (MA20, MA50, RSI) and generates buy/sell signals  
- Evaluates strategy performance through simulated trading  
- Computes total profit/loss per strategy  
- Loads the data into PostgreSQL and automates the pipeline using Apache Airflow  

This project showcases data engineering skills: ETL, automation, and workflow management.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python (yfinance, pandas, sqlalchemy, psycopg2-binary) | Data extraction & transformation |
| PostgreSQL | Data storage |
| Apache Airflow | Pipeline orchestration |
| Docker | Containerization |
| Power BI | Data visualization |

---

## Project Workflow

### 1. Extract Data
- Downloaded historical stock data (AAPL, MSFT, GOOGL, NVDA, AMZN) using `yfinance`
- Stored in `stock_price` table

---

### 2. Transform Data
- Computed indicators:
  - MA20
  - MA50
  - RSI

- Generated signals:
  - **MA_CROSS**
  - **RSI**

- Stored in:
  - `indicator`
  - `signal`

---

### 3. Load Data
- Stored simulated trades in `transaction` table  
- Each record includes:
  - strategy
  - stock
  - buy/sell price
  - profit/loss per trade  

---

### 4. Compute Profit/Loss (NEW)
- Aggregated transaction data to compute:
  - Total profit/loss per strategy
  - Total profit/loss per stock
  - Overall strategy performance ranking  

- Stored results in:
  - `strategy_performance` table  

---

### 5. Automation (Airflow DAGs)
DAG 1: Extract
→ Pulls stock data from Yahoo Finance
→ Stores in stock_price table

DAG 2: Transform
→ Reads stock_price
→ Computes MA20, MA50, RSI
→ Stores in indicator table

DAG 3: Load
→ Reads indicator
→ Generates signals & trade logs
→ Stores in transaction table

DAG 4: Performance Aggregation (NEW)
→ Reads transaction table
→ Computes total profit/loss per strategy & stock
→ Stores in strategy_performance table


---

## Analysis & Visualization

- Connected PostgreSQL to Power BI  
- Dashboard includes:
  - Total profit/loss per strategy  
  - Strategy comparison (MA_CROSS vs RSI)  
  - Performance by stock (AAPL, MSFT, etc.)  

---

## Docker Setup

- Used Docker & Docker Compose to run:
  - Apache Airflow
  - PostgreSQL  

---

## Skills Demonstrated

- End-to-end ETL pipeline development  
- Workflow orchestration using Airflow  
- Financial data processing with Pandas  
- Strategy backtesting and evaluation  
- SQL-based aggregation and analytics  
- Data visualization with Power BI  
- Containerization with Docker  

---

## Possible Improvements

- Add more strategies (MACD, Bollinger Bands)  
- Implement real-time streaming (Kafka)  
- Add alerting (email/slack) for pipeline failures  
- Deploy to cloud (AWS / GCP)  
