import requests

def check_user(user_name: str):
    url = "https://portal.lotuselectronics.com/web-api/user/check_user"
    
    headers = {
        "accept": "application/json, text/plain, */*",
        "auth-key": "Web2@!9",
        "auth-token": "",   # put token if required, else leave blank
        "end-client": "Lotus-Web",
        "origin": "https://www.lotuselectronics.com",
        "referer": "https://www.lotuselectronics.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    }

    data = {
        "user_name": user_name,
        "btn": "0"
    }

    # Send as normal form-data, not files
    response = requests.post(url, headers=headers, data=data)
    
    try:
        return response.json()
    except Exception:
        return {"error": "Invalid JSON", "raw": response.text}

# Example usage
if __name__ == "__main__":
    result = check_user("7000118651")
    print(result)
