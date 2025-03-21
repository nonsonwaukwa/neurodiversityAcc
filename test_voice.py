import asyncio
import os
from dotenv import load_dotenv
from app.services.voice import VoiceTranscriptionService

# Load environment variables
load_dotenv()

async def test_voice_transcription():
    """Test the voice transcription service with a sample audio URL."""
    print("Testing Voice Transcription Service")
    
    # Sample audio URL - this should be a valid audio URL for testing
    # In a real environment, you'd use an actual WhatsApp audio URL
    sample_audio_url = input("Enter a sample audio URL to test (or press Enter to skip): ").strip()
    
    if not sample_audio_url:
        print("No audio URL provided, skipping transcription test.")
        return
    
    # Initialize the service
    voice_service = VoiceTranscriptionService()
    
    # Test transcription
    try:
        success, transcription = await voice_service.transcribe_audio(sample_audio_url)
        
        if success:
            print(f"Transcription successful!")
            print(f"Transcribed text: {transcription}")
        else:
            print(f"Transcription failed: {transcription}")
    except Exception as e:
        print(f"Error during transcription: {str(e)}")

if __name__ == "__main__":
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
    asyncio.run(test_voice_transcription()) 