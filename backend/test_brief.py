
import requests
import json
import sys

def test_brief(doc_id):
    url = f"http://localhost:8011/api/analysis/case-brief/{doc_id}"
    print(f"Testing URL: {url}")
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Response Data (Brief):")
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: {response.status_code}")
            print(f"Detail: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    doc_id = sys.argv[1] if len(sys.argv) > 1 else 379
    test_brief(doc_id)
