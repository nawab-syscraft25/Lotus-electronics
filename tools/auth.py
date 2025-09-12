import httpx
import logging

AUTH_HEADERS = {
    "auth-key": "Web2@!9",
    "end-client": "Lotus-Web"
}

# Remote API endpoints
CHECK_USER_URL = "https://portal.lotuselectronics.com/web-api/user/check_user"
SEND_OTP_URL = "https://portal.lotuselectronics.com/web-api/user/send_otp"
VERIFY_OTP_URL = "https://portal.lotuselectronics.com/web-api/user/signin"

AUTH_HEADERS_otp = {
    "auth-key": "Web2@!9",
    "end-client": "Lotus-Web",
    "x-chatbot-auth": "3c4f72f2-923e-4efb-a1a2-2c5823d843ba"  # secure token
}

def send_otp(phone: str) -> dict:
    data = {
        "user_name": phone,
        "recaptcha_token": "chatbot-bypass-token"
    }

    try:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
        response = httpx.post(SEND_OTP_URL, data=data, headers=AUTH_HEADERS_otp, timeout=timeout)
        response.raise_for_status()
        return response.json()

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

send_otp_schema = {
    "name": "send_otp",
    "description": "Send an OTP to the user's phone number.",
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {"type": "string"}
        },
        "required": ["phone"]
    }
}

def verify_otp(phone: str, otp: str, session_id: str) -> dict:
    data = {"user_name": phone, "password": otp, "is_otp": "1"}
    response = httpx.post(VERIFY_OTP_URL, data=data, headers=AUTH_HEADERS)
    result = response.json()

    if result.get("error") == "0":
        answer = "OTP verified successfully. You are now logged in."
        status = "success"
        return answer
    return result

verify_otp_schema = {
    "name": "verify_otp",
    "description": "Verify the OTP for the user's phone number and session.",
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {"type": "string"},
            "otp": {"type": "string"},
            "session_id": {"type": "string"}
        },
        "required": ["phone", "otp", "session_id"]
    }
}

AUTH_HEADERS_sign = {
    "auth-key": "Web2@!9",
    "end-client": "Lotus-Web",
    "x-chatbot-auth": "3c4f72f2-923e-4efb-a1a2-2c5823d843ba"  # secure token
}

def sign_in(phone: str, password: str, session_id: str) -> dict:
    data = {
        "user_name": phone,
        "password": password,
        "is_otp": "1",
        "recaptcha_token": "chatbot-bypass-token"
    }

    try:
        # Add timeout to prevent hanging
        response = httpx.post(VERIFY_OTP_URL, data=data, headers=AUTH_HEADERS_sign, timeout=10.0)
        result = response.json()

        if result.get("error") == "0":
            return "success"
        else:
            return "failure"
    except httpx.TimeoutException:
        print("⏰ OTP verification timed out")
        return "timeout"
    except Exception as e:
        print(f"❌ OTP verification error: {e}")
        return "error"

sign_in_schema = {
    "name": "sign_in",
    "description": "Sign in the user with phone and password (not OTP).",
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {"type": "string"},
            "password": {"type": "string"},
            "session_id": {"type": "string"}
        },
        "required": ["phone", "password", "session_id"]
    }
}

tool_registry = {
    "send_otp": (send_otp, send_otp_schema),
    "verify_otp": (verify_otp, verify_otp_schema),
    "sign_in": (sign_in, sign_in_schema),
}

if __name__ == "__main__":
    phone_number = "8962507486"   # <-- replace with your real number
    session_id = "test_session_1"

    # Step 1: Send OTP
    print("=== Sending OTP ===")
    otp_response = send_otp(phone_number)
    print("Response:", otp_response)

    # Step 2: Ask user to enter OTP received on phone
    otp_input = input("Enter the OTP you received: ").strip()

    # Step 3: Verify OTP
    print("=== Verifying OTP ===")
    verify_response = sign_in(phone_number, otp_input, session_id)
    print("Response:", verify_response)

