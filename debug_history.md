# Lịch Sử Debug & Vượt Rào Bảo Mật Cloudflare (OneHousing API)

Tài liệu này ghi nhận quá trình gỡ lỗi (debug) và xây dựng giải pháp vượt tường lửa bảo mật Cloudflare thành công để cào dữ liệu từ API của OneHousing.

---

## 📅 Nhật Ký Debug Chi Tiết

### 1. Lỗi `ModuleNotFoundError: No module named 'requests'`
- **Triệu chứng:** Khi chạy script bằng Python của môi trường ảo `.venv` (`/Users/nghia/Documents/web_scraping_system/.venv/bin/python`), chương trình báo lỗi thiếu thư viện `requests`.
- **Phân tích nguyên nhân:** 
  - Thư viện `requests` đã được cài đặt ở môi trường Anaconda toàn cục (`/opt/anaconda3`), nhưng môi trường ảo độc lập `.venv` chưa có.
  - Thêm vào đó, Python 3.10 của hệ thống (cài qua Homebrew) đang gặp lỗi xung đột thư viện động `pyexpat.so` (`Symbol not found: _XML_SetAllocTrackerActivationThreshold`), khiến các lệnh quản lý gói như `pip` hay `ensurepip` bên trong `.venv` bị sập trực tiếp.
- **Giải pháp xử lý:** 
  - Thực hiện cài đặt gián tiếp `requests` từ môi trường ngoài vào thư mục `site-packages` của `.venv` bằng cờ `--target`.
  - Hoặc chuyển hướng sang sử dụng **Anaconda Python** (`/opt/anaconda3/bin/python`) - một môi trường rất ổn định và đầy đủ thư viện có sẵn trên máy.

---

### 2. Lỗi `Lỗi: 400 (Bad Request)`
- **Triệu chứng:** Sau khi import thành công thư viện, API trả về mã lỗi HTTP `400`.
- **Phân tích nguyên nhân:** 
  - Khi in nội dung chi tiết phản hồi từ máy chủ (`response.text`), nhận được thông báo lỗi nghiệp vụ (business error) từ OneHousing:
    ```json
    {"meta":{"code":"400","message":"Inventory is not in verified listing","internal_message":"Inventory is not in verified listing"}}
    ```
  - Điều này có nghĩa là mã ID bất động sản **`NJL0BN`** truyền vào URL API đã bị hết hạn, bị ẩn hoặc đã được bán trên hệ thống, không còn nằm trong danh mục đã được xác thực (verified listings).
- **Giải pháp xử lý:**
  - Thay thế mã bất động sản mới lấy trực tiếp từ trang chủ đang hoạt động: **`PUMQJ3`**.

---

### 3. Lỗi `Lỗi: 404 (Cloudflare Challenge Block)`
- **Triệu chứng:** Khi đổi sang mã mới, Cloudflare lập tức kích hoạt tường lửa chặn request và trả về trang HTML chứa mã kiểm tra thử thách JavaScript:
  ```html
  <title>HTTP Status 404 – Not Found</title>
  <script>window.__CF$cv$params={...}; .../challenge-platform/scripts/jsd/main.js</script>
  ```
- **Phân tích nguyên nhân:** 
  - Cloudflare sử dụng công nghệ **TLS Fingerprinting** (nhận diện vân tay giao thức bảo mật) để phát hiện các truy vấn HTTP tự động từ thư viện `requests` của Python (vốn có đặc tính TLS rất khác so với trình duyệt thật như Chrome, Firefox).
- **Giải pháp xử lý đột phá:**
  - Cài đặt thư viện nâng cao **`curl_cffi`** - thư viện mô phỏng chính xác dấu vân tay TLS và HTTP/2 của trình duyệt thật.
  - Cập nhật mã nguồn Python sử dụng `curl_cffi.requests` thay thế cho thư viện `requests` mặc định:
    ```python
    from curl_cffi import requests
    # Giả lập dấu vân tay của Chrome Browser
    response = requests.get(url, headers=headers, impersonate="chrome")
    ```

