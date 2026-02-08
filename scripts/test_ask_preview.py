import requests
import sys

def test_ask_preview():
    url = "http://localhost:5001/jarvis/ask-preview"
    params = {"query": "test query", "use_genai": "false"}
    
    print(f"Testing {url} with params {params}...")
    try:
        response = requests.get(url, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ask_preview()
