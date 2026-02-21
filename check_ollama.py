import requests

def check_ollama_connectivity(url="http://127.0.0.1:11434"):
    try:
        response = requests.get(f"{url}/api/tags")
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        print(f"Ollama server is reachable at {url}")
        if data.get("models"):
            print("Available models:")
            for model in data["models"]:
                print(f"- {model["name"]}")
        else:
            print("No models found on Ollama server.")
        return True
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to Ollama server at {url}. Is Ollama running?")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error: An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    check_ollama_connectivity()