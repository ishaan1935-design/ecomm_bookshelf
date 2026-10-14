import requests

# 1. Your Textbee credentials
API_KEY = "txb_V8rfJeg6jXa2lwMicl9FHqrfolVUMIyL" # Replace with your full API key
DEVICE_ID = "6aafa45eded9659b3a8ae036"

# 2. The destination phone number (must use E.164 format with country code)
# Replace with a real phone number you have access to. 
TARGET_PHONE_NUMBER = "+918847066933"

def test_sms():
    url = "https://api.textbee.dev/api/v1/gateway/send-sms"
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "recipients": [TARGET_PHONE_NUMBER],
        "message": "Hello! This is a test message bypassing Django.",
        "deviceId": DEVICE_ID
    }
    
    print(f"Sending test SMS to {TARGET_PHONE_NUMBER}...")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status() # Raises an error for bad status codes (4xx, 5xx)
        
        print("✅ Success! The API accepted the request.")
        print("Check your phone. If you don't receive the SMS within a minute, check the Textbee app on your Motorola to ensure it is awake and has network access.")
        
    except requests.exceptions.RequestException as e:
        print("❌ Failed to send SMS.")
        print(f"Error details: {e}")
        
        # If the server returned an error message, print it out
        if hasattr(e, 'response') and e.response is not None:
            print(f"Server response: {e.response.text}")

if __name__ == "__main__":
    test_sms()