from dataclasses import dataclass
import logging
import asyncio
import base64
import httpx
import os
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class STTResult:
    text: str
    confidence: float
    language: str


class BhashiniSTTClient:
    """Bhashini ASR client for Indian languages."""

    BASE_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute"

    # Bhashini language codes
    LANGUAGE_CODES = {
        "hi": "hi",
        "en": "en",
        "mr": "mr",
        "ta": "ta",
        "te": "te",
        "kn": "kn",
        "ml": "ml",
        "gu": "gu",
        "bn": "bn",
        "pa": "pa",
        "or": "or",
        "as": "as",
    }

    def __init__(self, api_key: Optional[str] = None, user_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("BHASHINI_API_KEY")
        self.user_id = user_id or os.getenv("BHASHINI_USER_ID")
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)  # type: ignore
        return self._client  # type: ignore

    async def process_audio(
        self, audio_data: bytes, mime_type: str, language: str = "hi"
    ) -> STTResult:
        """Process audio using Bhashini ASR."""
        if not self.api_key or not self.user_id:
            logger.warning("Bhashini credentials not configured")
            return None  # type: ignore

        try:
            client = await self._get_client()

            # Encode audio to base64
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")

            # Determine language code
            lang_code = self.LANGUAGE_CODES.get(language.lower(), "hi")

            # Bhashini payload structure
            payload = {
                "pipelineTasks": [
                    {
                        "taskType": "asr",
                        "config": {
                            "language": {"sourceLanguage": lang_code},
                            "audioFormat": self._get_audio_format(mime_type),
                            "samplingRate": 16000,
                        },
                    }
                ],
                "inputData": {"audio": [{"audioContent": audio_b64}]},
            }

            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json",
                "userID": self.user_id,
            }

            response = await client.post(self.BASE_URL, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(
                    f"Bhashini ASR error: {response.status_code} - {response.text}"
                )
                return None  # type: ignore

            result = response.json()
            return self._parse_response(result, language)

        except Exception as e:
            logger.error(f"Bhashini ASR error: {e}")
            return None  # type: ignore

    def _get_audio_format(self, mime_type: str) -> str:
        format_map = {
            "audio/ogg": "ogg",
            "audio/wav": "wav",
            "audio/mp3": "mp3",
            "audio/mp4": "mp4",
            "audio/aac": "aac",
            "audio/amr": "amr",
        }
        return format_map.get(mime_type, "ogg")

    def _parse_response(self, data: dict, fallback_lang: str) -> STTResult:
        """Parse Bhashini ASR response."""
        try:
            pipeline_response = data.get("pipelineResponse", [{}])[0]
            audio_response = pipeline_response.get("audio", [{}])[0]
            text = audio_response.get("source", "").strip()
            confidence = audio_response.get("confidence", 0.8)

            if not text:
                return None  # type: ignore

            return STTResult(text=text, confidence=confidence, language=fallback_lang)
        except Exception as e:
            logger.error(f"Failed to parse Bhashini response: {e}")
            return None  # type: ignore

    async def close(self):
        if self._client:
            await self._client.aclose()


class GoogleSTTClient:
    """Google Cloud Speech-to-Text client."""

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import speech

                self._client = speech.SpeechAsyncClient()
            except ImportError:
                logger.warning("google-cloud-speech not installed")
                return None
        return self._client

    async def process_audio(
        self, audio_data: bytes, mime_type: str, language: str = "en"
    ) -> STTResult:
        """Process audio using Google Cloud STT."""
        client = await self._get_client()
        if not client:
            return None  # type: ignore

        try:
            from google.cloud import speech

            # Map mime type to encoding
            encoding_map = {
                "audio/ogg": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                "audio/wav": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                "audio/mp3": speech.RecognitionConfig.AudioEncoding.MP3,
                "audio/mp4": speech.RecognitionConfig.AudioEncoding.MP3,
                "audio/aac": speech.RecognitionConfig.AudioEncoding.MP3,
                "audio/amr": speech.RecognitionConfig.AudioEncoding.AMR,
            }

            encoding = encoding_map.get(
                mime_type, speech.RecognitionConfig.AudioEncoding.OGG_OPUS
            )

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

            config = speech.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=16000,
                language_code=lang_code,
                alternative_language_codes=(
                    ["hi-IN", "en-US"] if lang_code != "hi-IN" else ["en-US", "hi-IN"]
                ),
                enable_automatic_punctuation=True,
            )

            audio = speech.RecognitionAudio(content=audio_data)

            response = await client.recognize(config=config, audio=audio)

            if not response.results:
                return None  # type: ignore

            result = response.results[0]
            alternative = result.alternatives[0]

            return STTResult(
                text=alternative.transcript,
                confidence=alternative.confidence,
                language=language,
            )

        except Exception as e:
            logger.error(f"Google STT error: {e}")
            return None  # type: ignore

    async def close(self):
        if self._client:
            # Speech client doesn't need explicit close
            pass


class MockSTTClient:
    """Mock STT client for development/testing."""

    async def process_audio(
        self, audio_data: bytes, mime_type: str, language: str = "en"
    ) -> STTResult:
        logger.info(f"Mock STT processing: {len(audio_data)} bytes, {mime_type}")
        await asyncio.sleep(0.1)  # Simulate API delay

        # Return different mock results based on language
        mock_texts = {
            "hi": "आज मौसम कैसा है और क्या मुझे सिंचाई करनी चाहिए",
            "mr": "आज हवामान कसे आहे आणि मी शेत सींचावे का",
            "en": "What is the weather today and should I irrigate my crops",
        }

        return STTResult(
            text=mock_texts.get(language, mock_texts["en"]),
            confidence=0.85,
            language=language,
        )

    async def close(self):
        pass


class STTClient:
    """
    Unified STT client with multiple provider support and fallback.
    Priority: Bhashini (for Indian languages) -> Google Cloud -> Mock
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = "auto"):
        self.provider = provider
        self.api_key = api_key

        # Initialize providers
        self.bhashini = BhashiniSTTClient(api_key=api_key)
        self.google = GoogleSTTClient()
        self.mock = MockSTTClient()

        # Track which provider was last used
        self._last_provider = "mock"

    async def process_audio(
        self, audio_data: bytes, mime_type: str, language: str = "en"
    ) -> STTResult:
        """
        Process audio with automatic provider selection and fallback.
        For Indian languages, tries Bhashini first. For English, tries Google first.
        """
        # Determine provider priority based on language
        indian_langs = {
            "hi",
            "mr",
            "ta",
            "te",
            "kn",
            "ml",
            "gu",
            "bn",
            "pa",
            "or",
            "as",
        }
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
                logger.info(f"Trying STT with {provider_name} for language: {language}")
                result = await provider.process_audio(audio_data, mime_type, language)

                if result and result.text:
                    self._last_provider = provider_name
                    logger.info(
                        f"STT successful with {provider_name}: '{result.text[:50]}...' (confidence: {result.confidence})"
                    )
                    return result

            except Exception as e:
                logger.warning(f"STT provider {provider_name} failed: {e}")
                continue

        # All providers failed, return mock as last resort
        logger.warning("All STT providers failed, using mock")
        self._last_provider = "mock"
        return await self.mock.process_audio(audio_data, mime_type, language)

    @property
    def last_provider(self) -> str:
        return self._last_provider

    async def close(self):
        await self.bhashini.close()
        await self.google.close()
        await self.mock.close()


# Global instance
stt_client = STTClient()
