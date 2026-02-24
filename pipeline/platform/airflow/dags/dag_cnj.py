"""DAG: CNJ DataJud — daily extraction and processing.

Extracts public lawsuit data from CNJ DataJud API.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator

from dag_helpers import DEFAULT_ARGS, extract_cmd, process_cmd

with DAG(
    dag_id="vigiabr_cnj",
    default_args=DEFAULT_ARGS,
    description="Extract and process CNJ DataJud public lawsuit data",
    schedule="@daily",
    catchup=False,
    tags=["vigiabr", "extraction", "cnj", "datajud"],
) as dag:
    extract = BashOperator(
        task_id="extract_cnj",
        bash_command=extract_cmd("cnj_datajud"),
    )

    process = BashOperator(
        task_id="process_cnj",
        bash_command=process_cmd("cnj"),
    )

    extract >> process
