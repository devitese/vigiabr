"""DAG: Receita Federal CNPJ — monthly bulk download and processing.

The CNPJ open data dump (~85GB compressed) is released monthly by Receita Federal.
This DAG downloads the latest dump and loads it into the local SQLite/DuckDB database.
"""

from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

from dag_helpers import DEFAULT_ARGS, bulk_cmd, process_cmd

cnpj_args = {
    **DEFAULT_ARGS,
    "retries": 3,
    "retry_delay": timedelta(minutes=30),
}

with DAG(
    dag_id="vigiabr_cnpj",
    default_args=cnpj_args,
    description="Download and process Receita Federal CNPJ bulk data",
    schedule="0 2 1 * *",  # 1st of each month at 02:00
    catchup=False,
    tags=["vigiabr", "bulk", "cnpj", "receita"],
) as dag:
    download = BashOperator(
        task_id="download_cnpj",
        bash_command=bulk_cmd("cnpj_downloader"),
        execution_timeout=timedelta(hours=12),
    )

    process = BashOperator(
        task_id="process_cnpj",
        bash_command=process_cmd("cnpj"),
        execution_timeout=timedelta(hours=6),
    )

    download >> process
