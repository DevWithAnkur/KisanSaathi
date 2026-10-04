import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import S3 client, but make it optional
try:
    from .s3 import get_s3_client

    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    get_s3_client = None  # type: ignore


class WhatsAppClient:
    def __init__(self, token: str, phone_number_id: str):
        self.token = token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def validate_voice_note(
        self, mime_type: str, file_size: int, duration_secs: int
    ) -> bool:
        """
        Validates voice note metadata before downloading.
        """
        allowed_mimes = [
            "audio/ogg",
            "audio/aac",
            "audio/mp4",
            "audio/amr",
            "audio/opus",
        ]

        if mime_type not in allowed_mimes:
            logger.warning(f"Unsupported MIME type: {mime_type}")
            return False

        if file_size > 5 * 1024 * 1024:  # 5 MB limit
            logger.warning(f"File size too large: {file_size}")
            return False

        if duration_secs > 60:  # 60 seconds limit
            logger.warning(f"Duration too long: {duration_secs}")
            return False

        return True

    async def download_media(
        self, media_id: str, farmer_id: Optional[str] = None
    ) -> tuple[bytes, str]:
        """
        Download media from WhatsApp Business API.
        Returns (audio_data, mime_type)
        Also uploads to S3 for lifecycle management if S3 is available.
        """
        logger.info(f"Downloading media {media_id}")

        # In production, this would:
        # 1. GET /{media_id} to get media URL
        # 2. Download the media from that URL
        # For mock, return dummy data

        async with httpx.AsyncClient() as client:
            # Step 1: Get media URL
            media_url = f"{self.base_url}/{media_id}"
            response = await client.get(media_url, headers=self.headers)
            if response.status_code != 200:
                logger.error(
                    f"Failed to get media URL: {response.status_code} {response.text}"
                )
                return b"", ""

            media_info = response.json()
            download_url = media_info.get("url")
            mime_type = media_info.get("mime_type", "audio/ogg")

            if not download_url:
                logger.error("No download URL in media response")
                return b"", ""

            # Step 2: Download the actual media
            # Note: Media download uses a different auth method (no Bearer token)
            media_response = await client.get(download_url)
            if media_response.status_code != 200:
                logger.error(f"Failed to download media: {media_response.status_code}")
                return b"", ""

            audio_data = media_response.content

            # Step 3: Upload to S3 for lifecycle management (if available)
            if S3_AVAILABLE and farmer_id:
                try:
                    s3 = get_s3_client()
                    # Ensure bucket exists with lifecycle policy
                    s3.ensure_bucket_exists()
                    # Upload as pending (will be moved to processed/failed after transcription)
                    s3_key = s3.upload_voice_note(
                        farmer_id, audio_data, mime_type, status="pending"
                    )
                    if s3_key:
                        logger.info(f"Voice note uploaded to S3: {s3_key}")
                        # Store S3 key in media_info for later reference
                        media_info["s3_key"] = s3_key
                except Exception as e:
                    logger.warning(f"S3 upload failed (non-blocking): {e}")

            return audio_data, mime_type

    async def mark_voice_processed(self, farmer_id: str, s3_key: str) -> bool:
        """Mark voice note as processed (moves to processed prefix for auto-deletion)."""
        if not S3_AVAILABLE or not s3_key:
            return False
        try:
            s3 = get_s3_client()
            return s3.move_to_processed(s3_key)
        except Exception as e:
            logger.warning(f"Failed to mark voice as processed: {e}")
            return False

    async def mark_voice_failed(self, farmer_id: str, s3_key: str) -> bool:
        """Mark voice note as failed (moves to failed prefix for 24h retry retention)."""
        if not S3_AVAILABLE or not s3_key:
            return False
        try:
            s3 = get_s3_client()
            return s3.move_to_failed(s3_key)
        except Exception as e:
            logger.warning(f"Failed to mark voice as failed: {e}")
            return False

    async def send_audio_message(
        self, to: str, audio_data: bytes, mime_type: str = "audio/ogg"
    ) -> bool:
        """
        Send an audio message via WhatsApp Business API.
        """
        logger.info(f"Sending audio message to {to}: {len(audio_data)} bytes")

        # In production, this would:
        # 1. Upload media to WhatsApp (POST /media)
        # 2. Send message with media_id (POST /messages)
        # For mock, just log and return success

        # Mock implementation - in production replace with actual API calls
        async with httpx.AsyncClient() as client:
            # Step 1: Upload media
            files = {"file": ("audio.ogg", audio_data, mime_type)}
            upload_response = await client.post(
                f"{self.base_url}/media",
                headers={"Authorization": f"Bearer {self.token}"},
                files=files,
            )
            media_id = upload_response.json().get("id")

            # Step 2: Send message
            message_payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "audio",
                "audio": {"id": media_id},
            }
            await client.post(
                f"{self.base_url}/messages", headers=self.headers, json=message_payload
            )

        return True

    async def send_text_message(self, to: str, text: str) -> bool:
        """
        Send a text message via WhatsApp Business API.
        """
        logger.info(f"Sending text message to {to}: {text[:50]}...")

        async with httpx.AsyncClient() as client:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            }
            response = await client.post(
                f"{self.base_url}/messages", headers=self.headers, json=payload
            )
            return response.status_code == 200

    async def close(self):
        """Close any connections."""


# Global instance (will be initialized with real config in production)
whatsapp_client = WhatsAppClient(token="dummy", phone_number_id="dummy")
