from airflow import DAG
from airflow.operators.python import PythonOperator

import boto3
import tarfile
import os
from datetime import datetime, timedelta

# boto3: Thư viện này cho phép các lập trình viên dễ dàng viết code Python để tạo, 
# quản lý và tương tác trực tiếp với các dịch vụ đám mây của AWS

default_args = {
    'owner': 'Nguyen Hoang Nghia',
    'start_date': datetime(2024, 1, 1)
}

def compact_bronze_files(**kwargs):
    # Dùng boto3 kết nối thẳng vào MiniO
    s3 = boto3.client('s3',
                        endpoint_url='http://minio:9000',
                        aws_access_key_id=os.environ.get("MINIO_ROOT_USER"),
                        aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD"))
    bucket_name='bronze'
    prefix='raw_properties/'

    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    if 'Contents' not in response:
        print("Không có file nào để gom nén!")
        return True
        
    archive_name = f"/tmp/bronze_archive_{datetime.now().strftime('%Y%m%d')}.tar.gz"

    with tarfile.open(archive_name, "w:gz") as tar:
        for obj in response['Contents']:
            
            file_key = obj['Key']
            local_path = f"/tmp/{os.path.basename(file_key)}"
            
            # Tải file về
            s3.download_file(bucket_name, file_key, local_path)
            # Add vào file nén
            tar.add(local_path, arcname=os.path.basename(file_key))
            # Xóa file tạm
            os.remove(local_path)
            
    # Upload file nén lên MinIO
    archive_key = f"archive_properties/{os.path.basename(archive_name)}"
    s3.upload_file(archive_name, bucket_name, archive_key)
    print(f"Đã upload file nén lên: {archive_key}")
    
    # Xóa các file JSON nhỏ gốc trên MinIO (Giải phóng rác)
    for obj in response['Contents']:
        s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
        
    # Xóa file tar.gz ở local
    os.remove(archive_name)

with DAG('monthly_bronze_compaction', default_args=default_args, schedule='0 0 30 * *') as dag:
    compact_task = PythonOperator(
        task_id='compact_files',
        python_callable=compact_bronze_files
    )
