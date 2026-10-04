#!/bin/bash
# PostgreSQL restore script for KisanSaathi
# Usage: ./restore_db.sh [backup_file|latest]

set -e

# Configuration
DB_NAME="${DB_NAME:-kisan_saathi}"
DB_USER="${DB_USER:-kisan}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
S3_BUCKET="${S3_BUCKET:-kisan-saathi-backups}"

# Determine backup file
if [ $# -eq 0 ]; then
    BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_latest.sql.gz"
    echo "Using latest backup: ${BACKUP_FILE}"
elif [ "$1" = "latest" ]; then
    BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_latest.sql.gz"
    echo "Using latest backup: ${BACKUP_FILE}"
elif [ "$1" = "list" ]; then
    echo "Available local backups:"
    ls -la "${BACKUP_DIR}"/${DB_NAME}_*.sql.gz 2>/dev/null | grep -v latest
    if command -v aws &> /dev/null && [ -n "${S3_BUCKET}" ]; then
        echo "Available S3 backups:"
        aws s3 ls "s3://${S3_BUCKET}/${DB_NAME}/" | grep -v latest
    fi
    exit 0
else
    BACKUP_FILE="$1"
    echo "Using specified backup: ${BACKUP_FILE}"
fi

# Check if file exists locally
if [ ! -f "${BACKUP_FILE}" ]; then
    # Try to download from S3
    if command -v aws &> /dev/null && [ -n "${S3_BUCKET}" ]; then
        FILENAME=$(basename "${BACKUP_FILE}")
        echo "Local file not found. Downloading from S3..."
        aws s3 cp "s3://${S3_BUCKET}/${DB_NAME}/${FILENAME}" "${BACKUP_FILE}"
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to download from S3"
            exit 1
        fi
    else
        echo "ERROR: Backup file not found: ${BACKUP_FILE}"
        exit 1
    fi
fi

echo "[$(date)] Starting restore of ${DB_NAME} from ${BACKUP_FILE}..."

# Confirm before proceeding (skip with -y flag)
if [ "$2" != "-y" ] && [ "$1" != "-y" ]; then
    read -p "This will REPLACE the database ${DB_NAME}. Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Restore cancelled."
        exit 0
    fi
fi

# Drop and recreate database
echo "[$(date)] Dropping and recreating database..."
PGPASSWORD="${DB_PASSWORD}" dropdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}" 2>/dev/null || true
PGPASSWORD="${DB_PASSWORD}" createdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}"

# Restore from backup
echo "[$(date)] Restoring data..."
gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -q

if [ $? -eq 0 ]; then
    echo "[$(date)] Restore completed successfully!"
else
    echo "[$(date)] ERROR: Restore failed!"
    exit 1
fi