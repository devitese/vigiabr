"""DAG: Camara dos Deputados — daily extraction and processing."""

from airflow import DAG
from airflow.operators.bash import BashOperator

from dag_helpers import DEFAULT_ARGS, extract_cmd, process_cmd

with DAG(
    dag_id="vigiabr_camara",
    default_args=DEFAULT_ARGS,
    description="Extract and process Camara dos Deputados data",
    schedule="@daily",
    catchup=False,
    tags=["vigiabr", "extraction", "camara"],
) as dag:
    extract = BashOperator(
        task_id="extract_camara",
        bash_command=extract_cmd("camara_deputados"),
    )

    process = BashOperator(
        task_id="process_camara",
        bash_command=process_cmd("camara"),
    )

    extract >> process
