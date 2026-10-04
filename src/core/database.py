import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from src.core.config import settings

logger = logging.getLogger(__name__)

# asyncpg requires the driver-specific PostgreSQL URL scheme.
DATABASE_URL = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://", 1
)

engine = None
AsyncSessionLocal = None


async def init_db():
    """Initialize database connection. Call on startup."""
    global engine, AsyncSessionLocal
    try:
        engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        # Test connection
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        AsyncSessionLocal = async_sessionmaker(
            bind=engine, expire_on_commit=False, class_=AsyncSession
        )
        logger.info("Database connection established")
        return True
    except Exception as e:
        logger.warning(f"Database unavailable: {e}")
        engine = None
        AsyncSessionLocal = None
        return False


Base = declarative_base()


async def get_db():
    if AsyncSessionLocal is None:
        yield None
        return

    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.warning(f"Database error during session: {e}")
            yield None
