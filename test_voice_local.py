import asyncio
import os
from dotenv import load_dotenv
import argparse
import tempfile
import random
import string

# Load environment variables
load_dotenv()

async def test_local_transcription(file_path=None):
    """Test the voice transcription service with a local audio file."""
    # Dynamically import to avoid circular imports
    from app.services.voice import VoiceTranscriptionService
    
    print("Testing Voice Transcription Service with Local File")
    
    if not file_path:
        # If no file provided, prompt for one
        file_path = input("Enter the path to an audio file to test (or press Enter to exit): ").strip()
        if not file_path:
            print("No audio file provided. Exiting.")
            return
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    print(f"Testing transcription with file: {file_path}")
    
    # Initialize the service
    voice_service = VoiceTranscriptionService()
    
    # Test transcription with file data
    try:
        # Read the file content
        with open(file_path, 'rb') as f:
            audio_data = f.read()
        
        # Create a temporary file to simulate a URL
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp:
            temp.write(audio_data)
            temp_path = temp.name
        
        # We'll modify the transcribe_audio method to accept file paths as well
        class MockResponse:
            def __init__(self, content, status_code=200):
                self.content = content
                self.status_code = status_code
                self.text = "OK"
        
        # Override the download_audio method to return our file content
        original_download = voice_service.download_audio
        
        async def mock_download(url):
            print(f"Mock downloading from URL: {url}")
            if url.startswith('file://'):
                file_path = url[7:]  # Remove the file:// prefix
                with open(file_path, 'rb') as f:
                    return f.read()
            return audio_data
        
        # Replace the download method temporarily
        voice_service.download_audio = mock_download
        
        # Call transcribe_audio with a fake URL
        success, transcription = await voice_service.transcribe_audio(f"file://{temp_path}")
        
        # Restore the original download method
        voice_service.download_audio = original_download
        
        # Clean up the temporary file
        try:
            os.unlink(temp_path)
        except:
            pass
        
        if success:
            print(f"✅ Transcription successful!")
            print(f"Transcribed text: {transcription}")
        else:
            print(f"❌ Transcription failed")
            
    except Exception as e:
        print(f"Error during transcription: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test voice transcription with local audio file')
    parser.add_argument('--file', type=str, help='Path to audio file', default=None)
    args = parser.parse_args()
    
    # Check if Deepgram API key is set
    if not os.getenv("DEEPGRAM_API_KEY"):
        print("WARNING: DEEPGRAM_API_KEY environment variable is not set.")
        api_key = input("Enter your Deepgram API key to continue (or press Enter to exit): ").strip()
        if api_key:
            os.environ["DEEPGRAM_API_KEY"] = api_key
        else:
            print("No API key provided. Exiting.")
            exit(1)
    
    # Run the test
    asyncio.run(test_local_transcription(args.file)) 