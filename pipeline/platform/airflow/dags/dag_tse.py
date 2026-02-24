"""DAG: TSE (Tribunal Superior Eleitoral) — per-election bulk download and processing.

TSE dumps are released per election cycle. Schedule runs monthly to check for new data.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator

from dag_helpers import DEFAULT_ARGS, bulk_cmd, process_cmd

with DAG(
    dag_id="vigiabr_tse",
    default_args=DEFAULT_ARGS,
    description="Download and process TSE election data dumps",
    schedule="@monthly",
    catchup=False,
    tags=["vigiabr", "bulk", "tse"],
) as dag:
    download = BashOperator(
        task_id="download_tse",
        bash_command=bulk_cmd("tse_dump_downloader"),
    )

    process = BashOperator(
        task_id="process_tse",
        bash_command=process_cmd("tse"),
    )

    download >> process
