"""
Database connection management with per-agent least-privilege roles.
Each agent gets its own connection pool with minimal required permissions.
"""
import logging
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError

from src.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# Global engine instances per agent
_engines: Dict[str, AsyncEngine] = {}
_session_factories: Dict[str, async_sessionmaker] = {}

# Agent role configurations
AGENT_ROLES = {
    "irrigation": {
        "description": "Irrigation advisory - weather data read access",
        "tables": ["weather_forecasts", "cached_weather_forecasts", "farmer_profiles"]
    },
    "spoilage": {
        "description": "Spoilage risk - weather + shelf life data",
        "tables": ["weather_forecasts", "cached_weather_forecasts", "farmer_profiles", "shelf_life"]
    },
    "subsidy": {
        "description": "Subsidy schemes - scheme data + farmer profiles",
        "tables": ["schemes", "farmer_profiles"]
    },
    "market_price": {
        "description": "Market prices - mandi/price data + farmer profiles",
        "tables": ["market_prices", "mandi_prices", "farmer_profiles"]
    },
    "climate": {
        "description": "Climate alerts - weather data + farmer profiles",
        "tables": ["weather_forecasts", "cached_weather_forecasts", "farmer_profiles"]
    },
    "onboarding": {
        "description": "Farmer onboarding - full profile CRUD",
        "tables": ["farmer_profiles"]
    },
    "router": {
        "description": "Webhook router - session management + profile read",
        "tables": ["session_failures", "farmer_profiles"]
    },
    "default": {
        "description": "Default/migration - full access",
        "tables": ["*"]
    }
}


def build_database_url(role: str) -> str:
    """
    Build a database URL for a specific agent role.
    In production, this would use role-specific credentials from Secrets Manager.
    """
    base_url = settings.database_url
    
    # Replace credentials based on role
    role_credentials = {
        "irrigation": ("irrigation_agent", "irrigation_secure_pass"),
        "spoilage": ("spoilage_agent", "spoilage_secure_pass"),
        "subsidy": ("subsidy_agent", "subsidy_secure_pass"),
        "market_price": ("market_price_agent", "market_secure_pass"),
        "climate": ("climate_agent", "climate_secure_pass"),
        "onboarding": ("onboarding_agent", "onboarding_secure_pass"),
        "router": ("webhook_router", "router_secure_pass"),
        "migration": ("migration_runner", "migration_secure_pass"),
        "default": None  # Use base URL as-is
    }
    
    if role in role_credentials and role_credentials[role]:
        user, password = role_credentials[role]
        # Replace user:password in URL
        # Format: postgresql://user:pass@host:port/db
        import re
        base_url = re.sub(
            r'postgresql://([^:]+):([^@]+)@',
            f'postgresql://{user}:{password}@',
            base_url
        )
    
    # Ensure asyncpg driver
    return base_url.replace("postgresql://", "postgresql+asyncpg://", 1)


async def init_agent_engine(role: str = "default") -> AsyncEngine:
    """
    Initialize a database engine for a specific agent role.
    Engines are cached globally.
    """
    if role in _engines:
        return _engines[role]
    
    database_url = build_database_url(role)
    
    try:
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        
        # Test connection
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        _engines[role] = engine
        logger.info(f"Database engine initialized for role: {role}")
        return engine
        
    except Exception as e:
        logger.warning(f"Failed to initialize engine for role '{role}': {e}")
        # Fall back to default engine
        if role != "default":
            return await init_agent_engine("default")
        raise


async def get_agent_session(role: str = "default") -> AsyncSession:
    """
    Get an async session for a specific agent role.
    Creates engine and session factory if not exists.
    """
    if role not in _session_factories:
        engine = await init_agent_engine(role)
        _session_factories[role] = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
            class_=AsyncSession
        )
    
    async with _session_factories[role]() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.warning(f"Database error in {role} session: {e}")
            await session.rollback()
            yield None


async def get_db() -> AsyncSession:
    """Default database session (backward compatible)."""
    async for session in get_agent_session("default"):
        yield session


async def close_all_engines():
    """Close all database engines."""
    for role, engine in _engines.items():
        try:
            await engine.dispose()
            logger.info(f"Closed engine for role: {role}")
        except Exception as e:
            logger.error(f"Error closing engine for role {role}: {e}")
    _engines.clear()
    _session_factories.clear()


def get_agent_roles() -> Dict[str, Dict]:
    """Return the agent role configurations."""
    return AGENT_ROLES