import os
import logging
import requests
import asyncio
import json
from typing import Optional, Tuple
from dotenv import load_dotenv
import io

# Load environment variables
load_dotenv()

# Set up logger
logger = logging.getLogger(__name__)

class VoiceTranscriptionService:
    """Service for transcribing voice messages using Deepgram API"""
    
    def __init__(self):
        """Initialize the voice transcription service"""
        self.api_key = os.environ.get('DEEPGRAM_API_KEY')
        
        if not self.api_key:
            logger.warning("DEEPGRAM_API_KEY not found in environment variables!")
            logger.warning("Voice transcription will not work properly.")
    
    async def download_audio(self, audio_url: str) -> Optional[bytes]:
        """
        Download audio from a URL
        
        Args:
            audio_url (str): The URL of the audio file
            
        Returns:
            bytes or None: The audio data as bytes
        """
        try:
            # Add authorization header for WhatsApp API URLs
            headers = {}
            if 'graph.facebook.com' in audio_url:
                # For WhatsApp Cloud API, we need to add the access token
                access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
                if access_token:
                    headers['Authorization'] = f'Bearer {access_token}'
            
            response = requests.get(audio_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Error downloading audio: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return None

    def _get_mime_type(self, file_path_or_url: str) -> str:
        """
        Get the MIME type of a file based on its extension
        
        Args:
            file_path_or_url (str): File path or URL
            
        Returns:
            str: MIME type
        """
        # Extract extension from file_path_or_url
        if '.' in file_path_or_url:
            ext = file_path_or_url.split('.')[-1].lower()
            if ext == 'mp3':
                return 'audio/mpeg'
            elif ext == 'wav':
                return 'audio/wav'
            elif ext == 'ogg':
                return 'audio/ogg'
            elif ext == 'm4a':
                return 'audio/m4a'
        
        # Default to ogg for WhatsApp audio
        return 'audio/ogg'

    async def transcribe_audio(self, audio_url: str) -> Tuple[bool, Optional[str]]:
        """
        Transcribe audio using Deepgram API directly
        
        Args:
            audio_url (str): The URL of the audio file
            
        Returns:
            tuple: (success, transcription)
        """
        if not self.api_key:
            logger.warning("Deepgram API key not configured")
            return False, None

        try:
            # Download the audio file
            audio_data = await self.download_audio(audio_url)
            if not audio_data:
                return False, None

            # Determine mime type from URL
            mime_type = self._get_mime_type(audio_url)
            logger.info(f"Using mime type: {mime_type} for {audio_url}")
            
            # Prepare the API endpoint
            url = "https://api.deepgram.com/v1/listen"
            
            # Prepare headers
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": mime_type
            }
            
            # Prepare query parameters
            params = {
                "model": "general",
                "language": "en-US",
                "smart_format": "true",
                "punctuate": "true"
            }
            
            # Make the API request
            logger.info("Sending request to Deepgram API...")
            
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
                    logger.info("Transcription successful")
                    return True, transcript
                else:
                    logger.warning("No transcript found in response")
                    logger.debug(f"Response: {json.dumps(result, indent=2)}")
                    return False, None
            else:
                logger.error(f"API request failed with status code {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False, None

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return False, None

    def process_voice_note(self, audio_url: str) -> Optional[str]:
        """
        Process a voice note and return the transcription
        
        Args:
            audio_url (str): The URL of the audio file
            
        Returns:
            str or None: The transcription text
        """
        try:
            # Run the async transcription in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, transcript = loop.run_until_complete(self.transcribe_audio(audio_url))
            loop.close()
            
            return transcript if success else None
            
        except Exception as e:
            logger.error(f"Error processing voice note: {e}")
            return None

# Create singleton instance
_voice_service = None

def get_voice_service():
    """
    Get the voice transcription service instance
    
    Returns:
        VoiceTranscriptionService: The voice service instance
    """
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceTranscriptionService()
    return _voice_service 