from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime
from airflow.sdk.execution_time.xcom import XCom
import extract
import load

with DAG(dag_id="Market_ELT", 
         start_date=datetime(2026, 8, 6), 
         schedule='@daily'
    ) as dag:

    def push_xcom(ti): #airflow의 구동 메타 데이터
        ti.xcom_push(key = "xcom_key", value = extract.extract())

    def pull_xcom(ti):
        data = ti.xcom_pull(key ="xcom_key", task_ids = "extract_task")
        load.load(data)

    extract_task = PythonOperator(task_id="extract", python_callable=push_xcom)

    load_task = PythonOperator(task_id="load", python_callable=pull_xcom)

    extract_task >> load_task