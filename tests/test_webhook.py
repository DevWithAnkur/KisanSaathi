from fastapi.testclient import TestClient
from src.api.main import app
from src.core.config import settings
import hmac
import hashlib
import json

client = TestClient(app)

def test_verify_webhook_success():
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "12345",
            "hub.verify_token": settings.whatsapp_verify_token
        }
    )
    assert response.status_code == 200
    assert response.text == "12345"

def test_verify_webhook_failure():
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "12345",
            "hub.verify_token": "wrong_token"
        }
    )
    assert response.status_code == 403

def test_webhook_invalid_signature():
    payload = {"object": "whatsapp_business_account", "entry": []}
    response = client.post(
        "/webhook",
        json=payload,
        headers={"x-hub-signature-256": "sha256=invalid_signature"}
    )
    assert response.status_code == 403

def generate_signature(payload_bytes: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

def test_webhook_valid_signature_text_message():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "1234", "phone_number_id": "5678"},
                            "contacts": [{"profile": {"name": "Test"}, "wa_id": "9999"}],
                            "messages": [
                                {
                                    "from": "9999",
                                    "id": "wamid.123",
                                    "timestamp": "123456789",
                                    "type": "text",
                                    "text": {"body": "how to irrigate"}
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = generate_signature(payload_bytes, settings.whatsapp_api_token)
    
    response = client.post(
        "/webhook",
        content=payload_bytes,
        headers={"x-hub-signature-256": signature, "Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "irrigation"
