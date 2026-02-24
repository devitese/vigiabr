"""DAG: Senado Federal — daily extraction and processing."""

from airflow import DAG
from airflow.operators.bash import BashOperator

from dag_helpers import DEFAULT_ARGS, extract_cmd, process_cmd

with DAG(
    dag_id="vigiabr_senado",
    default_args=DEFAULT_ARGS,
    description="Extract and process Senado Federal data",
    schedule="@daily",
    catchup=False,
    tags=["vigiabr", "extraction", "senado"],
) as dag:
    extract = BashOperator(
        task_id="extract_senado",
        bash_command=extract_cmd("senado_federal"),
    )

    process = BashOperator(
        task_id="process_senado",
        bash_command=process_cmd("senado"),
    )

    extract >> process
