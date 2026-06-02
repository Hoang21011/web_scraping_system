from curl_cffi import requests

urls = [
    "https://api.onehousing.vn/onehousing-channel/v1/inventories",
    "https://api.onehousing.vn/onehousing-channel/v1/properties",
    "https://api.onehousing.vn/onehousing-channel/v1/inventories/properties",
    "https://api.onehousing.vn/onehousing-channel/v1/search",
    "https://api.onehousing.vn/onehousing-channel/v1/properties/search"
]

for url in urls:
    try:
        r = requests.post(url, json={"page":0, "size":20}, impersonate="chrome", timeout=5)
        print("POST", url, r.status_code)
    except: pass
    try:
        r = requests.get(url + "?page=0&size=20", impersonate="chrome", timeout=5)
        print("GET", url, r.status_code)
    except: pass
