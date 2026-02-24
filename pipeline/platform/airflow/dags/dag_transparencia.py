"""DAG: Portal da Transparencia (CGU) — daily extraction and processing."""

from airflow import DAG
from airflow.operators.bash import BashOperator

from dag_helpers import DEFAULT_ARGS, extract_cmd, process_cmd

with DAG(
    dag_id="vigiabr_transparencia",
    default_args=DEFAULT_ARGS,
    description="Extract and process Portal da Transparencia (CGU) data",
    schedule="@daily",
    catchup=False,
    tags=["vigiabr", "extraction", "transparencia", "cgu"],
) as dag:
    extract = BashOperator(
        task_id="extract_transparencia",
        bash_command=extract_cmd("transparencia_cgu"),
    )

    process = BashOperator(
        task_id="process_transparencia",
        bash_command=process_cmd("transparencia"),
    )

    extract >> process
