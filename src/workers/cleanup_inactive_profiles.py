"""
Cron worker to handle inactive profiles (notify then archive after 12 months).
"""

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.future import select

from src.core.database import AsyncSessionLocal
from src.models.profile_db import FarmerProfileDB
from src.integrations.whatsapp import WhatsAppClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InactiveProfileCleanupWorker")


async def run_cron():
    """
    Check for inactive profiles and send notification / archive.
    - Profiles inactive for 11 months: send notification
    - Profiles inactive for 12 months: archive (mark as inactive)
    """
    if not AsyncSessionLocal:
        logger.error("Database not configured. Cannot run cron.")
        return

    logger.info("Starting inactive profile cleanup worker...")

    # Initialize WhatsApp client for notifications
    # In production, initialize with real credentials
    whatsapp = WhatsAppClient(token="dummy", phone_number_id="dummy")

    now = datetime.utcnow()
    notify_cutoff = now - timedelta(days=330)  # 11 months
    archive_cutoff = now - timedelta(days=365)  # 12 months

    async with AsyncSessionLocal() as db:
        # Find profiles that have been inactive for 11 months (send notification)
        notify_result = await db.execute(
            select(FarmerProfileDB).filter(
                FarmerProfileDB.onboarding_step == "complete",
                FarmerProfileDB.updated_at < notify_cutoff,
                FarmerProfileDB.updated_at >= archive_cutoff,
                FarmerProfileDB.alert_opt_in == True,  # Only notify if they opted in
            )
        )
        notify_profiles = notify_result.scalars().all()

        for profile in notify_profiles:
            logger.info(f"Sending inactivity notification to {profile.phone_number}")
            try:
                await whatsapp.send_text_message(
                    profile.phone_number,
                    "We noticed you haven't used KisanSaathi in a while. "
                    "We're here to help with irrigation, crop health, subsidies, and market prices. "
                    "Just send us a message anytime!",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to send notification to {profile.phone_number}: {e}"
                )

        # Find profiles that have been inactive for 12 months (archive)
        archive_result = await db.execute(
            select(FarmerProfileDB).filter(
                FarmerProfileDB.onboarding_step == "complete",
                FarmerProfileDB.updated_at < archive_cutoff,
            )
        )
        archive_profiles = archive_result.scalars().all()

        for profile in archive_profiles:
            logger.info(f"Archiving inactive profile: {profile.phone_number}")
            # Mark as archived by setting a special step
            profile.onboarding_step = "archived"
            profile.alert_opt_in = False  # Stop all alerts

        if archive_profiles:
            await db.commit()
            logger.info(f"Archived {len(archive_profiles)} inactive profiles")

        if notify_profiles:
            logger.info(
                f"Sent notifications to {len(notify_profiles)} inactive farmers"
            )

    await whatsapp.close()
    logger.info("Inactive profile cleanup worker finished.")


if __name__ == "__main__":
    asyncio.run(run_cron())
