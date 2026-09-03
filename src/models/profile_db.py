import os
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.types import TypeDecorator
from cryptography.fernet import Fernet
from datetime import datetime
from src.core.database import Base

# A static key for MVP, normally loaded from env
# E.g. Fernet.generate_key() -> b'x_...'
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", b'lR9N4tG8B6y-h0rN4_6wP3wzQc5JpA7bM2mZ_H8V4Xw=')
fernet = Fernet(ENCRYPTION_KEY)

class EncryptedString(TypeDecorator):
    """
    Transparently encrypts and decrypts strings on the way in and out of the DB.
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return fernet.encrypt(value.encode('utf-8')).decode('utf-8')
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return fernet.decrypt(value.encode('utf-8')).decode('utf-8')
        return value

class FarmerProfileDB(Base):
    __tablename__ = "farmer_profiles"

    # phone_number is used as the primary key/ID for the farmer
    phone_number = Column(String, primary_key=True, index=True)
    
    # Consent flag (FR-27)
    consent_given = Column(Boolean, default=False, nullable=False)
    
    # State tracking for the onboarding flow
    onboarding_step = Column(String, default="consent") # consent -> location -> crop -> details -> complete
    
    # Encrypted fields
    state = Column(EncryptedString, nullable=True)
    district = Column(EncryptedString, nullable=True)
    crop = Column(EncryptedString, nullable=True)
    land_size_ha = Column(EncryptedString, nullable=True) # Stored as string to simplify encryption
    category = Column(EncryptedString, nullable=True)
    harvest_date = Column(EncryptedString, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
