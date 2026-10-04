"""
Cron worker to anonymize PII in query logs after 90 days.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from src.core.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QueryLogCleanupWorker")

# In a real implementation, you would have a QueryLog model
# For now, this demonstrates the pattern and would be adapted to your actual log table


async def run_cron():
    """
    Anonymize query logs older than 90 days.
    """
    if not AsyncSessionLocal:
        logger.error("Database not configured. Cannot run cron.")
        return

    logger.info("Starting query log anonymization worker...")

    # This is a template - adapt to your actual query log table
    # Example query log model would have:
    # - farmer_id (phone number)
    # - query_text
    # - timestamp
    # - intent
    # - is_anonymized flag

    cutoff_date = datetime.utcnow() - timedelta(days=90)

    logger.info(f"Anonymizing query logs older than {cutoff_date.isoformat()}")

    # Pseudocode for actual implementation:
    # async with AsyncSessionLocal() as db:
    #     # Find non-anonymized logs older than 90 days
    #     result = await db.execute(
    #         select(QueryLog).filter(
    #             QueryLog.timestamp < cutoff_date,
    #             QueryLog.is_anonymized == False
    #         )
    #     )
    #     logs = result.scalars().all()
    #
    #     for log in logs:
    #         # Anonymize: replace farmer_id with hash, remove PII from query_text
    #         log.farmer_id = hash_phone(log.farmer_id)
    #         log.query_text = "[ANONYMIZED]"
    #         log.is_anonymized = True
    #
    #     await db.commit()
    #     logger.info(f"Anonymized {len(logs)} query log entries")

    logger.info(
        "Query log anonymization worker finished (template - implement with actual log model)"
    )


def hash_phone(phone: str) -> str:
    """Create a consistent hash for phone number anonymization."""
    import hashlib

    return "ANON_" + hashlib.sha256(phone.encode()).hexdigest()[:12]


if __name__ == "__main__":
    asyncio.run(run_cron())
