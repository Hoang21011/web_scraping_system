from airflow import DAG         # Định nghĩa thứ tự thực thi của các tác vụ
# pyrefly: ignore [missing-import]
from airflow.operators.bash import BashOperator     # Công cụ cho phép Airflow chạy câu lệnh trên hệ điều hành

import os
import requests
from datetime import datetime, timedelta

# Hàm gửi thông báo discord khi thất bại
def task_failed_discord_alert(context):
    try:
        from dotenv import load_dotenv
        load_dotenv("/app/.env")
        discord_webhook_token = os.environ.get("DISCORD_WEBHOOK")
        if not discord_webhook_token:
            return

        discord_msg = f"""
        🔴 **Task Failed!**
        *Task*: {context.get('task_instance').task_id}
        *DAG*: {context.get('task_instance').dag_id}
        *Execution Time*: {context.get("execution_date")}
        """
        requests.post(discord_webhook_token, json={"content": discord_msg})
    except Exception as e:
        print(f"Lỗi khi gửi webhook discord: {e}")

default_arg = {
    'owner': 'Nguyen Hoang Nghia',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
    'on_failure_callback': task_failed_discord_alert
}

with DAG("daily_etl_and_quality_check", default_args = default_arg, schedule = '0 0 * * *', catchup = False):
    # schedule sử dụng biểu thức Crone. *: mọi giá trị
    # 0 0 * * *: 0 phút 0 giờ mọi ngày mọi tháng mọi năm
    # catchup = False. Nếu catchup bằng True, khi mà airflow không chạy trong 1 tháng, khi được bật lên airflow sẽ chạy bù 30 lần liên tục

    #1: Crawl Data
    crawl_data = BashOperator(
        task_id='crawl_data',
        bash_command='docker exec web-scraping-system-datalake-1 python /app/datalake/src/main.py'
    )

    bronze_to_silver = BashOperator(
        task_id='bronze_to_silver_etl',
        bash_command='docker exec web-scraping-system-spark-master-1 /opt/spark/bin/spark-submit --conf spark.jars.ivy=/tmp/.ivy2 --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0 /app/datalake/src/silver_etl.py'
    )

    run_gx_validation = BashOperator(
        task_id='run_gx',
        bash_command='docker exec web-scraping-system-spark-master-1 /opt/spark/bin/spark-submit --conf spark.jars.ivy=/tmp/.ivy2 --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0 /app/gx/gx_checkpoint.py'
    )

    silver_to_gold = BashOperator(
        task_id='feature_engineering_gold',
        bash_command='docker exec web-scraping-system-spark-master-1 /opt/spark/bin/spark-submit --conf spark.jars.ivy=/tmp/.ivy2 --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0 /app/datalake/src/feature_engineering.py'
    )

    wait_for_streaming = BashOperator(
        task_id = 'wait_for_streaming',
        bash_command = 'sleep 15'
    )

    crawl_data >> wait_for_streaming >> bronze_to_silver >> run_gx_validation >> silver_to_gold   