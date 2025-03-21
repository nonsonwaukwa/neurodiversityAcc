import asyncio
import os
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

async def test_transcription(file_path):
    """Test transcription with Deepgram directly."""
    try:
        # Import Deepgram directly
        from deepgram import DeepgramClient
        
        # Initialize client
        api_key = os.environ.get('DEEPGRAM_API_KEY')
        if not api_key:
            print("ERROR: DEEPGRAM_API_KEY not found in environment variables")
            return
            
        # Initialize client
        deepgram = DeepgramClient(api_key)
        
        # Open the file
        print(f"Opening file: {file_path}")
        
        # Determine mimetype based on file extension
        mime_type = "audio/mpeg"  # Default for MP3
        if file_path.endswith(".wav"):
            mime_type = "audio/wav"
        elif file_path.endswith(".ogg"):
            mime_type = "audio/ogg"
        
        print(f"Using mime type: {mime_type}")
        
        # Read the audio file
        with open(file_path, 'rb') as audio:
            print("Sending transcription request...")
            
            # Use the current API structure
            payload = {
                "model": "general",
                "language": "en-US",
                "smart_format": True,
                "punctuate": True
            }
            
            try:
                # Try using listen.prerecorded.v1.transcribe
                response = await deepgram.listen.prerecorded.v1.transcribe(audio, payload)
                print("Used prerecorded v1 transcribe")
            except Exception as e1:
                print(f"First attempt failed: {e1}")
                try:
                    # Fall back to listen.rest.v1.transcribe
                    audio.seek(0)  # Reset file position
                    response = await deepgram.listen.rest.v1.transcribe(audio, payload)
                    print("Used rest v1 transcribe")
                except Exception as e2:
                    print(f"Second attempt failed: {e2}")
                    # Final fallback - try the v("1") pattern
                    audio.seek(0)  # Reset file position
                    response = await deepgram.listen.prerecorded.v("1").transcribe(audio, payload)
                    print("Used prerecorded v(\"1\") transcribe")
        
        print("Processing response...")
        
        # Print the raw response for debugging
        print(f"Response type: {type(response)}")
        print(f"Response dir: {dir(response)}")
        
        # Try to extract the transcript using different approaches
        transcript = None
        
        # Approach 1: Using response.results.channels
        try:
            transcript = response.results.channels[0].alternatives[0].transcript
        except (AttributeError, IndexError, TypeError) as e:
            print(f"Approach 1 failed: {e}")
            
            # Approach 2: Using response["results"]
            try:
                transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
            except (KeyError, IndexError, TypeError) as e:
                print(f"Approach 2 failed: {e}")
            
                # Approach 3: Using response.to_dict()
                try:
                    resp_dict = response.to_dict()
                    transcript = resp_dict["results"]["channels"][0]["alternatives"][0]["transcript"]
                except (AttributeError, KeyError, IndexError, TypeError) as e:
                    print(f"Approach 3 failed: {e}")
        
        if transcript:
            print("✅ Transcription successful:")
            print(transcript)
        else:
            print("❌ No transcript found in the response")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test Deepgram transcription directly')
    parser.add_argument('--file', type=str, help='Path to audio file', required=True)
    args = parser.parse_args()
    
    # Run the test
    asyncio.run(test_transcription(args.file)) 