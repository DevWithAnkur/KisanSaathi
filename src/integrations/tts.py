from dataclasses import dataclass
import logging
import asyncio
import httpx
import os
import base64
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class TTSResult:
    audio_data: bytes
    mime_type: str
    duration_secs: float


class BhashiniTTSClient:
    """Bhashini TTS client for Indian languages."""
    
    BASE_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute"
    
    # Bhashini language codes and speaker/gender options
    LANGUAGE_CODES = {
        "hi": {"sourceLanguage": "hi", "gender": "female"},
        "en": {"sourceLanguage": "en", "gender": "female"},
        "mr": {"sourceLanguage": "mr", "gender": "female"},
        "ta": {"sourceLanguage": "ta", "gender": "female"},
        "te": {"sourceLanguage": "te", "gender": "female"},
        "kn": {"sourceLanguage": "kn", "gender": "female"},
        "ml": {"sourceLanguage": "ml", "gender": "female"},
        "gu": {"sourceLanguage": "gu", "gender": "female"},
        "bn": {"sourceLanguage": "bn", "gender": "female"},
        "pa": {"sourceLanguage": "pa", "gender": "female"},
        "or": {"sourceLanguage": "or", "gender": "female"},
        "as": {"sourceLanguage": "as", "gender": "female"},
    }
    
    def __init__(self, api_key: str = None, user_id: str = None):
        self.api_key = api_key or os.getenv("BHASHINI_API_KEY")
        self.user_id = user_id or os.getenv("BHASHINI_USER_ID")
        self._client = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def synthesize(self, text: str, language: str = "hi") -> TTSResult:
        """Synthesize speech using Bhashini TTS."""
        if not self.api_key or not self.user_id:
            logger.warning("Bhashini credentials not configured")
            return None
            
        if len(text) > 500:
            logger.warning(f"Text too long for Bhashini TTS ({len(text)} chars), truncating")
            text = text[:500]
            
        try:
            client = await self._get_client()
            
            lang_config = self.LANGUAGE_CODES.get(language.lower(), self.LANGUAGE_CODES["hi"])
            
            payload = {
                "pipelineTasks": [{
                    "taskType": "tts",
                    "config": {
                        "language": {
                            "sourceLanguage": lang_config["sourceLanguage"]
                        },
                        "gender": lang_config["gender"],
                        "audioFormat": "ogg"
                    }
                }],
                "inputData": {
                    "input": [{
                        "source": text
                    }]
                }
            }
            
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json",
                "userID": self.user_id
            }
            
            response = await client.post(self.BASE_URL, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Bhashini TTS error: {response.status_code} - {response.text}")
                return None
                
            result = response.json()
            return self._parse_response(result)
            
        except Exception as e:
            logger.error(f"Bhashini TTS error: {e}")
            return None
    
    def _parse_response(self, data: dict) -> TTSResult:
        """Parse Bhashini TTS response."""
        try:
            pipeline_response = data.get("pipelineResponse", [{}])[0]
            audio_response = pipeline_response.get("audio", [{}])[0]
            audio_b64 = audio_response.get("audioContent", "")
            
            if not audio_b64:
                return None
                
            audio_data = base64.b64decode(audio_b64)
            
            return TTSResult(
                audio_data=audio_data,
                mime_type="audio/ogg",
                duration_secs=len(audio_data) / 8000  # Rough estimate
            )
        except Exception as e:
            logger.error(f"Failed to parse Bhashini TTS response: {e}")
            return None
    
    async def close(self):
        if self._client:
            await self._client.aclose()


class GoogleTTSClient:
    """Google Cloud Text-to-Speech client."""
    
    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self._client = None
        
    async def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import texttospeech
                self._client = texttospeech.TextToSpeechAsyncClient()
            except ImportError:
                logger.warning("google-cloud-texttospeech not installed")
                return None
        return self._client
    
    async def synthesize(self, text: str, language: str = "en") -> TTSResult:
        """Synthesize speech using Google Cloud TTS."""
        client = await self._get_client()
        if not client:
            return None
            
        try:
            from google.cloud import texttospeech
            
            # Language code mapping
            lang_codes = {
                "hi": "hi-IN",
                "en": "en-US",
                "mr": "mr-IN",
                "ta": "ta-IN",
                "te": "te-IN",
                "kn": "kn-IN",
                "ml": "ml-IN",
                "gu": "gu-IN",
                "bn": "bn-IN",
                "pa": "pa-IN",
            }
            
            lang_code = lang_codes.get(language.lower(), "en-US")
            
            # Voice selection
            voice = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.OGG_OPUS,
                speaking_rate=1.0,
                pitch=0.0
            )
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            response = await client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            return TTSResult(
                audio_data=response.audio_content,
                mime_type="audio/ogg",
                duration_secs=len(response.audio_content) / 8000
            )
            
        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            return None
    
    async def close(self):
        pass


