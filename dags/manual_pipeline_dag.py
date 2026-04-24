from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime
import pendulum

local_tz = pendulum.timezone("Asia/Manila")

with DAG(
    dag_id="manual_pipeline",
    description="Manually triggered: load_stocks -> compute_indicators -> generate_signals -> transaction_analysis",
    schedule=None,  # manual trigger only
    start_date=datetime(2026, 1, 1, tzinfo=local_tz),
    catchup=False,
    tags=["stocks", "manual"],
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

    load_stocks = DockerOperator(
        task_id="load_stocks",
        command="python load_stocks.py",
        **_common,
    )

    compute_indicators = DockerOperator(
        task_id="compute_indicators",
        command="python compute_indicators.py",
        **_common,
    )

    generate_signals = DockerOperator(
        task_id="generate_signals",
        command="python generate_signals.py",
        **_common,
    )

    transaction_analysis = DockerOperator(
        task_id="transaction_analysis",
        command="python transaction_analysis.py",
        **_common,
    )

    load_stocks >> compute_indicators >> generate_signals >> transaction_analysis