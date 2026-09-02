# KisanSaathi Implementation Plan

## 1. Implementation Objective

Build a voice-first farmer advisory service around one WhatsApp/IVR number. The MVP must accept text and voice queries, identify the farmer, route each query to an independent domain agent, use verified data sources, and return one short answer in the farmer's language.

The implementation should prioritize Phases 0-7 as the demo-critical path. Phases 8-10 complete the stretch features, security validation, and presentation readiness. Security controls marked as critical are mandatory even when time is limited.

## 2. MVP Priorities

### Demo-critical

- WhatsApp text and voice-note intake
- Webhook authentication and input validation
- Speech-to-text, language handling, and intent routing
- Irrigation Advisory Agent
- Spoilage Risk Agent
- At least one of the Subsidy or Market Price agents, preferably both
- Voice response generation and delivery
- Farmer onboarding and profile storage
- Source attribution and output verification for subsidy/price responses
- Cached last-known advisory and documented low-connectivity behavior
- Unit, integration, security, and scripted end-to-end tests

### Stretch

- Climate alert scheduler
- IVR fallback through Twilio or Exotel
- PWA companion cache
- Lightweight NLU model instead of keyword classification
- Satellite/NDVI integration
- Expanded language and state-scheme coverage

### Explicitly out of scope

- Physical IoT or soil-moisture hardware
- Native mobile application
- Payment, fintech, marketplace, or buyer negotiation features
- Filing subsidy applications on behalf of farmers
- Crop-disease image scanning
- Full ML model training
- Formal penetration testing or production-grade certification
- Strong IVR caller authentication beyond documented caller-ID limitations

## 3. Phase-by-Phase Plan

## Phase 0 - Project Setup and Decisions

**Timing:** Day 1, first few hours

### Objectives

Create the working foundation, select concrete services, and prevent credentials, data, and deployment decisions from becoming blockers later.

### Tasks

- Confirm the backend framework: Node.js with Express or Python with FastAPI.
- Initialize the repository structure for API gateway, router, agents, integrations, data models, workers, tests, and configuration.
- Set up local development, environment variables, formatting, linting, and test commands.
- Create development and production-like configuration profiles without committing secrets.
- Create a WhatsApp Business API sandbox, test number, webhook URL, and Meta application.
- Register for weather API access and Bhashini or Google ASR/TTS access.
- Confirm Agmarknet/eNAM access and rate limits.
- Curate the first scheme dataset from PM-KISAN, PMFBY, KCC, PM Kusum, and selected state schemes.
- Choose PostgreSQL, Redis, temporary voice storage, and a hosting provider.
- Configure an India-region cloud project where possible.
- Set up a secrets manager or secure environment configuration from the beginning.
- Define the initial billing cap and alerts for every paid service.
- Assign owners for backend, agents, language services, data/infra, and demo/pitch work.

### Deliverables

- Runnable backend skeleton
- Local setup instructions
- Environment variable specification
- Initial scheme dataset with source URLs and last-updated dates
- Service and ownership decisions
- Cloud project and secrets configuration

### Completion checks

- The application starts locally with a health endpoint.
- A test webhook can reach the backend.
- No API key or personal data is committed to the repository.
- A sample scheme record can be loaded and queried.

## Phase 1 - Secure Query Pipeline and Agent Router

**Timing:** Day 1-2

### Objectives

Build the shared pipeline that receives a farmer message, validates it, identifies intent, and dispatches it to exactly one domain handler.

### Tasks

- Implement the WhatsApp webhook endpoint for text and voice messages.
- Verify Meta's `X-Hub-Signature-256` before processing any inbound webhook.
- Reject and log invalid signatures without routing the message.
- Validate voice-note MIME type, codec, file size, duration, and download response.
- Add rate limiting per phone number and source IP with thresholds documented in configuration.
- Add request timeouts, retry limits, and safe error responses.
- Download voice media to temporary storage only after validation.
- Integrate speech-to-text for the selected language set.
- Capture transcription confidence and ask the farmer to repeat low-confidence input.
- Detect or select language and normalize the internal query representation.
- Treat all transcribed and typed content as untrusted input.
- Sanitize values before database queries, agent calls, or any generative prompt.
- Implement five-way intent classification: irrigation, spoilage, climate, subsidy, and market price.
- Support an unclassified state and return a spoken five-option menu.
- Track repeated classification failures and fall back to the menu after two failures in one session.
- Define a common agent request and response contract.
- Add machine-readable source tags, timestamps, confidence, and cache metadata to responses.
- Make each agent independently callable and independently failure-tolerant.

