"""
Cron worker to clean up failed transcription audio files (>24 hours).
"""

import asyncio
import logging
from datetime import datetime, timedelta

from src.integrations.s3 import get_s3_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FailedAudioCleanupWorker")


async def run_cron():
    """
    Delete failed voice notes in S3 that are older than 24 hours.
    Uses S3 lifecycle policy, but this provides a manual fallback.
    """
    logger.info("Starting failed audio cleanup worker...")

    s3 = get_s3_client()

    if not hasattr(s3, "_get_client"):
        logger.warning("S3 client not available, skipping cleanup")
        return

    try:
        client = s3._get_client()
        bucket = s3.bucket_name

        # List objects in voice/failed/ prefix
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix="voice/failed/")

        deleted_count = 0
        cutoff = datetime.utcnow() - timedelta(hours=24)

        for page in pages:
            for obj in page.get("Contents", []):
                # Check if object is older than 24 hours
                if obj["LastModified"].replace(tzinfo=None) < cutoff:
                    try:
                        client.delete_object(Bucket=bucket, Key=obj["Key"])
                        deleted_count += 1
                        logger.info(f"Deleted old failed audio: {obj['Key']}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {obj['Key']}: {e}")

        logger.info(f"Failed audio cleanup finished. Deleted {deleted_count} objects.")

    except Exception as e:
        logger.error(f"Failed audio cleanup error: {e}")


if __name__ == "__main__":
    asyncio.run(run_cron())
