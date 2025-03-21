import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def transcribe_audio(file_path):
    """Transcribe audio using the Deepgram API directly."""
    # Get API key from environment
    api_key = os.environ.get('DEEPGRAM_API_KEY')
    if not api_key:
        print("ERROR: DEEPGRAM_API_KEY not found in environment variables")
        return False, None
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return False, None
    
    print(f"Transcribing file: {file_path}")
    
    # Prepare the API endpoint
    url = "https://api.deepgram.com/v1/listen"
    
    # Prepare headers
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/mpeg"  # Adjust based on file type
    }
    
    # Prepare query parameters
    params = {
        "model": "general",
        "language": "en-US",
        "smart_format": "true",
        "punctuate": "true"
    }
    
    try:
        # Read the file content
        with open(file_path, 'rb') as file:
            audio_data = file.read()
        
        # Make the API request
        print("Sending request to Deepgram API...")
        response = requests.post(
            url, 
            params=params, 
            headers=headers, 
            data=audio_data
        )
        
        # Check response status
        if response.status_code == 200:
            result = response.json()
            # Extract the transcript
            transcript = result.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0].get('transcript')
            
            if transcript:
                print("\nTranscription successful:")
                print(transcript)
                return True, transcript
            else:
                print("No transcript found in response")
                print(f"Response: {json.dumps(result, indent=2)}")
                return False, None
        else:
            print(f"API request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"Error during transcription: {e}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    # Get the file path from command line arguments or use default
    import sys
    file_path = sys.argv[1] if len(sys.argv) > 1 else "testrecroding.mp3"
    
    # Transcribe the audio
    transcribe_audio(file_path) 