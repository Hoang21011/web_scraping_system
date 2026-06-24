from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime

default_args = {
    'owner': 'Nguyen Hoang Nghia',
    'start_date': datetime(2024, 1, 1) 
}

with DAG('monthly_iceberg_maintenance', default_args=default_args, schedule='@monthly') as dag:
    run_maintenance = SparkSubmitOperator(
        task_id='clean_iceberg_trash',
        conn_id='spark_default',
        application='/Users/nghia/Documents/web_scraping_system/dags/maintenance_script.py',
        packages='org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0'
    ) 
