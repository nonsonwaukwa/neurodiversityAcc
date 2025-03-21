import os
import asyncio
import sys
from dotenv import load_dotenv
import tempfile

# Load environment variables
load_dotenv()

async def main():
    from deepgram import DeepgramClient
    
    # Get API key from environment
    api_key = os.environ.get('DEEPGRAM_API_KEY')
    if not api_key:
        print("DEEPGRAM_API_KEY not found in environment variables")
        sys.exit(1)
    
    # Check if file exists
    file_path = "testrecroding.mp3"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)
    
    print(f"Testing transcription of {file_path}...")
    
    # Create a Deepgram client
    deepgram = DeepgramClient(api_key)
    
    # Set options
    options = {
        "smart_format": True,
        "model": "general"
    }
    
    try:
        print("Sending transcription request...")
        
        # Open the audio file and use the recommended method
        with open(file_path, "rb") as audio:
            # Use the v("1") version syntax with transcribe_file which was suggested
            response = await deepgram.listen.prerecorded.v("1").transcribe_file(audio, options)
        
        # Print the raw response for debugging
        print(f"Response type: {type(response)}")
        
        # Try to extract the transcript
        if hasattr(response, 'results') and hasattr(response.results, 'channels'):
            channels = response.results.channels
            if channels and len(channels) > 0:
                alternatives = channels[0].alternatives
                if alternatives and len(alternatives) > 0:
                    transcript = alternatives[0].transcript
                    if transcript:
                        print("\nTranscript:")
                        print(transcript)
                        return
        
        print("Failed to extract transcript from response structure")
        
    except Exception as e:
        print(f"Error during transcription: {e}")
        import traceback
        traceback.print_exc()
        
        # Try alternate approach with rest instead of prerecorded
        try:
            print("\nTrying alternate approach with deepgram.listen.rest...")
            with open(file_path, "rb") as audio:
                response = await deepgram.listen.rest.v("1").transcribe_file(audio, options)
            
            print(f"Response type: {type(response)}")
            
            # Try to access transcript
            transcript = response.results.channels[0].alternatives[0].transcript
            print("\nTranscript:")
            print(transcript)
        except Exception as e2:
            print(f"Alternative approach also failed: {e2}")

if __name__ == "__main__":
    asyncio.run(main()) 