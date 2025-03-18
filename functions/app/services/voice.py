import os
import logging
from deepgram import Deepgram
import aiohttp
import asyncio
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class VoiceTranscriptionService:
    def __init__(self):
        self.deepgram = None
        self.api_key = os.getenv('DEEPGRAM_API_KEY')
        if self.api_key:
            self.deepgram = Deepgram(self.api_key)

    async def download_audio(self, url: str) -> Optional[bytes]:
        """Download audio file from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download audio: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return None

    async def transcribe_audio(self, audio_url: str) -> Tuple[bool, Optional[str]]:
        """
        Transcribe audio using Deepgram
        Returns: (success, transcription)
        """
        if not self.deepgram:
            logger.warning("Deepgram API key not configured")
            return False, None

        try:
            # Download the audio file
            audio_data = await self.download_audio(audio_url)
            if not audio_data:
                return False, None

            # Configure Deepgram request
            source = {'buffer': audio_data, 'mimetype': 'audio/ogg'}
            options = {
                'punctuate': True,
                'model': 'general',
                'language': 'en-US'
            }

            # Get response from Deepgram
            response = await self.deepgram.transcription.prerecorded(source, options)
            
            # Extract transcript
            transcript = response['results']['channels'][0]['alternatives'][0]['transcript']
            
            if not transcript:
                return False, None
                
            return True, transcript

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return False, None

    def process_voice_note(self, audio_url: str) -> Optional[str]:
        """
        Process a voice note and return the transcription
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