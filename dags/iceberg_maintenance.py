from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

default_args = {
    'owner': 'Nguyen Hoang Nghia',
    'start_date': datetime(2024, 1, 1) 
}

with DAG('monthly_iceberg_maintenance', default_args=default_args, schedule='@monthly') as dag:
    run_maintenance = BashOperator(
        task_id='clean_iceberg_trash',
        bash_command='docker exec web-scraping-system-spark-master-1 /opt/spark/bin/spark-submit --conf spark.jars.ivy=/tmp/.ivy2 --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0 /app/dags/maintenance_script.py'
    ) 
