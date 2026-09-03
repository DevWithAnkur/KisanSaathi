import asyncio
import logging
from sqlalchemy.future import select

# In a real app, these dependencies would be properly managed
from src.core.database import AsyncSessionLocal
from src.models.profile_db import FarmerProfileDB
from src.agents.climate import ClimateAgent
from src.integrations.weather import WeatherClient
from src.models.contracts import AgentRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClimateCronWorker")

async def run_cron():
    """
    Scheduled job to check weather anomalies and push alerts.
    """
    if not AsyncSessionLocal:
        logger.error("Database not configured. Cannot run cron.")
        return
        
    logger.info("Starting scheduled climate alert worker...")
    
    weather_client = WeatherClient()
    climate_agent = ClimateAgent(weather_client)
    
    async with AsyncSessionLocal() as db:
        # Fetch all farmers who have completed onboarding and given consent
        result = await db.execute(
            select(FarmerProfileDB).filter(
                FarmerProfileDB.onboarding_step == "complete",
                FarmerProfileDB.consent_given == True
            )
        )
        profiles = result.scalars().all()
        
        for profile in profiles:
            logger.info(f"Checking climate for farmer {profile.phone_number} in {profile.district}, {profile.state}...")
            
            # Create a mock request to reuse the ClimateAgent logic
            request = AgentRequest(
                farmer_id=profile.phone_number,
                session_id="cron_session",
                message_id="cron_msg",
                language="en",
                query_text="cron trigger",
                profile={
                    "state": profile.state,
                    "district": profile.district,
                    # We could map state/district to lat/lon here, or ClimateAgent will use fallback
                },
                correlation_id="cron"
            )
            
            response = await climate_agent.process_request(request)
            
            if response.verification_status == "verified" and "WARNING" in response.text:
                logger.info(f"ALERT TRIGGERED for {profile.phone_number}: {response.text}")
                # In a live system, we would push this via Twilio SMS, WhatsApp, or IVR outbound call here
                # e.g., twilio_client.messages.create(to=profile.phone_number, body=response.text)
            else:
                logger.info(f"No alert for {profile.phone_number}.")
                
    logger.info("Climate alert worker finished.")

if __name__ == "__main__":
    asyncio.run(run_cron())
