#!/bin/bash
# Daily PostgreSQL backup script for KisanSaathi
# Run via cron: 0 2 * * * /path/to/backup_db.sh

set -e

# Configuration
DB_NAME="${DB_NAME:-kisan_saathi}"
DB_USER="${DB_USER:-kisan}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
S3_BUCKET="${S3_BUCKET:-kisan-saathi-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"
LATEST_LINK="${BACKUP_DIR}/${DB_NAME}_latest.sql.gz"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting backup of ${DB_NAME}..."

# Perform backup
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --no-owner \
    --no-privileges \
    --format=plain \
    | gzip > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup completed: ${BACKUP_FILE}"
    
    # Update latest symlink
    ln -sf "${BACKUP_FILE}" "${LATEST_LINK}"
    
    # Upload to S3 if configured
    if command -v aws &> /dev/null && [ -n "${S3_BUCKET}" ]; then
        echo "[$(date)] Uploading to S3..."
        aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/${DB_NAME}/"
        aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/${DB_NAME}/latest.sql.gz"
        echo "[$(date)] S3 upload completed"
    fi
    
    # Clean up old local backups
    find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    echo "[$(date)] Cleaned up local backups older than ${RETENTION_DAYS} days"
    
    # Clean up old S3 backups (optional, S3 lifecycle policy preferred)
    if command -v aws &> /dev/null && [ -n "${S3_BUCKET}" ]; then
        aws s3 ls "s3://${S3_BUCKET}/${DB_NAME}/" | while read -r line; do
            FILE_DATE=$(echo "$line" | awk '{print $1}')
            FILE_NAME=$(echo "$line" | awk '{print $4}')
            if [[ "$FILE_NAME" != "latest.sql.gz" ]]; then
                FILE_EPOCH=$(date -d "$FILE_DATE" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$FILE_DATE" +%s 2>/dev/null)
                NOW_EPOCH=$(date +%s)
                AGE_DAYS=$(( (NOW_EPOCH - FILE_EPOCH) / 86400 ))
                if [ $AGE_DAYS -gt ${RETENTION_DAYS} ]; then
                    aws s3 rm "s3://${S3_BUCKET}/${DB_NAME}/${FILE_NAME}"
                    echo "[$(date)] Deleted old S3 backup: ${FILE_NAME}"
                fi
            fi
        done
    fi
    
    echo "[$(date)] Backup process completed successfully"
else
    echo "[$(date)] ERROR: Backup failed!"
    rm -f "${BACKUP_FILE}"
    exit 1
fi