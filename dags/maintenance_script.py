from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("iceberg_maintainance").getOrCreate()
# Xoá các dữ liệu sau 1 tháng
spark.sql("CALL iceberg.system.expire_snapshots('silver.properties', TIMESTAMP 'SYSDATE' - INTERVAL 30 DAYS)")
# Xoá các dữ liệu rác
spark.sql("CALL iceberg.system.remove_orphan_files('silver.properties')")
spark.sql("CALL iceberg.system.remove_orphan_files('gold.feature_table')")
