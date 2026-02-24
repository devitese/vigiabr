"""DAG: Querido Diario — daily extraction and processing.

Extracts DOU (Diario Oficial da Uniao) entries via Querido Diario API.
"""

from airflow import DAG
from airflow.operators.bash import BashOperator

from dag_helpers import DEFAULT_ARGS, extract_cmd, process_cmd

with DAG(
    dag_id="vigiabr_querido_diario",
    default_args=DEFAULT_ARGS,
    description="Extract and process Querido Diario (DOU) data",
    schedule="@daily",
    catchup=False,
    tags=["vigiabr", "extraction", "querido_diario", "dou"],
) as dag:
    extract = BashOperator(
        task_id="extract_querido_diario",
        bash_command=extract_cmd("querido_diario"),
    )

    process = BashOperator(
        task_id="process_querido_diario",
        bash_command=process_cmd("querido_diario"),
    )

    extract >> process
