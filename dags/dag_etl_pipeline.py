from airflow import DAG         # Định nghĩa thứ tự thực thi của các tác vụ
# pyrefly: ignore [missing-import]
from airflow.operators.bash import BashOperator     # Công cụ cho phép Airflow chạy câu lệnh trên hệ điều hành
# pyrefly: ignore [missing-import]
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator # Công cụ chuyên dụng được dùng để kích hoạt ứng dụng spark. tương đương với spark-submit
# pyrefly: ignore [missing-import]
from airflow.utils.dates import days_ago
import os
import requests
from datetime import timedelta

# Hàm gửi thông báo discord khi thất bại
def task_failed_discord_alert(context):
    discord_webhook_token = os.environ.get("DISCORD_WEB_HOOK")
    discord_msg = f"""
        ! Task Failerd
        *Task*: {context.get('task_instance').task_id}
        *DAG*: {context.get('task_instance').dag_id}
        *Execution Time*: {context.get("execution_date")}
    """
    requests.post(discord_webhook_token, json = {"content": discord_msg})

default_arg = {
    'owner': 'Nguyen Hoang Nghia',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
    'on_failure_callback': task_failed_discord_alert
}

with DAG("daily_etl_and_quality_check", default_args = default_arg, schedule = '0 0 * * *', catchup = False):
    # schedule sử dụng biểu thức Crone. *: mọi giá trị
    # 0 0 * * *: 0 phút 0 giờ mọi ngày mọi tháng mọi năm
    # catchup = False. Nếu catchup bằng True, khi mà airflow không chạy trong 1 tháng, khi được bật lên airflow sẽ chạy bù 30 lần liên tục

    #1: Crawl Data
    crawl_data = SparkSubmitOperator(
        task_id='crawl_data',
        application="/Users/nghia/Documents/web_scraping_system/datalake/src/main.py",
        conn_id='spark_default',
        packages='org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0'
    )

    bronze_to_silver = SparkSubmitOperator(
        task_id='run_silver_pipeline',
        conn_id='spark_default',
        application='/Users/nghia/Documents/web_scraping_system/datalake/src/silver_etl.py',
        packages= 'org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0'
    )

    run_gx_validation = BashOperator(
        task_id = 'run_gx',
        bash_command = 'python /Users/nghia/Documents/web_scraping_system/gx/gx_checkpoint.py'
    )

    silver_to_gold = SparkSubmitOperator(
        task_id='run_gold_pipeline',
        conn_id='spark_default',
        application='/Users/nghia/Documents/web_scraping_system/datalake/src/feature_engineering.py',
        packages='org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0'
    )

    crawl_data >> bronze_to_silver >> run_gx_validation >> silver_to_gold   