### Deliverables

- Authenticated WhatsApp webhook
- Voice validation and transcription flow
- Intent classifier and router
- Shared agent interface
- Spoken fallback menu
- Structured request/response logging

### Completion checks

- Invalid webhook signatures are rejected.
- Oversized and malformed audio is rejected without reaching STT.
- Low-confidence transcription requests a repeat.
- Representative queries route to the correct agent.
- Unclassified queries receive the five-option menu.
- Rate limits return a controlled response and create an audit event.

## Phase 2 - Irrigation Advisory Agent

**Timing:** Day 2

### Objectives

Deliver the primary energy- and water-saving feature: a simple, explainable decision on whether to irrigate.

### Tasks

- Define the crop, growth-stage, rainfall, temperature, and humidity inputs.
- Retrieve the farmer's approximate location and crop profile.
- Integrate the weather API for a local or nearest-district 48-hour forecast.
- Cache successful weather responses with timestamp and source.
- Define crop-water-need and rainfall-threshold rules for the initial supported crops.
- Implement the binary recommendation: irrigate or skip.
- Handle missing or stale weather data explicitly.
- Format the result as one short sentence in the selected language.
- Convert the response to speech and send it through WhatsApp.
- If pump type and motor information are available, estimate avoided pump energy using a documented local benchmark.
- Include the source and timestamp in the internal response metadata.

### Deliverables

- Irrigation rule engine
- Weather integration and cache
- Text and voice response formatter
- Optional pump-energy estimate

### Completion checks

- Rain above the configured threshold produces a skip recommendation.
- Dry conditions produce an irrigate recommendation.
- Weather failure returns cached data with its age, or an explicit unavailable message.
- The complete voice flow works through the WhatsApp sandbox within the 30-second target.

## Phase 3 - Spoilage Risk Agent

**Timing:** Day 2-3

### Objectives

Warn farmers early enough to sell or store harvested crops before avoidable post-harvest loss.

### Tasks

- Define the supported crop list and shelf-life lookup table.
- Capture or retrieve crop type and harvest date.
- Integrate local temperature and humidity trends.
- Implement the spoilage calculation using shelf life and environmental conditions.
- Map the result to Green, Yellow, or Red.
- Define a clear action for every risk level:
  - Green: safe to store
  - Yellow: sell within a defined number of days
  - Red: sell or move immediately
- Reuse the response, source-tagging, TTS, and WhatsApp delivery pipeline.
- Add handling for missing harvest dates or unsupported crops.

### Deliverables

- Crop shelf-life dataset
- Spoilage risk calculator
- Risk-level response formatter
- Voice alert response

### Completion checks

- Known test cases produce the expected risk level.
- Missing required information results in one targeted question.
- The response contains a practical action, not only a color label.
- Weather data failure is clearly reported or served from cache with age.

## Phase 4 - Subsidy Scheme Agent

**Timing:** Day 3

### Objectives

Match a farmer's profile against a small, trustworthy scheme dataset and provide one actionable next step.

### Tasks

- Define the scheme schema: name, state, crops, land limits, category rules, benefit, next action, source, and last-updated date.
- Load and validate the curated central and state scheme records.
- Implement matching using state, crop, land size, and farmer category.
- Check profile completeness before matching.
- Ask exactly one targeted voice question when a required field is missing.
- Return scheme name, one-line benefit, next action, source, and update date.
- Make clear that the system guides the farmer and does not submit the application.
- Implement output verification before sending any scheme name or amount.
- Block generated or malformed responses that do not match the scheme database.
- Return a safe unavailable response when verification fails or the dataset is stale/unavailable.
- Add a defined monthly refresh process and dataset version field.

### Deliverables

- Versioned scheme dataset
- Eligibility matcher
- Missing-profile-field flow
- Source-verification layer
- Scheme response with application guidance

### Completion checks

