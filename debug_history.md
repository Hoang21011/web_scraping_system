# Lịch Sử Debug & Vượt Rào Bảo Mật Cloudflare (OneHousing API)

Tài liệu này tổng hợp tất cả các lỗi đã xảy ra trong quá trình xây dựng hệ thống cào dữ liệu và xử lý ETL.

---

### 1. Lỗi `ModuleNotFoundError: No module named 'requests'`
- **Triệu chứng:** Khi chạy script bằng Python của môi trường ảo `.venv` (`/Users/nghia/Documents/web_scraping_system/.venv/bin/python`), chương trình báo lỗi thiếu thư viện `requests`.
- **Nguyên nhân:** Thư viện `requests` đã được cài đặt ở môi trường Anaconda toàn cục (`/opt/anaconda3`), nhưng môi trường ảo độc lập `.venv` chưa có. Thêm vào đó, Python 3.10 của hệ thống đang gặp lỗi xung đột thư viện động `pyexpat.so`, khiến các lệnh quản lý gói như `pip` bên trong `.venv` bị sập trực tiếp.
- **Giải pháp xử lý:** Thực hiện cài đặt gián tiếp `requests` từ môi trường ngoài vào thư mục `site-packages` của `.venv` bằng cờ `--target`. Hoặc chuyển hướng sang sử dụng **Anaconda Python** (`/opt/anaconda3/bin/python`).

---

### 2. Lỗi `Lỗi: 400 (Bad Request)`
- **Triệu chứng:** Sau khi import thành công thư viện, API trả về mã lỗi HTTP `400`.
- **Nguyên nhân:** Thông báo lỗi nghiệp vụ từ OneHousing cho thấy mã ID bất động sản truyền vào URL API đã bị hết hạn, bị ẩn hoặc đã được bán trên hệ thống, không còn nằm trong danh mục đã được xác thực (verified listings).
- **Giải pháp xử lý:** Thay thế mã bất động sản mới lấy trực tiếp từ trang chủ đang hoạt động.

---

### 3. Lỗi `Lỗi: 404 (Cloudflare Challenge Block)`
- **Triệu chứng:** Khi đổi sang mã mới, Cloudflare lập tức kích hoạt tường lửa chặn request và trả về trang HTML chứa mã kiểm tra thử thách JavaScript.
- **Nguyên nhân:** Cloudflare sử dụng công nghệ **TLS Fingerprinting** (nhận diện vân tay giao thức bảo mật) để phát hiện các truy vấn HTTP tự động từ thư viện `requests` của Python.
- **Giải pháp xử lý:** Cài đặt thư viện nâng cao **`curl_cffi`** để mô phỏng chính xác dấu vân tay TLS và HTTP/2 của trình duyệt thật (Chrome Browser) thông qua tham số `impersonate="chrome"`.

---

### 4. Lỗi `405 (Method Not Allowed)`
- **Triệu chứng:** Khi chạy luồng Crawler Project-Level, các API `price-history` và `price-chart` trả về mã lỗi HTTP 405.
- **Nguyên nhân:** Giao thức mặc định để lấy dữ liệu từ các API này được phía OneHousing cấu hình là `POST` (với body JSON rỗng `{}`), nhưng script sử dụng phương thức `GET`.
- **Giải pháp xử lý:** Thay đổi phương thức gọi API thành `requests.post(url, json={}, impersonate="chrome")` cho các endpoint về giá.

---

### 5. Lỗi `400 (Bad Request) / Thiếu Data ở API Surrounding`
- **Triệu chứng:** API tiện ích xung quanh trả về lỗi 400 hoặc trả về object rỗng `{"data": {}}` nếu gọi bằng `GET`.
- **Nguyên nhân:** API surrounding đòi hỏi các payload phân loại tiện ích cụ thể để trả về đúng dữ liệu, không trả toàn bộ danh sách khi gọi chung chung.
- **Giải pháp xử lý:** Cập nhật logic lọc: Bổ sung điều kiện kiểm tra nếu `data` trả về là rỗng (`{}`) thì sẽ bỏ qua không ghi vào file JSONL để tránh rác dữ liệu.

---

