import httpx
import logging

AUTH_HEADERS = {
    "auth-key": "Web2@!9",
    "end-client": "Lotus-Web"
}

# Remote API endpoints
CHECK_USER_URL = "https://portal.lotuselectronics.com/web-api/user/check_user"
SEND_OTP_URL = "https://portal.lotuselectronics.com/web-api/user/send_chatbot_otp"
VERIFY_OTP_URL = "https://portal.lotuselectronics.com/web-api/user/verify_chatbot_otp"

AUTH_HEADERS_otp = {
    "auth-key": "Web2@!9",
    "end-client": "Lotus-Web",
    "x-chatbot-auth": "3c4f72f2-923e-4efb-a1a2-2c5823d843ba"  # This matches CHATBOT_SECRET_TOKEN in backend
}

def send_otp(phone: str) -> dict:
    """
    Send OTP to phone number using the chatbot API
    Backend expects:
    - POST method
    - user_name field with phone number (10-15 digits)
    - recaptcha_token field (can be bypass token for chatbot)
    - x-chatbot-auth header to bypass CAPTCHA verification
    """
    print(f"Sending OTP to phone: {phone}")
    
    # Validate phone number format (10-15 digits as per backend)
    if not phone.isdigit() or len(phone) < 10 or len(phone) > 15:
        return {
            "status": "error",
            "data": {
                "answer": "Invalid phone number format. Please provide 10-15 digits."
            }
        }
    
    # Prepare data as expected by backend
    data = {
        "user_name": phone,  # Backend expects 'user_name' field
        "recaptcha_token": "chatbot-bypass-token"  # Backend will bypass CAPTCHA due to x-chatbot-auth header
    }

    try:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
        response = httpx.post(SEND_OTP_URL, data=data, headers=AUTH_HEADERS_otp, timeout=timeout)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        print(response)
        # Backend returns JSON response
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('error') == "0":
                    return {
                        "status": "success",
                        "data": {
                            "answer": result.get('message', 'OTP sent successfully'),
                            "otp_sent": True
                        }
                    }
                else:
                    return {
                        "status": "error", 
                        "data": {
                            "answer": result.get('message', 'Failed to send OTP')
                        }
                    }
            except Exception as json_error:
                logging.error(f"JSON parsing error: {json_error}")
                return {
                    "status": "error",
                    "data": {
                        "answer": "Invalid response from server"
                    }
                }
        else:
            # Handle HTTP errors (400, 401, etc.)
            try:
                error_result = response.json()
                return {
                    "status": "error",
                    "data": {
                        "answer": error_result.get('message', f'HTTP Error {response.status_code}')
                    }
                }
            except:
                return {
                    "status": "error", 
                    "data": {
                        "answer": f"HTTP Error {response.status_code}: {response.text}"
                    }
                }

    except httpx.ReadTimeout:
        logging.error("OTP request timed out for phone: %s", phone)
        return {
            "status": "error",
            "data": {
                "answer": "We're currently unable to reach our OTP service. Please try again in a moment."
            }
        }

    except httpx.HTTPStatusError as exc:
        logging.error("OTP request failed: %s", exc.response.text)
        return {
            "status": "error",
            "data": {
                "answer": f"OTP request failed with status code {exc.response.status_code}."
            }
        }

    except Exception as e:
        logging.exception("Unexpected error during OTP sending")
        return {
            "status": "error",
            "data": {
                "answer": "An unexpected error occurred while sending the OTP."
            }
        }

def verify_otp(phone: str, otp: str, session_id: str = None) -> dict:
    """
    Verify OTP for phone number
    This would use the VERIFY_OTP_URL endpoint
    """
    data = {
        "user_name": phone,
        "otp": otp
    }
    
    if session_id:
        data["session_id"] = session_id
    
    try:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
        response = httpx.post(VERIFY_OTP_URL, data=data, headers=AUTH_HEADERS_otp, timeout=timeout)
        
        print(f"Verify OTP Status Code: {response.status_code}")
        print(f"Verify OTP Response: {response.text}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                return {
                    "status": "success" if result.get('error') == "0" else "error",
                    "data": {
                        "answer": result.get('message', 'OTP verification completed'),
                        "verified": result.get('error') == "0"
                    }
                }
            except Exception as json_error:
                logging.error(f"JSON parsing error: {json_error}")
                return {
                    "status": "error",
                    "data": {
                        "answer": "Invalid response from server"
                    }
                }
        else:
            try:
                error_result = response.json()
                return {
                    "status": "error",
                    "data": {
                        "answer": error_result.get('message', f'HTTP Error {response.status_code}')
                    }
                }
            except:
                return {
                    "status": "error",
                    "data": {
                        "answer": f"HTTP Error {response.status_code}: {response.text}"
                    }
                }
                
    except Exception as e:
        logging.exception("Unexpected error during OTP verification")
        return {
            "status": "error",
            "data": {
                "answer": "An unexpected error occurred while verifying the OTP."
            }
        }

if __name__ == "__main__":
    phone_number = "7000118651"   # <-- replace with your real number
    session_id = "test_session_1"

    # Step 1: Send OTP
    print("=== Sending OTP ===")
    otp_response = send_otp(phone_number)
    print("Response:", otp_response)

    # Step 2: Ask user to enter OTP received on phone
    if otp_response.get("status") == "success":
        otp_input = input("Enter the OTP you received: ").strip()

        # Step 3: Verify OTP
        print("=== Verifying OTP ===")
        verify_response = verify_otp(phone_number, otp_input, session_id)
        print("Response:", verify_response)
    else:
        print("OTP sending failed, cannot proceed with verification")