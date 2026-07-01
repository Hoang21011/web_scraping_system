import os
from dotenv import load_dotenv
from pyspark.sql import SparkSession

load_dotenv("/app/.env")

spark = SparkSession.builder \
    .appName("iceberg_maintainance") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.iceberg.type", "jdbc") \
    .config("spark.sql.catalog.iceberg.uri", "jdbc:postgresql://postgres:5432/iceberg_catalog") \
    .config("spark.sql.catalog.iceberg.jdbc.user", os.environ.get("POSTGRES_USER", "iceberg")) \
    .config("spark.sql.catalog.iceberg.jdbc.password", os.environ.get("POSTGRES_PASSWORD", "iceberg_password")) \
    .config("spark.sql.catalog.iceberg.warehouse", "s3a://silver/") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER")) \
    .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD")) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()
# Xoá các dữ liệu sau 1 thángo
spark.sql("CALL iceberg.system.expire_snapshots('silver.properties', TIMESTAMP 'SYSDATE' - INTERVAL 30 DAYS)")
# Xoá các dữ liệu rác
spark.sql("CALL iceberg.system.remove_orphan_files('silver.properties')")
spark.sql("CALL iceberg.system.remove_orphan_files('gold.feature_table')")
