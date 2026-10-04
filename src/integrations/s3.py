import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import boto3, but make it optional
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None
    ClientError = Exception


class S3Client:
    """S3 client for voice note storage with lifecycle management."""
    
    def __init__(self, bucket_name: str = None, region: str = None):
        self.bucket_name = bucket_name or os.getenv("S3_VOICE_BUCKET", "kisan-saathi-voice")
        self.region = region or os.getenv("AWS_REGION", "ap-south-1")
        self._client = None
        self._s3_resource = None
        
    def _get_client(self):
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 not available. Install boto3 to use S3 client.")
        if self._client is None:
            self._client = boto3.client('s3', region_name=self.region)
        return self._client
    
    def _get_resource(self):
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 not available. Install boto3 to use S3 client.")
        if self._s3_resource is None:
            self._s3_resource = boto3.resource('s3', region_name=self.region)
        return self._s3_resource
    
    def ensure_bucket_exists(self) -> bool:
        """Create bucket if it doesn't exist, and apply lifecycle policy."""
        if not BOTO3_AVAILABLE:
            logger.warning("boto3 not available, skipping S3 bucket creation")
            return False
            
        try:
            client = self._get_client()
            client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                    logger.info(f"Created bucket {self.bucket_name}")
                except ClientError as ce:
                    logger.error(f"Failed to create bucket: {ce}")
                    return False
            else:
                logger.error(f"Error checking bucket: {e}")
                return False
        
        # Apply lifecycle policy
        return self._apply_lifecycle_policy()
    
    def _apply_lifecycle_policy(self) -> bool:
        """Apply lifecycle policy to auto-delete voice notes after 1 day."""
        if not BOTO3_AVAILABLE:
            return False
            
        try:
            client = self._get_client()
            
            lifecycle_config = {
                'Rules': [
                    {
                        'ID': 'VoiceNoteAutoDelete',
                        'Status': 'Enabled',
                        'Filter': {
                            'Prefix': 'voice/'
                        },
                        'Expiration': {
                            'Days': 1
                        },
                        'NoncurrentVersionExpiration': {
                            'NoncurrentDays': 1
                        },
                        'AbortIncompleteMultipartUpload': {
                            'DaysAfterInitiation': 1
                        }
                    },
                    {
                        'ID': 'FailedTranscriptionRetry',
                        'Status': 'Enabled',
                        'Filter': {
                            'Prefix': 'voice/failed/'
                        },
                        'Expiration': {
                            'Days': 1
                        }
                    }
                ]
            }
            
            client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            logger.info(f"Applied lifecycle policy to bucket {self.bucket_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to apply lifecycle policy: {e}")
            return False
    
    def upload_voice_note(self, farmer_id: str, audio_data: bytes, mime_type: str, 
                          status: str = "pending") -> Optional[str]:
        """
        Upload voice note to S3.
        Returns the S3 key if successful, None otherwise.
        """
        if not BOTO3_AVAILABLE:
            logger.warning("boto3 not available, skipping S3 upload")
            return None
            
        try:
            client = self._get_client()
            
            # Generate key: voice/{status}/{farmer_id}/{timestamp}.{ext}
            import time
            timestamp = int(time.time() * 1000)
            ext = self._get_extension(mime_type)
            key = f"voice/{status}/{farmer_id}/{timestamp}.{ext}"
            
            client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=audio_data,
                ContentType=mime_type,
                Metadata={
                    'farmer_id': farmer_id,
                    'status': status,
                    'original_mime': mime_type
                }
            )
            
            logger.info(f"Uploaded voice note to s3://{self.bucket_name}/{key}")
            return key
            
        except ClientError as e:
            logger.error(f"Failed to upload voice note: {e}")
            return None
    
    def move_to_processed(self, key: str) -> bool:
        """Move voice note from pending to processed (triggers lifecycle deletion)."""
        if not BOTO3_AVAILABLE:
            return False
            
        try:
            client = self._get_client()
            
            # Copy to processed prefix, then delete original
            new_key = key.replace('voice/pending/', 'voice/processed/')
            
            client.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': key},
                Key=new_key
            )
            
            client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Moved voice note to processed: {new_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to move voice note to processed: {e}")
            return False
    
    def move_to_failed(self, key: str) -> bool:
        """Move voice note to failed prefix for retry (24h retention)."""
        if not BOTO3_AVAILABLE:
            return False
            
        try:
            client = self._get_client()
            
            new_key = key.replace('voice/pending/', 'voice/failed/')
            
            client.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': key},
                Key=new_key
            )
            
            client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Moved voice note to failed: {new_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to move voice note to failed: {e}")
            return False
    
    def delete_voice_note(self, key: str) -> bool:
        """Delete voice note from S3."""
        if not BOTO3_AVAILABLE:
            return False
            
        try:
            client = self._get_client()
            client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Deleted voice note: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete voice note: {e}")
            return False
    
    def _get_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        ext_map = {
            'audio/ogg': 'ogg',
            'audio/wav': 'wav',
            'audio/mp3': 'mp3',
            'audio/mp4': 'mp4',
            'audio/aac': 'aac',
            'audio/amr': 'amr',
            'audio/opus': 'opus',
        }
        return ext_map.get(mime_type, 'ogg')
    
    async def close(self):
        """Close any connections."""
        pass


# Global instance (initialized on demand)
s3_client = None

def get_s3_client() -> S3Client:
    global s3_client
    if s3_client is None:
        s3_client = S3Client()
    return s3_client