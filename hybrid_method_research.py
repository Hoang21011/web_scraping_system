from curl_cffi import requests
from bs4 import BeautifulSoup
import json

# Test 1: HTML Pagination
url = "https://onehousing.vn/ban-can-ho?page=1"
res = requests.get(url, impersonate="chrome")
print("HTML Status:", res.status_code)
soup = BeautifulSoup(res.text, "html.parser")
script = soup.find("script", id="__NEXT_DATA__")
if script:
    data = json.loads(script.string)
    # The properties are usually in props.pageProps.initialState...
    # Let's just print keys to navigate
    print("Next Data Keys:", data.keys())
    try:
        # OneHousing typically stores data in props.pageProps
        props = data.get("props", {}).get("pageProps", {})
        print("pageProps keys:", props.keys())
        if "initialState" in props:
            # Maybe Redux state?
            print("Found initialState")
            state = props["initialState"]
            if "search" in state:
                print("Search state keys:", state["search"].keys())
        if "fallback" in props:
             print("Fallback keys:", list(props["fallback"].keys())[:5])
    except Exception as e:
        print(e)
else:
    print("No __NEXT_DATA__ found")

# Test 2: Quick Filter
url_qf = "https://api.onehousing.vn/onehousing-channel/v1/inventories/search/quick-filter?fetch_all=true"
res_qf = requests.post(url_qf, json={}, impersonate="chrome")
print("\nQuick Filter Status:", res_qf.status_code)
qf_data = res_qf.json().get("data", {})
print("Quick filter keys:", qf_data.keys())
if "projects" in qf_data:
    projects = qf_data["projects"]
    print("Total projects in quick filter:", len(projects))
    if projects:
        print("First project:", json.dumps(projects[0], ensure_ascii=False))

