import requests
import json
import os
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

def simulate_audio_webhook(audio_url=None):
    """
    Simulate a WhatsApp webhook request with an audio message
    
    Args:
        audio_url (str, optional): URL of an audio file to use in the test
    """
    if not audio_url:
        # If no URL provided, prompt for one
        audio_url = input("Enter a sample audio URL to test (or press Enter to use a placeholder): ").strip()
        if not audio_url:
            print("Using a placeholder URL. This will test the webhook handling but not actual transcription.")
            audio_url = "https://example.com/sample-audio.ogg"
    
    print(f"Testing webhook with audio URL: {audio_url}")
    
    # Create a webhook payload that mimics a WhatsApp audio message
    webhook_data = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "12345",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "16505551111",
                                "phone_number_id": os.environ.get("WHATSAPP_PHONE_NUMBER_ID_1", "12345")
                            },
                            "messages": [
                                {
                                    "from": os.environ.get("TEST_USER_PHONE", "1234567890"),
                                    "id": f"test_audio_{os.urandom(4).hex()}",
                                    "timestamp": "1677856663",
                                    "type": "audio",
                                    "audio": {
                                        "id": "1234567890",
                                        "mime_type": "audio/ogg; codecs=opus",
                                        "url": audio_url
                                    }
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    # Get the app URL from environment or use localhost
    app_url = os.environ.get("APP_URL", "http://localhost:5000")
    webhook_url = f"{app_url}/api/webhook"
    
    print(f"Sending test webhook to: {webhook_url}")
    
    try:
        # Send the webhook request
        response = requests.post(
            webhook_url,
            json=webhook_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook test successful")
        else:
            print("❌ Webhook test failed")
            
    except Exception as e:
        print(f"Error sending webhook request: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test WhatsApp webhook with audio message')
    parser.add_argument('--url', type=str, help='Audio URL to use in the test', default=None)
    args = parser.parse_args()
    
    simulate_audio_webhook(args.url) 