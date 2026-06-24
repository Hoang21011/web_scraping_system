import sys
# pyrefly: ignore [missing-import]
import great_expectations as gx
import os
from pyspark.sql import SparkSession

def run_checkpoint():
    context = gx.get_context(mode="file", project_root_dir=os.environ.get("PROJECT_ROOT_DIR"))
    spark = SparkSession.builder \
        .appName("gx_quality_check") \
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.6.0") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.iceberg.type", "jdbc") \
        .config("spark.sql.catalog.iceberg.uri", "jdbc:postgresql://postgres:5432/iceberg_catalog") \
        .config("spark.sql.catalog.iceberg.jdbc.user", "iceberg") \
        .config("spark.sql.catalog.iceberg.jdbc.password", "iceberg") \
        .config("spark.sql.catalog.iceberg.warehouse", "s3a://silver/") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ROOT_USER")) \
        .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_ROOT_PASSWORD")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .getOrCreate()
    
    # Load dataframe từ bảng Silver
    my_df = spark.table("iceberg.silver.properties")
    # Khai báo DataSource cho GX
    data_source = context.data_sources.add_spark("my_spark_source")
    data_asset = data_source.add_dataframe_asset("silver_properties", dataframe=my_df)
    # 3. Tạo Suite (Bộ luật)
    suite = context.suites.add(gx.ExpectationSuite(name="silver_properties_suite"))
    # Thêm các quy tắc vào suite bằng Code Python
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="min_selling_price", min_value=0, max_value=1000000000000
        )
    )
    # 4. Khởi tạo Checkpoint và Chạy
    checkpoint = context.checkpoints.add(
        gx.Checkpoint(
            name="daily_silver_checkpoint",
            validation_definitions=[
                gx.ValidationDefinition(
                    name="silver_validation",
                    data=data_asset,
                    suite=suite
                )
            ]
        )
    )
    result = checkpoint.run()
    # 5. Phản hồi cho Airflow biết
    if not result.success:
        print("Dữ liệu lỗi! Dừng luồng ETL.")
        sys.exit(1) # Báo lỗi cho terminal
    else:
        print("Dữ liệu sạch! Đi tiếp.")
        sys.exit(0) # Báo thành công cho terminal
if __name__ == "__main__":
    run_checkpoint()