- Eligible and ineligible profile fixtures produce expected results.
- Missing profile data triggers one focused question.
- A deliberately fabricated scheme or benefit is blocked.
- Every spoken scheme response has a matching source record and update date.

## Phase 5 - Market Price Agent

**Timing:** Day 3

### Objectives

Give farmers a verifiable mandi price range and help them identify offers that are meaningfully below it.

### Tasks

- Integrate Agmarknet and/or eNAM for the selected crops.
- Resolve the nearest two or three mandis from the farmer's approximate location.
- Retrieve price range, unit, market, MSP where available, source, and timestamp.
- Cache the latest successful price response in Redis.
- Extract an offered price from the farmer's query where possible.
- Compare the offered price with the verified range.
- Flag offers that are below the configured meaningful-deviation threshold.
- Format one concise response containing price range, MSP comparison, source, and timestamp.
- State when the value is cached or unavailable instead of presenting stale data as current.
- Implement output verification so spoken price figures must match the retrieved source record.
- Surface discrepancies when cached and fresh sources disagree.

### Deliverables

- Mandi integration
- Nearest-market lookup
- Price comparison logic
- MSP comparison response
- Price source-verification layer

### Completion checks

- A known market fixture returns the expected range and source.
- A below-range offer produces the warning response.
- Deliberately mismatched price output is blocked.
- API failure returns cached data with age or an explicit unavailable message.

## Phase 6 - Farmer Onboarding and Profile Management

**Timing:** Day 3

### Objectives

Capture only the profile information required for accurate advisories and subsidy matching, using a voice-first flow.

### Tasks

- Identify farmers by their registered WhatsApp phone number.
- Build a one-time guided onboarding flow for location, crop, land size, and language.
- Collect farmer category only when needed for subsidy matching where possible.
- Add optional pump type and motor size fields for energy estimates.
- Add explicit spoken consent covering collected data and voice-recording handling.
- Communicate the advisory-only disclaimer in simple language.
- Store profile data in PostgreSQL with appropriate access controls and encryption at rest.
- Add profile update and missing-field handling.
- Add `STOP` and spoken equivalent for opting out of proactive alerts.
- Add voice/text requests for profile summary and deletion request.
- Route deletion requests to a human-reviewed MVP queue.
- Keep intermediary access optional and limited to aggregated, non-PII information.

### Deliverables

- Farmer profile schema and migrations
- Voice onboarding flow
- Consent and disclaimer prompts
- Profile update, access, deletion, and opt-out flows

### Completion checks

- A new number is onboarded without a form or password.
- Returning farmers are recognized by phone number.
- Consent is recorded before profile use.
- Profile data can be summarized and deletion can be queued.
- Sensitive fields cannot be read by unauthorized service components.

## Phase 7 - Offline Resilience, Caching, and Data Hygiene

**Timing:** Day 3-4

### Objectives

Keep the service useful when live connectivity or an external data source is unavailable, while minimizing retained sensitive data.

### Tasks

- Cache the last successful advisory for each farmer and agent type in Redis.
- Include source, timestamp, and cache age in cached responses.
- Define behavior for queries received during a connectivity gap.
- Queue eligible messages and process them after reconnection where channel behavior permits.
- Prevent duplicate processing using message IDs and idempotency keys.
- Store voice notes only in temporary storage.
- Delete raw audio after successful transcription.
- Retain failed-transcription audio for less than 24 hours only for retry.
- Apply a 90-day retention period to query/response logs, then anonymize or delete them.
- Define inactive-profile handling after 12 months with prior notification.
- Configure automated daily PostgreSQL backups.
- Document and test a basic restore procedure.
- Apply least-privilege credentials for agents and integrations.

### Deliverables

- Redis cache and queue behavior
- Idempotent message processing
- Voice-storage lifecycle policy
- Retention and deletion jobs
- Daily backup and restore documentation
- IAM/service credential boundaries

### Completion checks

- A cached advisory remains retrievable when the external API is unavailable.
- Cached responses identify their age.
- Duplicate webhooks do not create duplicate responses.
- Raw audio is deleted after transcription.
- A database backup can be restored in a test environment.

## Phase 8 - Climate Alerts and IVR Fallback

