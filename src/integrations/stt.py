from dataclasses import dataclass

@dataclass
class STTResult:
    text: str
    confidence: float
    language: str

class STTClient:
    def process_audio(self, audio_data: bytes, mime_type: str) -> STTResult:
        """
        Mock implementation of Speech-to-Text (e.g., Bhashini or Google ASR).
        """
        # Mocking a successful transcription
        # In reality, we'd send audio_data to the STT provider.
        return STTResult(
            text="mock transcribed text about weather",
            confidence=0.85,
            language="en"
        )

stt_client = STTClient()
