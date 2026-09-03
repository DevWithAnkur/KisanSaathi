#!/bin/bash
# scripts/db_backup.sh
# 
# This script performs a daily backup of the KisanSaathi PostgreSQL database.
# It should be run via a cron job (e.g., 0 2 * * * /path/to/db_backup.sh)

# Exit on any error
set -e

# Configuration
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="postgres"
DB_NAME="kisansaathi"
BACKUP_DIR="/var/backups/kisansaathi"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/kisansaathi_db_backup_$DATE.sql.gz"
RETENTION_DAYS=7

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "Starting KisanSaathi database backup: $BACKUP_FILE"

# Run pg_dump (requires PGPASSWORD to be set in the environment or .pgpass)
# Example: PGPASSWORD="yourpassword" ./db_backup.sh
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

echo "Backup completed successfully."

# Cleanup old backups
echo "Removing backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +$RETENTION_DAYS -exec rm {} \;

echo "Cleanup completed."
