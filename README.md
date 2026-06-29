# Tổng quan Dự án & Cấu trúc mã nguồn Cào Dữ liệu

Tài liệu này giải thích nhanh về các nhánh hiện tại trên kho lưu trữ GitHub của dự án và mô tả vai trò của các file Python thực hiện nhiệm vụ cào dữ liệu (Crawl/Scrape) trong hệ thống `real_estate_pipeline`.

## 1. Các nhánh trên GitHub

Dự án hiện đang được chia thành các nhánh với các mục đích cụ thể như sau:

- **`databricks_pipeline`**:Đây là nhánh chính. Nhánh chuyên biệt dùng để phát triển, thiết kế và tối ưu hoá hệ thống Data Pipeline ETL từ Bronze -> Silver -> Gold chạy trên nền tảng Databricks. 
- **`data_infrastructure`**: Nhánh dùng để xây dựng và thử nghiệm các cấu trúc hạ tầng dữ liệu khác (như thiết lập CSDL, Iceberg catalog, MinIO, v.v.).
- **`config_dockerfile`**: Nhánh tập trung vào việc cấu hình môi trường Docker và Docker Compose (ví dụ thiết lập Apache Airflow, Spark, PostgreSQL). Nhánh này dùng để test cho nhánh data_infrastructure
- **`method_2_pagination`**: Nhánh thử nghiệm và xây dựng giải pháp cào dữ liệu dựa trên phương pháp lặp phân trang trên giao diện web thay vì chỉ gọi API đơn thuần.
- **`apply_filter_for_all_properties`**: Nhánh thử nghiệm cách dùng Quick Filter API để quét và cào triệt để toàn bộ danh sách căn hộ theo từng bộ lọc nhỏ.

---

## 2. Các file phục vụ việc crawl data (`real_estate_pipeline/src/`)

Trong pipeline tầng **Bronze (Thu thập dữ liệu thô)**, các file Python được phân chia trách nhiệm rất rõ ràng nhằm tối ưu quá trình cào dữ liệu:

- **`main.py`**:
  - Đây là kịch bản chạy chính.
  - Điều phối vòng lặp lật trang để cào liên tục từ trang 1 đến hết. 
  - Gọi các hàm từ file khác và chứa logic dừng sớm (Early Stopping) nếu phát hiện trang web chỉ toàn dữ liệu căn hộ cũ đã từng cào.

- **`html_parser.py`**:
  - Chịu trách nhiệm trực tiếp tải mã nguồn HTML của trang web về bằng `requests`.
  - Dùng `BeautifulSoup` để lấy danh sách các căn hộ (properties) đang mở bán.

- **`api_client.py`**:
  - Chịu trách nhiệm giao tiếp trực tiếp với các API.
  - Lấy các dữ liệu chuyên sâu mà HTML không có sẵn: Thông tin chi tiết các dự án, phân khu, và lịch sử giá / biểu đồ giá.

- **`data_manager.py`**:
  - Phụ trách việc ghi dữ liệu thô lấy được xuống DBFS dưới dạng file `.jsonl`.
  - Đọc các file dữ liệu cũ để ghi nhớ những ID căn hộ nào đã từng được cào, qua đó giúp hệ thống phân biệt dữ liệu mới và dữ liệu cũ, tránh cào đi cào lại.

---

## 3. Các file khác trong pipeline
- **`silver_etl.py`**:
  - Phụ trách việc tiền xử lý dữ liệu và lưu sang layer silver.

- **`feature_engineering.py`**:
  - Mapping các bảng với nhau thành 1 bảng.
  - Chịu trách nhiệm cho việc tạo ra các biến phục vụ cho công việc xây dựng mô hình dự đoán.
  - Lưu feature table vào tầng gold.

- **`logger_config`**:
  - Phát hiện và lưu trữ các lỗi xảy ra khi triển khai pipeline.

- **`gold_aggregation`**:
  - Aggregate các bảng để tạo dashboard trên databricks