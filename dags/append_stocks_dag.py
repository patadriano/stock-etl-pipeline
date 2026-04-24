from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime
import pendulum

local_tz = pendulum.timezone("Asia/Manila")

with DAG(
    dag_id="append_stocks",
    description="Daily append of stock prices at 9:00 PM Philippine time",
    schedule="0 14 * * 2-6",  # 21:00 PHT = 9 PM PH time, weekdays only
    start_date=datetime(2026, 2, 26, 21, 0, tzinfo=local_tz),
    catchup=False,
    tags=["stocks"],
) as dag:

    # Shared env config
    _env = {
        "DB_HOST": "stocks_postgres",
        "DB_PORT": "5432",
        "DB_NAME": "stocksdb",
        "DB_USER": "stocksuser",
        "DB_PASS": "stockspass",
    }
    _common = dict(
        image="newfolder-loader",
        network_mode="newfolder_stocks_net",
        environment=_env,
        auto_remove="success",
        docker_url="unix://var/run/docker.sock",
    )

    append_stocks = DockerOperator(
        task_id="append_stocks",
        command="python append_stocks.py",
        **_common,
    )

    append_indicators = DockerOperator(
        task_id="append_indicators",
        command="python append_indicators.py",
        **_common,
    )

    append_signals = DockerOperator(
        task_id="append_signals",
        command="python append_signals.py",
        **_common,
    )

    append_transaction_analysis = DockerOperator(
        task_id="append_transaction_analysis",
        command="python append_transaction_analysis.py",
        **_common,
    )

    append_stocks >> append_indicators >> append_signals >> append_transaction_analysis