import hmac
import hashlib
import re
from typing import Optional

def verify_whatsapp_signature(payload: bytes, signature_header: str, app_secret: str) -> bool:
    """
    Verifies that the incoming webhook payload is legitimately from Meta.
    Expects signature_header to be in the format 'sha256=....'
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    
    signature = signature_header.split("sha256=")[1]
    
    expected_hash = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_hash, signature)

def sanitize_input(text: Optional[str]) -> str:
    """
    Strips potentially harmful characters or prompt injection attempts from text.
    Treats all text as untrusted data.
    """
    if not text:
        return ""
    
    # Remove null bytes, control characters, and standard HTML/script tags
    clean_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    
    return clean_text.strip()
