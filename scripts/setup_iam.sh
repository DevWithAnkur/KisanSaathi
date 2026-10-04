#!/bin/bash
# PostgreSQL least-privilege IAM setup script for KisanSaathi
# Run as superuser (postgres): sudo -u postgres bash setup_iam.sh

set -e

DB_NAME="${DB_NAME:-kisan_saathi}"
DB_SUPERUSER="${DB_SUPERUSER:-postgres}"

echo "Setting up least-privilege IAM roles for database: $DB_NAME"

# Create roles for each agent
echo "Creating agent roles..."

# Irrigation agent - needs weather data access
psql -U "$DB_SUPERUSER" -d "$DB_NAME" -c "
CREATE ROLE irrigation_agent WITH LOGIN PASSWORD 'irrigation_secure_pass';
GRANT CONNECT ON DATABASE $DB_NAME TO irrigation_agent;
GRANT USAGE ON SCHEMA public TO irrigation_agent;
GRANT SELECT ON weather_forecasts, cached_weather_forecasts TO irrigation_agent;
GRANT SELECT ON farmer_profiles TO irrigation_agent;
" 2>/dev/null || echo "Tables may not exist yet - run migrations first"

# Spoilage agent - needs weather + shelf life data
psql -U "$DB_SUPERUSER" -d "$DB_NAME" -c "
CREATE ROLE spoilage_agent WITH LOGIN PASSWORD 'spoilage_secure_pass';
GRANT CONNECT ON DATABASE $DB_NAME TO spoilage_agent;
GRANT USAGE ON SCHEMA public TO spoilage_agent;
GRANT SELECT ON weather_forecasts, cached_weather_forecasts TO spoilage_agent;
GRANT SELECT ON farmer_profiles, shelf_life TO spoilage_agent;
" 2>/dev/null || echo "Tables may not exist yet"

# Subsidy agent - needs scheme data
psql -U "$DB_SUPERUSER" -d "$DB_NAME" -c "
CREATE ROLE subsidy_agent WITH LOGIN PASSWORD 'subsidy_secure_pass';
GRANT CONNECT ON DATABASE $DB_NAME TO subsidy_agent;
GRANT USAGE ON SCHEMA public TO subsidy_agent;
GRANT SELECT ON schemes, farmer_profiles TO subsidy_agent;
" 2>/dev/null || echo "Tables may not exist yet"

# Market price agent - needs market data
psql -U "$DB_SUPERUSER" -d "$DB_NAME" -c "
CREATE ROLE market_price_agent WITH LOGIN PASSWORD 'market_secure_pass';
GRANT CONNECT ON DATABASE $DB_NAME TO market_price_agent;
GRANT USAGE ON SCHEMA public TO market_price_agent;
GRANT SELECT ON market_prices, mandi_prices, farmer_profiles TO market_price_agent;
" 2>/dev/null || echo "Tables may not exist yet"

# Climate agent - needs weather data
psql -U "$DB_SUPERUSER" -d "$DB_NAME" -c "
CREATE ROLE climate_agent WITH LOGIN PASSWORD 'climate_secure_pass';
GRANT CONNECT ON DATABASE $DB_NAME TO climate_agent;
GRANT USAGE ON SCHEMA public TO climate_agent;
GRANT SELECT ON weather_forecasts, cached_weather_forecasts, farmer_profiles TO climate_agent;
" 2>/dev/null || echo "Tables may not exist yet"

# Onboarding agent - needs full profile CRUD
psql -U "$DB_SUPERUSER" -d "$DB_NAME" -c "
CREATE ROLE onboarding_agent WITH LOGIN PASSWORD 'onboarding_secure_pass';
GRANT CONNECT ON DATABASE $DB_NAME TO onboarding_agent;
GRANT USAGE ON SCHEMA public TO onboarding_agent;
GRANT SELECT, INSERT, UPDATE ON farmer_profiles TO onboarding_agent;
" 2>/dev/null || echo "Tables may not exist yet"

# Webhook/router - minimal read access for session/failure tracking
psql -U "$DB_SUPERUSER" -d "$DB_NAME" -c "
CREATE ROLE webhook_router WITH LOGIN PASSWORD 'router_secure_pass';
GRANT CONNECT ON DATABASE $DB_NAME TO webhook_router;
GRANT USAGE ON SCHEMA public TO webhook_router;
GRANT SELECT, INSERT, UPDATE ON session_failures TO webhook_router;
GRANT SELECT ON farmer_profiles TO webhook_router;
" 2>/dev/null || echo "Tables may not exist yet"

# Migration role - for running alembic migrations
psql -U "$DB_SUPERUSER" -d "$DB_NAME" -c "
CREATE ROLE migration_runner WITH LOGIN PASSWORD 'migration_secure_pass';
GRANT CONNECT ON DATABASE $DB_NAME TO migration_runner;
GRANT USAGE ON SCHEMA public TO migration_runner;
GRANT CREATE ON SCHEMA public TO migration_runner;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO migration_runner;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO migration_runner;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO migration_runner;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO migration_runner;
" 2>/dev/null || echo "Tables may not exist yet"

echo "IAM roles created successfully!"

# Show created roles
echo ""
echo "Created roles:"
psql -U "$DB_SUPERUSER" -d "$DB_NAME" -c "\du" | grep -E "(irrigation|spoilage|subsidy|market|climate|onboarding|webhook|migration)_agent"

echo ""
echo "Next steps:"
echo "1. Run database migrations with migration_runner role"
echo "2. Update application config to use agent-specific DB URLs"
echo "2. Example: postgresql://irrigation_agent:irrigation_secure_pass@localhost:5432/kisan_saathi"
echo "3. Store passwords in AWS Secrets Manager"