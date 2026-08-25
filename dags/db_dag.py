from airflow.sdk import DAG
import pendulum
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime,timedelta
import extract
import load

default_args={"retries": 3, "retry_delay": timedelta(minutes=1)}

kst_tz = pendulum.timezone("Asia/Seoul")

with DAG(dag_id="Market_ELT", 
         start_date=datetime(2026, 8, 14,tzinfo=kst_tz), 
         schedule="*/1 * * * *",
         catchup=False,
         max_active_runs=1
    ) as dag:

    def push_xcom(ti): #airflow의 구동 메타 데이터
        ti.xcom_push(key = "xcom_key", value = extract.extract())

    def pull_xcom(ti,**context):
        data,utc_collected_at = ti.xcom_pull(key ="xcom_key", task_ids = "extract") #extract의 데이터 받아오기
        utc_slot_at = context["data_interval_start"] #utc datetime slot_at
        iso_slot_at = utc_slot_at.in_timezone(kst_tz) #iso 형태의 kst slot_at
        slot_at = iso_slot_at.replace(tzinfo=None) #kst
        utc_collected_at = pendulum.instance(utc_collected_at, tz="UTC")
        iso_collected_at = utc_collected_at.in_timezone(kst_tz)
        collected_at = iso_collected_at.replace(tzinfo=None)
        load.load(data=data,collected_at=collected_at,slot_at=slot_at)

    extract_task = PythonOperator(task_id="extract", python_callable=push_xcom)

    load_task = PythonOperator(task_id="load", python_callable=pull_xcom)

    extract_task >> load_task