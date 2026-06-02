from curl_cffi import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://onehousing.vn/",
    "Origin": "https://onehousing.vn",
}

# Đường dẫn API đang hoạt động
url = "https://api.onehousing.vn/onehousing-channel/v1/inventories"

# Gửi GET request và giả lập Chrome để vượt Cloudflare TLS fingerprinting
response = requests.get(url, headers=headers, impersonate="chrome")

# Kiểm tra xem request có thành công không (mã 200 là thành công)
if response.status_code == 200:
    # Chuyển đổi dữ liệu trả về thành dạng Dictionary/List của Python
    data = response.json()
    
    # In thử dữ liệu ra màn hình
    print("Kết quả cào thành công:")
    print(data)
else:
    print(f"Lỗi: {response.status_code}")
    print("Nội dung lỗi:", response.text)