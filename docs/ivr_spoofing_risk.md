# IVR Caller-ID Spoofing Risk & Mitigation

As part of Phase 8 (Climate Alerts & IVR Fallback), we have identified a security risk associated with the Interactive Voice Response (IVR) channel.

## The Risk
In the Twilio IVR fallback implementation, the system identifies the user based on the incoming Caller ID (e.g., the `From` parameter in the webhook payload). 

**Vulnerability:** Caller ID can be easily spoofed using various SIP manipulation techniques or malicious VoIP providers. An attacker could spoof a farmer's phone number to query the system and extract their profile details or manipulate their settings (e.g., changing their crop or location to receive incorrect subsidies).

## Accepted MVP Scope
For the hackathon MVP, this is an accepted risk. The current functionality focuses on read-only queries based on the spoofed profile, and does not yet allow critical write-operations or expose sensitive financial details directly.

## Production Mitigation Path
Before deploying the IVR system to production with real farmer data and profile-editing capabilities, the following mitigations will be implemented:

1. **Voice-PIN System**: 
   When a user calls from their registered number, the IVR will prompt them to enter or speak a 4-digit PIN configured during onboarding.
   
2. **Callback Verification for Sensitive Actions**: 
   If a user requests to change their profile data (e.g., land size or crop type) via IVR, the system will hang up and immediately call the registered number back to confirm the action. Since a spoofed caller cannot receive the callback to the real number, this completely neutralizes the spoofing threat for write-operations.
