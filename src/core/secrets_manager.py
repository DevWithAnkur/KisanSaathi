"""
Secrets Manager Client for KisanSaathi
Supports AWS Secrets Manager and local .env fallback for development.
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

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


class SecretsManagerClient:
    """
    Client for retrieving secrets from AWS Secrets Manager.
    Falls back to environment variables for local development.
    """
    
    def __init__(self, region: str = None, secret_prefix: str = "kisan-saathi/"):
        self.region = region or os.getenv("AWS_REGION", "ap-south-1")
        self.secret_prefix = secret_prefix
        self._client = None
        self._secrets_cache: Dict[str, Any] = {}
        
    def _get_client(self):
        """Get or create the AWS Secrets Manager client."""
        if not BOTO3_AVAILABLE:
            return None
            
        if self._client is None:
            try:
                self._client = boto3.client('secretsmanager', region_name=self.region)
                # Test connection
                self._client.list_secrets(MaxResults=1)
                logger.info("AWS Secrets Manager connection established")
            except Exception as e:
                logger.warning(f"AWS Secrets Manager unavailable: {e}")
                self._client = None
        return self._client
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Get a secret value by name.
        First checks cache, then AWS Secrets Manager, then environment variables.
        """
        # Check cache first
        if secret_name in self._secrets_cache:
            return self._secrets_cache[secret_name]
        
        # Try AWS Secrets Manager
        client = self._get_client()
        if client:
            try:
                full_name = f"{self.secret_prefix}{secret_name}"
                response = client.get_secret_value(SecretId=full_name)
                secret_value = response.get('SecretString')
                if secret_value:
                    self._secrets_cache[secret_name] = secret_value
                    logger.info(f"Retrieved secret '{secret_name}' from AWS Secrets Manager")
                    return secret_value
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceNotFoundException':
                    logger.debug(f"Secret '{secret_name}' not found in AWS Secrets Manager")
                else:
                    logger.warning(f"Failed to get secret '{secret_name}': {e}")
            except Exception as e:
                logger.warning(f"Error retrieving secret '{secret_name}': {e}")
        
        # Fallback to environment variable
        env_value = os.getenv(secret_name.upper().replace('-', '_'))
        if env_value:
            logger.info(f"Using environment variable for '{secret_name}'")
            self._secrets_cache[secret_name] = env_value
            return env_value
        
        logger.debug(f"Secret '{secret_name}' not found in any source")
        return None
    
    def get_secret_json(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Get a secret and parse as JSON."""
        secret_str = self.get_secret(secret_name)
        if secret_str:
            try:
                return json.loads(secret_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse secret '{secret_name}' as JSON: {e}")
        return None
    
    def load_all_secrets(self) -> Dict[str, str]:
        """
        Load all secrets with the configured prefix from AWS Secrets Manager.
        Returns a dict of secret_name -> value.
        """
        client = self._get_client()
        if not client:
            logger.warning("AWS Secrets Manager not available, skipping bulk load")
            return {}
        
        try:
            paginator = client.get_paginator('list_secrets')
            secrets = {}
            
            for page in paginator.paginate(
                Filters=[{'Key': 'name', 'Values': [self.secret_prefix]}]
            ):
                for secret in page.get('SecretList', []):
                    name = secret['Name']
                    # Extract short name (remove prefix)
                    short_name = name.replace(self.secret_prefix, '')
                    value = self.get_secret(short_name)
                    if value:
                        secrets[short_name] = value
            
            logger.info(f"Loaded {len(secrets)} secrets from AWS Secrets Manager")
            return secrets
            
        except Exception as e:
            logger.error(f"Failed to load secrets from AWS: {e}")
            return {}
    
    def clear_cache(self):
        """Clear the secrets cache (useful for rotation)."""
        self._secrets_cache.clear()


# Global instance
secrets_manager = SecretsManagerClient()


@lru_cache(maxsize=1)
def get_secrets_manager() -> SecretsManagerClient:
    """Get the global secrets manager instance."""
    return secrets_manager