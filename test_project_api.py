from curl_cffi import requests
import json
url = "https://api.onehousing.vn/onehousing-channel/v1/insights/projects/16a7f900-56e6-11eb-ae93-0242ac130002"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}
try:
    res = requests.get(url, headers=headers, impersonate="chrome")
    print("Status:", res.status_code)
    data = res.json().get("data", {})
    print("Project keys:", data.keys())
    if "sectors" in data:
        print("Sectors (subdivisions) count:", len(data["sectors"]))
        if len(data["sectors"]) > 0:
            print("First sector keys:", data["sectors"][0].keys())
except Exception as e:
    print("Error:", e)