---

### 4. Lỗi `405 (Method Not Allowed)`
- **Triệu chứng:** Khi chạy luồng Crawler Project-Level, các API `price-history` và `price-chart` trả về mã lỗi HTTP 405.
- **Phân tích nguyên nhân:** 
  - Giao thức mặc định để lấy dữ liệu từ các API này được phía OneHousing cấu hình là `POST` (với body JSON rỗng `{}`), nhưng ban đầu script sử dụng phương thức `GET`.
- **Giải pháp xử lý:**
  - Thay đổi phương thức gọi API thành `requests.post(url, json={}, impersonate="chrome")` cho các endpoint về giá.

---

### 5. Lỗi `400 (Bad Request) / Thiếu Data ở API Surrounding`
- **Triệu chứng:** API tiện ích xung quanh (surrounding) trả về lỗi 400 yêu cầu `category_name` nếu gọi bằng `POST`, hoặc trả về object rỗng `{"data": {}}` nếu gọi bằng `GET` với tọa độ. Dẫn tới file `surrounding.jsonl` chỉ có duy nhất trường `project_id`.
- **Phân tích nguyên nhân:** 
  - API surrounding đòi hỏi các payload cụ thể (như phân loại tiện ích: trường học, bệnh viện...) để có thể trả về đúng dữ liệu, chứ không trả toàn bộ danh sách khi gọi chung chung.
- **Giải pháp xử lý:**
  - Cập nhật logic trong `data_processor.py`: Bổ sung điều kiện kiểm tra nếu `data` trả về là rỗng (`{}`) thì sẽ bỏ qua không ghi vào file JSONL để tránh rác dữ liệu.

---

### 6. Lỗi `AttributeError: 'str' object has no attribute 'get'`
- **Triệu chứng:** Hàm parsing `parse_vinhomes_project_ids` bị sập và văng lỗi string không có hàm `.get()`.
- **Phân tích nguyên nhân:** 
  - Cấu trúc API Suggestion trả về `{"data": {"locations": [], "projects": [...]}}`.
  - Logic cũ lặp trực tiếp qua `raw_data['data']`, nghĩa là lặp qua các key `"locations"` và `"projects"`, nên biến vòng lặp trở thành một chuỗi (string). Gọi `.get()` trên chuỗi sẽ gây sập.
- **Giải pháp xử lý:**
  - Sửa lại cây trích xuất JSON cho đúng đích: trỏ thẳng vào `raw_data['data']['projects']` rồi mới thực hiện vòng lặp `for item in items`.

---

### 7. Lỗi `Mất lịch sử Resume của BFS Crawler (chỉ crawl 54 thay vì 105 căn)`
- **Triệu chứng:** Crawler BFS chạy với 3 hạt giống mới nhưng tạo ra file `properties_1780375906.jsonl` mới tinh và kết thúc quá trình ở mức 54 căn, bỏ qua hoàn toàn lịch sử 51 căn đã lưu trước đó.
- **Phân tích nguyên nhân:** 
  - Đường dẫn `RESUME_FILE` khai báo ở `main.py` là đường dẫn tương đối (`"data/properties_data.jsonl"`). Khi script được gọi từ thư mục gốc, hệ điều hành không tìm thấy file, nên logic resume không kích hoạt.
- **Giải pháp xử lý:**
  - Cập nhật khai báo biến môi trường bằng đường dẫn tuyệt đối: `os.path.join(os.path.dirname(__file__), "data", "properties_data.jsonl")` để script luôn nối đúng file, giúp BFS Crawler hợp nhất 3 hạt giống mới với 51 hạt giống cũ, lấy được tổng cộng 105 căn hộ thuộc đa dạng phân khu (The Miami, The Sapphire, Cọ Xanh, Đảo Dừa...).
