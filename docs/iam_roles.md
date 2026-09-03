# IAM Roles & Security Policies

As part of Phase 7 (Data Hygiene and Security), the following Least-Privilege IAM Roles are defined for the KisanSaathi production deployment.

## 1. API Gateway / Webhook Service Role
**Purpose**: Runs the FastAPI application that receives WhatsApp webhooks.
**Permissions**:
- **Allow**: `s3:PutObject` on `arn:aws:s3:::kisansaathi-voice-notes/voice_notes/*` (to temporarily store incoming audio before transcription).
- **Allow**: `secretsmanager:GetSecretValue` for WhatsApp API tokens, DB credentials, and Fernet encryption key.
- **Deny**: `s3:GetObject` on the voice notes bucket (the API should only write, not read back old voice notes).

## 2. Background Worker Role
**Purpose**: Processes the transcribed voice notes and executes Agent logic.
**Permissions**:
- **Allow**: `s3:GetObject` on `arn:aws:s3:::kisansaathi-voice-notes/voice_notes/*` (to pass audio to the STT engine).
- **Allow**: `s3:DeleteObject` on `arn:aws:s3:::kisansaathi-voice-notes/voice_notes/*` (to proactively delete the audio immediately after successful transcription, before the 1-day lifecycle policy kicks in).
- **Allow**: `secretsmanager:GetSecretValue` for Weather API keys and DB credentials.

## 3. Database Backup Role
**Purpose**: Executes the daily `pg_dump` cron job.
**Permissions**:
- **Allow**: `s3:PutObject` on `arn:aws:s3:::kisansaathi-db-backups/*`.
- **Allow**: `secretsmanager:GetSecretValue` for read-only DB credentials.

## S3 Data Hygiene (FR-27)
Voice notes are strictly ephemeral. 
1. The background worker deletes the audio object immediately after the Bhashini/Google STT engine returns the text transcript.
2. As a fallback, an S3 Lifecycle Policy (`scripts/setup_s3_lifecycle.json`) forces hard deletion of any object in the `voice_notes/` prefix after 1 day.