class MockTTSClient:
    """Mock TTS client for development/testing."""
    
    async def synthesize(self, text: str, language: str = "en") -> TTSResult:
        logger.info(f"Mock TTS synthesizing: '{text[:50]}...' in {language}")
        await asyncio.sleep(0.1)  # Simulate API delay
        
        # Return mock audio data
        mock_audio = f"MOCK_TTS_AUDIO:{language}:{text}".encode('utf-8')
        
        return TTSResult(
            audio_data=mock_audio,
            mime_type="audio/ogg",
            duration_secs=len(text) * 0.05
        )
    
    async def close(self):
        pass


class TTSClient:
    """
    Unified TTS client with multiple provider support and fallback.
    Priority: Bhashini (for Indian languages) -> Google Cloud -> Mock
    """
    
    def __init__(self, api_key: str = None, provider: str = "auto"):
        self.provider = provider
        self.api_key = api_key
        
        # Initialize providers
        self.bhashini = BhashiniTTSClient(api_key=api_key)
        self.google = GoogleTTSClient()
        self.mock = MockTTSClient()
        
        # Track which provider was last used
        self._last_provider = "mock"
        
    async def synthesize(self, text: str, language: str = "en") -> TTSResult:
        """
        Synthesize speech with automatic provider selection and fallback.
        For Indian languages, tries Bhashini first. For English, tries Google first.
        """
        if not text or not text.strip():
            return TTSResult(audio_data=b"", mime_type="audio/ogg", duration_secs=0)
        
        # Determine provider priority based on language
        indian_langs = {"hi", "mr", "ta", "te", "kn", "ml", "gu", "bn", "pa", "or", "as"}
        is_indian = language.lower() in indian_langs
        
        providers = []
        if is_indian:
            providers = ["bhashini", "google", "mock"]
        else:
            providers = ["google", "bhashini", "mock"]
            
        # Override if specific provider requested
        if self.provider != "auto" and self.provider in ["bhashini", "google", "mock"]:
            providers = [self.provider] + [p for p in providers if p != self.provider]
        
        for provider_name in providers:
            provider = getattr(self, provider_name)
            if provider is None:
                continue
                
            try:
                logger.info(f"Trying TTS with {provider_name} for language: {language}")
                result = await provider.synthesize(text, language)
                
                if result and result.audio_data:
                    self._last_provider = provider_name
                    logger.info(f"TTS successful with {provider_name} ({len(result.audio_data)} bytes)")
                    return result
                    
            except Exception as e:
                logger.warning(f"TTS provider {provider_name} failed: {e}")
                continue
        
        # All providers failed, return mock as last resort
        logger.warning("All TTS providers failed, using mock")
        self._last_provider = "mock"
        return await self.mock.synthesize(text, language)
    
    @property
    def last_provider(self) -> str:
        return self._last_provider
    
    async def close(self):
        await self.bhashini.close()
        await self.google.close()
        await self.mock.close()


# Global instance
tts_client = TTSClient()