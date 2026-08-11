from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime
import db

with DAG(dag_id="sample_dag", start_date=datetime(2026, 8, 6), schedule='@daily') as dag:
    python_task = PythonOperator(task_id="print_hello", python_callable=get_connection)