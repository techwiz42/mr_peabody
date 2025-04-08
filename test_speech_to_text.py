#!/usr/bin/env python3
"""
Simple test script to verify Google API Key works with Speech-to-Text API
"""
import os
import requests
from dotenv import load_dotenv

def test_google_api():
    """Test Google API key with a simple Speech-to-Text API request"""
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env file")
        return False
    
    # Speech-to-Text API endpoint for testing
    url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
    
    # Simple request to test API key (this won't actually transcribe anything)
    payload = {
        "config": {
            "encoding": "LINEAR16",
            "sampleRateHertz": 16000,
            "languageCode": "en-US"
        },
        "audio": {
            "content": "" # Empty content for testing purposes
        }
    }
    
    # Send request
    response = requests.post(url, json=payload)
    
    # Check if API key is valid
    if response.status_code == 400:
        # 400 means the request was malformed (expected with empty audio)
        # but the API key was accepted
        print("API key is valid! The 400 error is expected (empty audio content).")
        print("Response:", response.json())
        return True
    elif response.status_code == 403:
        print("API key is invalid or doesn't have access to Speech-to-Text API")
        print("Response:", response.json())
        return False
    else:
        print(f"Unexpected status code: {response.status_code}")
        print("Response:", response.json())
        return False

if __name__ == "__main__":
    if test_google_api():
        print("\nYour Google API key is working correctly with Speech-to-Text API!")
        print("You can now use the full speech_to_text_test.py script.")
    else:
        print("\nFailed to validate Google API key for Speech-to-Text API.")
        print("Make sure:")
        print("1. Your API key is correctly set in the .env file")
        print("2. The Speech-to-Text API is enabled in your Google Cloud project")
        print("3. Your API key has permission to access the Speech-to-Text API")