**Timing:** Day 4, stretch

### Objectives

Extend the service from query-driven advice to proactive climate resilience alerts and feature-phone access.

### Tasks

- Build a scheduled forecast-checking worker.
- Define heat-stress, irregular-rainfall, and frost thresholds.
- Select opted-in farmers by region and language.
- Send short proactive voice alerts with source and timestamp.
- Implement simple opt-in and opt-out commands.
- Integrate Twilio or Exotel IVR if time permits.
- Mirror the WhatsApp routing and response behavior in IVR prompts.
- Document caller-ID authentication limitations and spoofing risk.
- Do not represent caller-ID-only authentication as solved security.
- Define a future voice-PIN or callback-verification approach for sensitive profile changes.

### Deliverables

- Forecast alert worker
- Alert preference handling
- Climate alert templates
- IVR prototype or documented integration path
- IVR risk and mitigation note

### Completion checks

- A forecast fixture triggers an alert only for matching regions and opted-in farmers.
- Opted-out farmers receive no proactive alerts.
- IVR callers can complete at least one advisory flow if the integration is implemented.
- Caller authentication limitations are visible in documentation and demo notes.

## Phase 9 - Security Pass and Adversarial Testing

**Timing:** Day 4

### Objectives

Demonstrate that the service rejects forged requests, abusive inputs, prompt-injection attempts, and unverifiable financial or scheme claims.

### Tasks

- Add dependency scanning through GitHub Dependabot or equivalent.
- Add a basic SAST scan such as Semgrep to CI.
- Resolve high-severity findings that affect the demo path.
- Test invalid, missing, and altered WhatsApp signatures.
- Test oversized, malformed, unsupported, and corrupt voice files.
- Test rate-limit thresholds and reset behavior.
- Create 5-10 adversarial inputs covering:
  - Requests to fabricate subsidy names or amounts
  - Requests to override agent instructions
  - Attempts to access another farmer's profile
  - Prompt injection embedded in transcribed voice text
  - Requests to bypass source verification
- Confirm all transcribed text is handled as data, not system instructions.
- Test output verification with mismatched scheme, amount, price, source, and timestamp.
- Test conflicting fresh and cached data behavior.
- Review logs for unnecessary personally identifiable information.
- Confirm third-party credentials are supplied only through secrets management.
- Record results and unresolved risks in the demo checklist.

### Deliverables

- CI dependency and SAST checks
- Adversarial test set and results
- Webhook, input-validation, rate-limit, and verification test results
- Security findings and residual-risk list

### Completion checks

- Forged webhooks never reach the router.
- Untrusted or oversized audio is rejected safely.
- Prompt-injection inputs cannot produce unverifiable scheme or price claims.
- Verification failures produce an explicit unavailable response.
- Security checks pass before the final demo build.

## Phase 10 - Testing, Demo Preparation, and Polish

**Timing:** Final hours

### Objectives

Prove the complete user journey, stabilize the demo, and communicate both the product value and its limitations honestly.

### Tasks

- Write unit tests for irrigation, spoilage, scheme matching, price comparison, routing, and cache age handling.
- Write integration tests for webhook-to-agent-to-TTS-to-WhatsApp flows.
- Run manual UAT with a team member unfamiliar with the implementation.
- Test Hindi, English, and at least one regional language where supported.
- Test low-confidence speech, missing profile data, upstream API failure, duplicate webhook, and offline/cache scenarios.
- Prepare scripted scenarios for:
  - Irrigation recommendation
  - Spoilage warning
  - Subsidy eligibility
  - Mandi price verification
  - Offline or cached response
  - Adversarial request safely refused
- Measure response latency against the 30-second target.
- Confirm every subsidy and price response exposes source and timestamp.
- Prepare a backup video and local fixtures for connectivity failures.
- Prepare the pitch around energy and water savings, post-harvest loss reduction, accessibility, climate resilience, and verified data.
- Clearly state the software-only scope, IVR limitations, and pre-production security work.
- Review the legal/liability disclaimer and demo language.

### Deliverables

- Passing test suite and CI result
- UAT checklist and results
- Stable demo environment
- Scripted demo scenarios
- Backup video or recorded walkthrough
- Pitch material and known-limitations slide

