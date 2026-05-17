import requests
import sys

BASE_URL = "http://localhost:5000"

def test_login(username, password):
    url = f"{BASE_URL}/auth/login"
    print(f"Testing login for {username}...")
    try:
        resp = requests.post(url, json={"username": username, "password": password})
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code == 200:
            print("Login SUCCESS")
        else:
            print("Login FAILED")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login("admin", "admin123")
    test_login("user", "user123")
