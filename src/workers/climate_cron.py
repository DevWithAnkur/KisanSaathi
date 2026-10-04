import asyncio
import logging
from sqlalchemy.future import select

# In a real app, these dependencies would be properly managed
from src.core.database import AsyncSessionLocal
from src.models.profile_db import FarmerProfileDB
from src.agents.climate import ClimateAgent
from src.integrations.weather import WeatherClient
from src.models.contracts import AgentRequest
from src.integrations.whatsapp import whatsapp_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClimateCronWorker")


async def run_cron():
    """
    Scheduled job to check weather anomalies and push alerts via WhatsApp.
    Only sends to farmers who have alert_opt_in = True.
    """
    if not AsyncSessionLocal:
        logger.error("Database not configured. Cannot run cron.")
        return

    logger.info("Starting scheduled climate alert worker...")

    weather_client = WeatherClient()
    climate_agent = ClimateAgent(weather_client)

    # Initialize WhatsApp client
    # In production, this would use real credentials from settings
    # whatsapp_client.token = settings.whatsapp_api_token
    # whatsapp_client.phone_number_id = settings.whatsapp_phone_number_id

    async with AsyncSessionLocal() as db:
        # Fetch all farmers who have completed onboarding, given consent, and opted in for alerts
        result = await db.execute(
            select(FarmerProfileDB).filter(
                FarmerProfileDB.onboarding_step == "complete",
                FarmerProfileDB.consent_given == True,
                FarmerProfileDB.alert_opt_in == True,
            )
        )
        profiles = result.scalars().all()

        alert_count = 0

        for profile in profiles:
            logger.info(
                f"Checking climate for farmer {profile.phone_number} in {profile.district}, {profile.state}..."
            )

            # Create a mock request to reuse the ClimateAgent logic
            request = AgentRequest(
                farmer_id=profile.phone_number,
                session_id="cron_session",
                message_id="cron_msg",
                language=(
                    profile.language
                    if hasattr(profile, "language") and profile.language
                    else "en"
                ),
                query_text="cron trigger",
                profile={
                    "state": profile.state,
                    "district": profile.district,
                    # We could map state/district to lat/lon here, or ClimateAgent will use fallback
                },
                correlation_id="cron",
            )

            response = await climate_agent.process_request(request)

            # Check if there's a warning in the response
            has_warning = response.verification_status == "verified" and any(
                keyword in response.text.upper()
                for keyword in ["WARNING", "चेतावनी", "ALERT"]
            )

            if has_warning:
                logger.info(
                    f"ALERT TRIGGERED for {profile.phone_number}: {response.text}"
                )

                # Send alert via WhatsApp
                try:
                    success = await whatsapp_client.send_text_message(
                        profile.phone_number, response.text
                    )
                    if success:
                        alert_count += 1
                        logger.info(f"Climate alert sent to {profile.phone_number}")
                    else:
                        logger.warning(
                            f"Failed to send climate alert to {profile.phone_number}"
                        )
                except Exception as e:
                    logger.error(
                        f"Error sending climate alert to {profile.phone_number}: {e}"
                    )
            else:
                logger.info(f"No alert for {profile.phone_number}.")

    logger.info(f"Climate alert worker finished. Sent {alert_count} alerts.")


if __name__ == "__main__":
    asyncio.run(run_cron())
