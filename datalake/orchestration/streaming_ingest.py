import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# BÌNH LUẬN SỬA LỖI:
# 1. Khởi tạo SparkSession: appName phải viết hoa chữ N, và phải có .getOrCreate() ở cuối.
# 2. Schema: Thay vì phải định nghĩa StructType khổng lồ cho từng loại dữ liệu (rất dễ mất dữ liệu 
#    nếu API có trường mới), cách Best Practice cho tầng Bronze là lưu nguyên cục RAW JSON string. 
#    Lên tầng Silver, Spark sẽ tự động suy luận Schema (Schema Inference) khi đọc.
# 3. Format ghi: Ta dùng định dạng "json" với 1 cột nguyên bản để ghi nguyên vẹn dữ liệu.
# ==============================================================================

spark = SparkSession.builder \
    .appName("kafka_to_minio_bronze") \
    .master("spark://spark-master:7077") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.apache.hadoop:hadoop-aws:3.3.4") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER")) \
    .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD")) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .getOrCreate()

# Hàm tiện ích để tạo stream cho từng topic
def create_bronze_stream(topic_name, s3_path):
    # 1. Đọc từ Kafka
    df_kafka = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", topic_name) \
        .option("startingOffset", "earliest") \
        .load()
    
    # 2. Chuyển đổi Binary thành String. Ta giữ lại timestamp để biết giờ cào.
    # BÌNH LUẬN SỬA LỖI: selectExpr viết thường chữ s, không có chữ Select bên trong.
    df_raw = df_kafka.selectExpr(
        "CAST(value AS string) as raw_json", 
        "timestamp as kafka_timestamp"
    )
    
    # 3. Ghi ra MinIO dưới dạng JSON (1 cột chứa raw_json)
    query = df_raw.writeStream \
        .format("json") \
        .outputMode("append") \
        .option("path", f"s3a://bronze/{s3_path}") \
        .option("checkpointLocation", f"s3a://bronze/checkpoints/{s3_path}") \
        .start()
        
    return query

# Khởi tạo 4 luồng chạy song song cho 4 Topic
print("Đang khởi động 4 luồng Spark Streaming...")

# option("startingOffset", "earliest"): Xác định vị trí đọc dữ liệu trong trường hợp Spark chưa đọc từ topic này trước đây
query_props = create_bronze_stream("topic_properties", "raw_properties")
query_projects = create_bronze_stream("topic_projects", "raw_projects")
query_subs = create_bronze_stream("topic_subdivisions", "raw_subdivisions")
query_pricing = create_bronze_stream("topic_project_pricing", "raw_pricing")

# BÌNH LUẬN SỬA LỖI: Lệnh chờ là spark.streams.awaitAnyTermination() (có chữ s ở streams)
spark.streams.awaitAnyTermination()