### 6. Lỗi `AttributeError: 'str' object has no attribute 'get'`
- **Triệu chứng:** Hàm parsing `parse_vinhomes_project_ids` bị sập và văng lỗi string không có hàm `.get()`.
- **Nguyên nhân:** Cấu trúc API trả về là `{"data": {"locations": [], "projects": [...]}}`. Logic lặp trực tiếp qua `raw_data['data']` khiến biến vòng lặp trở thành string của key thay vì object.
- **Giải pháp xử lý:** Sửa lại cây trích xuất JSON cho đúng đích: trỏ thẳng vào `raw_data['data']['projects']` rồi mới lặp.

---

### 7. Lỗi `Mất lịch sử Resume của BFS Crawler`
- **Triệu chứng:** Crawler BFS chạy với các hạt giống mới nhưng tạo ra file data mới tinh, bỏ qua hoàn toàn lịch sử đã lưu trước đó.
- **Nguyên nhân:** Đường dẫn file lưu trữ khai báo là đường dẫn tương đối (`"data/properties_data.jsonl"`). Khi script được gọi từ thư mục gốc, OS không tìm thấy file, logic resume không kích hoạt.
- **Giải pháp xử lý:** Sử dụng đường dẫn tuyệt đối bằng `os.path.join(os.path.dirname(__file__), ...)` để script luôn nối đúng file dữ liệu, giúp Resume thành công.

---

### 8. Lỗi `ModuleNotFoundError: No module named 'duckdb'`
- **Triệu chứng:** Khi chạy script `export_to_duckdb.py`, chương trình báo lỗi văng khỏi tiến trình do thiếu module `duckdb`.
- **Nguyên nhân:** Thư viện `duckdb` chưa được cài đặt trong môi trường ảo `.venv` đang sử dụng.
- **Giải pháp xử lý:** Cài đặt thư viện thông qua lệnh `pip install duckdb` và lưu lại thông tin qua `pip freeze > requirements.txt`.

---

### 9. Lỗi `Binder Error: Could not find key "month" in struct`
- **Triệu chứng:** Khi chạy câu truy vấn SQL DuckDB sử dụng hàm `UNNEST(price_chart)` cho bảng `project_prices`, xuất hiện lỗi không tìm thấy trường `month`.
- **Nguyên nhân:** Nhầm lẫn về cấu trúc JSON của API. Dữ liệu lịch sử giá theo tháng (`month`, `price_average`) thực chất nằm trong trường `price_history.value`, còn `price_chart` lại chứa thông tin thống kê giá của các tòa nhà.
- **Giải pháp xử lý:** Đổi câu truy vấn sang `UNNEST(price_history.value)` và ánh xạ lại chính xác các trường dữ liệu cần thiết.

---

### 10. Lỗi `Catalog Error: Aggregate Function with name list_aggr does not exist!`
- **Triệu chứng:** Quá trình biến đổi Silver Layer bằng script `silver_etl.py` bị ngừng lại kèm thông báo lỗi SQL không tìm thấy hàm `list_aggr`.
- **Nguyên nhân:** Hàm `list_aggr` trong DuckDB là một hàm aggregate (hàm gom nhóm dùng với GROUP BY), không thể dùng nó như hàm vô hướng để biến đổi một list có sẵn thành string trên từng dòng dữ liệu.
- **Giải pháp xử lý:** Chuyển sang sử dụng hàm chuỗi `array_to_string(column_name, ', ')` để nối mảng thành chuỗi văn bản.

---

### 11. Lỗi `Hiển thị mã UUID dạng chuỗi Bytes nhị phân trong Pandas`
- **Triệu chứng:** Cột ID trong các file `.parquet` (tầng Silver) khi được đọc bằng Pandas trên Jupyter Notebook hiển thị thành dạng chuỗi bytes mã hóa (`b'\xcf\x91...'`) thay vì chuỗi Text UUID (`cf917354...`).
- **Nguyên nhân:** Hàm tự động đọc JSONL của DuckDB thông minh nhận diện cột ID là kiểu UUID và tối ưu hóa nó thành chuẩn Fixed Length Byte Array (16 bytes) khi ghi ra định dạng Parquet. Thư viện Pandas khi load Parquet đọc dưới dạng bytes thô mặc định.
- **Giải pháp xử lý:** Thêm lệnh ép kiểu `::VARCHAR` (vd: `id::VARCHAR as id`) vào tất cả các cột chứa ID trong truy vấn SQL của script `silver_etl.py` nhằm ép định dạng về chuỗi (Text) trước khi xuất file.