### Completion checks

- All demo-critical scenarios work end to end.
- No critical security test fails.
- The backup demo is usable without live external APIs.
- The final build has no hardcoded secrets.
- The team can explain every source, fallback, limitation, and security control shown in the demo.

## 4. Shared Technical Contracts

Every agent should accept a normalized request containing:

- Farmer identifier
- Session and message identifier
- Language
- Sanitized query text
- Farmer profile fields required by that agent
- Request timestamp
- Correlation ID

Every agent response should contain:

- Short farmer-facing text
- Optional audio payload or TTS input
- Agent name
- Intent
- Source name and source record/reference
- Source timestamp and response timestamp
- Verification status
- Cache status and cache age, if applicable
- Safe fallback status when the requested answer cannot be verified

## 5. Core Data Models

### Farmer profile

- Phone number identifier
- Preferred language
- Approximate village/district location
- Crop and growth stage
- Land size
- Farmer category, only when required
- Optional pump type and motor size
- Consent status and consent timestamp
- Alert opt-in status
- Created and last-active timestamps

### Scheme record

- Scheme name
- State or national scope
- Eligible crops
- Land-size rules
- Category rules
- Benefit description and amount
- Required documents
- Next action
- Official source URL
- Last-updated date
- Dataset version

### Market price record

- Crop
- Mandi
- Location
- Minimum, maximum, and modal price where available
- Unit
- MSP and MSP date where available
- Source
- Retrieved timestamp
- Cache expiry

### Advisory log

- Correlation ID
- Farmer reference with retention controls
- Intent and agent
- Input confidence
- Response latency
- Source and timestamp
- Verification result
- Cache/fallback status
- Security event flags

## 6. Testing Matrix

| Area | Required checks |
|---|---|
| Router | Five valid intents, unclassified menu, two-failure fallback |
| WhatsApp security | Valid signature, invalid signature, missing signature, replay/idempotency |
| Voice intake | Valid file, unsupported codec, oversized file, corrupt file, low STT confidence |
| Irrigation | Rain expected, no rain, missing weather, cached weather, energy estimate |
| Spoilage | Green, Yellow, Red, missing harvest date, unsupported crop |
| Subsidy | Eligible, ineligible, missing field, stale dataset, fabricated output |
| Market price | Fresh price, cached price, API failure, low offer, source mismatch |
| Privacy | Consent, STOP, profile readback, deletion request, retention cleanup |
| Resilience | API timeout, duplicate message, queue/reconnect, database restore |
| Security | Prompt injection, profile access attempt, rate limit, source-verification bypass |
| UAT | First-time farmer completes the scripted flows using voice |

## 7. Operational Policies to Document

- API keys are stored in a secrets manager and rotated on a defined cadence or after suspected exposure.
- Third-party calls have timeouts, bounded retries, and rate-limit handling.
- Farmer data is not sold or shared with buyers, middlemen, or input companies.
- Voice recordings are transient and deleted after transcription or retry expiry.
- Query logs are retained for 90 days, then anonymized or deleted.
- Inactive profiles are handled after 12 months of no interaction.
- Daily database backups and restore steps are maintained.
- Every subsidy and price response is source-tagged and verified before speech output.
- The service is advisory only and does not guarantee irrigation outcomes, subsidy approval, or sale price.
- Production rollout requires a security review, stronger IVR authentication, formal breach handling, and scalable data-subject access/erasure tooling.

## 8. Final Go/No-Go Checklist

- [ ] WhatsApp webhook signature verification works.
- [ ] Voice input validation and low-confidence fallback work.
- [ ] At least three modules are functional, including irrigation and spoilage.
- [ ] Subsidy and market price figures cannot bypass source verification.
- [ ] Voice responses work in Hindi/English and at least one regional language where supported.
- [ ] Farmer onboarding collects consent and required profile fields.
- [ ] Cached responses identify their age and source.
- [ ] Daily database backup is configured and restore is documented.
- [ ] Rate limiting and audit logging are enabled.
- [ ] Adversarial-input tests pass.
- [ ] Unit, integration, and manual UAT checks pass.
- [ ] Demo scenarios and backup video are ready.
- [ ] Known limitations and post-hackathon roadmap are documented.
