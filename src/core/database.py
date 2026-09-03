import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

# Using an environment variable or default
# Format: postgresql+asyncpg://user:password@host:port/dbname
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/kisansaathi"

try:
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
except Exception as e:
    logger.error(f"Failed to create async engine: {e}")
    engine = None
    AsyncSessionLocal = None

Base = declarative_base()

async def get_db():
    if AsyncSessionLocal is None:
        yield None
        return
        
    async with AsyncSessionLocal() as session:
        yield session
