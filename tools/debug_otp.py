import httpx
import logging

# Enable debug logging for httpx
logging.basicConfig(level=logging.DEBUG)

AUTH_HEADERS_otp = {
    "auth-key": "Web2@!9",
    "end-client": "Lotus-Web", 
    "x-chatbot-auth": "3c4f72f2-923e-4efb-a1a2-2c5823d843ba"
}

SEND_OTP_URL = "https://portal.lotuselectronics.com/web-api/user/send_chatbot_otp"

def detailed_test():
    phone = "8962507486"
    
    print("=== Detailed API Test ===")
    print(f"URL: {SEND_OTP_URL}")
    print(f"Headers: {AUTH_HEADERS_otp}")
    
    data = {
        "user_name": phone,
        "recaptcha_token": "chatbot-bypass-token"
    }
    print(f"Data: {data}")
    
    try:
        # Create a client with detailed logging
        with httpx.Client(timeout=30.0) as client:
            print("\n--- Making POST request ---")
            response = client.post(
                SEND_OTP_URL,
                data=data,
                headers=AUTH_HEADERS_otp
            )
            
            print(f"\n--- Response Details ---")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            
            print(f"\nRaw Response Text: '{response.text}'")
            print(f"Response Length: {len(response.text)}")
            print(f"Response Bytes: {response.content}")
            
            # Check if it's actually a successful empty response
            if response.status_code == 200 and not response.text.strip():
                print("\n--- Analysis ---")
                print("Got HTTP 200 with empty body.")
                print("This might indicate:")
                print("1. The backend processed successfully but returns empty response")
                print("2. There's an issue with the backend logic before json_output")
                print("3. The backend auth check might be failing silently")
                
            elif response.text.strip():
                print(f"\n--- Attempting JSON Parse ---")
                try:
                    json_data = response.json()
                    print(f"JSON Response: {json_data}")
                except Exception as e:
                    print(f"JSON Parse Error: {e}")
                    print("Response is not valid JSON")
            
            return response
            
    except Exception as e:
        print(f"Request failed: {e}")
        return None

if __name__ == "__main__":
    detailed_test()