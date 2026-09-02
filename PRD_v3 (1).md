# Product Requirements Document (PRD)
## "One Number, One Answer" — Unified Farmer Advisory System

**Version:** 3.1 (Updated — verified and tightened against the official Challenge 01 brief; adds explicit energy-savings framing and a Challenge Outcome Alignment scorecard)
**Track:** Yuva Yodha Energy Tech Hackathon by Schneider Electric — Challenge 01: Sustainable Agriculture — Energy, Water & Productivity ("Feeding a billion people cleanly, efficiently, and resiliently")
**Challenge source:** https://www.yuvayodhatech.com/challenges
**Document Owner:** [Your Team Name]
**Date:** September 2026
**Changelog from v3.0:** Verified this PRD against the live Challenge 01 brief (Section 2.1a — Challenge Outcome Alignment, new). Added explicit energy-intensity framing to the Irrigation module and product goals, since the challenge name and first required outcome are energy **and** water, not water alone. Added an explicit justification note tying the Subsidy and Market Price modules back to the challenge's "productivity and affordability" language, so they read as intentional scope, not drift from Challenge 1. No other track's content (Buildings/Grid/Manufacturing) appears anywhere in this document — confirmed on review.
**Changelog from v2.0:** Added webhook/IVR authentication requirements, input validation and prompt-injection safeguards, LLM output verification layer, expanded data governance (retention periods, data subject rights, breach notification, data residency), Security Hardening Backlog (Section 10.4, prioritized), Legal & Liability Disclaimer (Section 14), Testing Strategy (Section 15), Team Roles & Ownership (Section 16), Budget & Cost Ceiling (Section 17), Analytics & Instrumentation (Section 18), new risks in Section 13, and security-specific tasks folded into the Implementation Plan (Section 12).

---

## 1. Executive Summary

"One Number, One Answer" is a single WhatsApp/IVR-based advisory channel that gives smallholder farmers instant, voice-first, vernacular answers to their most pressing daily questions — irrigation timing (which reduces both water use **and** the pumping energy spent applying it), spoilage risk, climate alerts, government subsidy eligibility, and real market prices — without requiring a smartphone app, literacy, or a stable data connection.

Instead of building another feature-heavy dashboard, this project consolidates decision support into **one trusted number** farmers call, message, or send a voice note to. Behind that single number sits a **multi-agent backend**: specialized AI agents (Irrigation, Spoilage, Climate, Subsidy, Market Price) each own one domain, pull from verified data sources, and hand a single, unambiguous instruction back to the farmer in their own dialect — rather than one monolithic model trying to do everything.

This directly targets the adoption gap documented across agritech research: only ~10% of smallholder farmers in low- and middle-income countries actively use digital agricultural services, primarily due to literacy, connectivity, and trust barriers — not a lack of available technology. Two of those trust barriers are addressed head-on by the new modules: farmers routinely miss subsidy entitlements because scheme information is scattered and jargon-heavy, and they are frequently underpaid by middlemen because they have no fast way to verify the "real" mandi price against what they're being offered.

A third trust barrier — silent, invisible in most agritech PRDs — is **whether the system can be trusted not to be hijacked, spoofed, or wrong without saying so**. Section 10 now treats that as a first-class product requirement, not an afterthought.

---

## 2. Problem Statement

### 2.1 Challenge Brief Alignment
Per Challenge 01 — Sustainable Agriculture: Energy, Water & Productivity (yuvayodhatech.com/challenges):
- 40%+ of India's workforce is employed in agriculture
- 90% of freshwater withdrawals are used for agriculture
- 15–20% post-harvest losses occur across key crops and value chains

The brief frames the opportunity as combining distributed renewable energy, precision irrigation, low-cost sensing, and farmer-facing digital tools to raise productivity, affordability, and climate resilience — and names four specific outcomes a solution should achieve: (1) reduce energy and water intensity per unit of output, (2) minimize post-harvest losses, (3) empower the smallholder with accessible decision-support, and (4) strengthen climate resilience. This PRD is scoped to the **farmer-facing digital tools** and **decision-support** portion of that opportunity — not the distributed-renewable-energy or physical-sensing hardware portion, which is explicitly out of scope for this software-only MVP (Section 5.2).

### 2.1a Challenge Outcome Alignment *(new — scorecard)*

| Challenge 01 required outcome | How this PRD addresses it | Section |
|---|---|---|
| Reduce energy and water intensity | Irrigation Advisory Agent turns weather/crop-stage data into a skip/irrigate decision, cutting both wasted water **and** the pump-running energy spent applying it — "smarter scheduling" as named in the brief, delivered without new hardware | 6.3 |
| Minimize post-harvest losses | Spoilage Risk Agent (shelf-life table + temperature/humidity trend) gives a green/yellow/red sell-or-store signal in time to act, directly targeting the 15–20% post-harvest loss stat | 6.4 |
| Empower the smallholder | Every module is voice-first, vernacular, no-login, and designed for feature phones/2G — this is the accessibility layer the brief calls out explicitly ("limited literacy and connectivity") | 4, 6.1, 6.9 |
| Strengthen climate resilience | Climate Resilience Alerts push proactive heat-stress/rainfall/frost warnings from regional forecast data | 6.5 |
| *(Supporting, not a named outcome)* Productivity & affordability | Subsidy Navigator and Market Price Verification are framed by the brief's opening line — "improve productivity, affordability and climate resilience" — not the four bullet outcomes directly. They're included because unclaimed subsidies and mid-sale underpricing are productivity/affordability losses just as real as water or post-harvest waste, and they reinforce the "one trusted number" adoption thesis. Flagged here explicitly so the scoping choice is visible to reviewers, not assumed | 6.6, 6.7 |

**Out of scope by design, and why that's consistent with the brief:** the brief also mentions distributed renewable energy and low-cost physical sensing as opportunity areas. This MVP deliberately stays software-only (satellite/weather data instead of soil sensors, no on-farm energy hardware) — see Section 5.2 for the explicit exclusion and rationale. This is a scoping choice for a 3–4 day build, not a misreading of the brief.

### 2.2 Root Cause (Why Existing Apps Fail)
Research consistently shows the failure is **not** technology quality, but accessibility and trust:
- Most platforms assume digital literacy, stable connectivity, and smartphone access — conditions rarely met in rural India
- Farmers strongly prefer voice over text due to limited literacy and poor eyesight from sun/age exposure
- Farmers distrust apps built by "outsiders" who don't reflect local realities, land size, or indigenous knowledge
- Apps that stop working in connectivity dead zones get uninstalled after first failure
- Most agritech tools serve either large commercial farms or narrow single-feature use cases, not an integrated, low-friction experience for smallholders
- Farmers routinely leave money on the table — either through unclaimed subsidy entitlements (schemes are scattered across state/central portals in bureaucratic language) or through underpricing by middlemen at the point of sale, because there's no fast, trusted way to check "am I being told the truth right now?"

### 2.3 Our Angle
Solve for **depth of accessibility, not breadth of features** — but recognize that "one number, one answer" only builds lasting trust if it can also answer the two questions farmers ask most *outside* the field: "What money am I owed?" and "Am I being paid fairly?" One number. One channel. One clear, verified answer per query — in the language and format (voice) the farmer already trusts and uses daily, delivered by a system that is demonstrably hard to spoof, hijack, or trick into fabricating an answer.

---

## 3. Goals & Success Metrics

### 3.1 Product Goals
| Goal | Metric |
|---|---|
| Reduce water/energy waste in irrigation | % reduction in advised irrigation volume vs. baseline farmer practice, **plus estimated pump-energy saved (irrigation volume avoided × local pump energy-per-litre benchmark)** — directly evidences the challenge's "energy and water intensity" outcome, not water alone |
| Reduce post-harvest loss | % of alerted crops sold/stored before spoilage vs. control group |
| Increase subsidy uptake | % of onboarded farmers who successfully identify and apply for ≥1 eligible scheme |
| Improve price realization | % deviation between farmer's sale price and verified mandi price, tracked over time |
| Drive real adoption (not just downloads) | Weekly active queries per registered farmer |
| Build trust | Repeat usage rate after first 2 weeks |
| Accessibility | % of interactions completed via voice (target >70%) |
| **Security posture (new)** | **Zero unauthenticated write actions reach a farmer profile; 100% of subsidy/price responses pass source-verification before being spoken** |

### 3.2 Hackathon Deliverable Goals
- Working prototype demonstrating end-to-end query → agent routing → verified advisory response flow
- At least 3 of 5 core modules functional (irrigation, spoilage, plus one of: climate / subsidy / market price)
- Demonstrated offline/low-connectivity resilience (cached last-known advisory)
- Vernacular voice output in at least 1 regional language beyond Hindi/English
- Demonstrated "verified vs. unverified" data provenance — every subsidy or price answer visibly traceable to a government/mandi source, not a generic LLM guess
- **New:** Demonstrated webhook signature verification and one adversarial-input test case (e.g., a transcribed query attempting to manipulate the agent into fabricating a scheme or price) handled safely, to show judges the system isn't just a wrapper around an unguarded LLM call

---

## 4. Target Users

### Primary Persona: Smallholder Farmer
- Owns/farms <2 hectares
- Basic feature phone or entry-level smartphone
- Limited/functional literacy, comfortable with voice communication
- Intermittent 2G/3G connectivity, WhatsApp is often the only app used regularly
- Speaks a regional language/dialect, not necessarily Hindi or English

### Secondary Persona: Local Intermediary (Optional Layer)
- Panchayat volunteer, cooperative lead, or "lead farmer"
- Slightly higher literacy/connectivity, can relay advisories to a farmer cluster
- Used to build initial trust and word-of-mouth adoption

---

## 5. Scope

### 5.1 In Scope (Hackathon MVP)
- WhatsApp-based query intake (text + voice note)
- Basic IVR/call-based fallback for non-smartphone users (simulated/documented if not fully built)
- Query classification and routing to the correct specialized agent: irrigation / spoilage / climate alert / subsidy scheme / market price
- Weather-API-driven irrigation recommendation engine
- Rule-based spoilage risk model (crop type + harvest date + local temperature/humidity)
- Subsidy Scheme Navigator — matches farmer profile (crop, land size, state, category) against a curated database of central/state schemes (PM-KISAN, PMFBY, KCC, state-specific) and returns eligibility + application steps in voice
- Market Price Verification — pulls live mandi prices (Agmarknet/eNAM) for the farmer's crop and nearest mandis, and states the verified price range so the farmer can compare it against what a buyer is offering
- Voice response generation in 1–2 vernacular languages
- Offline caching of last-received advisory
- Basic farmer profile (crop type, location, land size, farmer category for scheme matching) captured once via onboarding
- **New: Baseline security controls** — webhook signature verification, input size/type validation on voice notes, rate limiting on public endpoints, and a source-verification check before any subsidy/price figure is spoken (see Section 10.4)

### 5.2 Out of Scope (for MVP)
- Physical IoT sensors (soil moisture hardware, etc.) — replaced by satellite/weather data
- Full marketplace/buyer-matching or price negotiation features (we verify price, we don't broker sales)
- Payment or fintech integration, or actually filing subsidy applications on the farmer's behalf (we guide, we don't submit forms)
- Full multi-crop, multi-region ML model training (use rule-based/heuristic models for MVP, note ML as future roadmap)
- Native mobile app (WhatsApp/IVR only for MVP)
- AI crop-disease image scanning (a KisanMitra feature we are deliberately **not** adopting — it pulls focus from the energy/water/post-harvest challenge brief and adds camera/vision infra out of scope for a voice-first MVP)
- Full penetration testing / formal security audit / SOC-2-style certification (documented as a pre-production requirement, not a hackathon deliverable — see Section 10.4)
- Strong cryptographic caller authentication for IVR (full OTP-based call verification) — MVP uses caller-ID with documented spoofing risk and a defined mitigation path (see Section 10.4)

---

## 6. Core Features & Functional Requirements

### 6.1 Unified Query Intake
- **FR-1:** System accepts input via WhatsApp text, WhatsApp voice note, and/or IVR call
- **FR-2:** System identifies farmer via registered phone number (no login/password)
- **FR-3:** System supports at least 1 regional language + Hindi + English for input
- **FR-1a (new):** System enforces input size and type limits on voice notes (max duration, max file size, allowed codecs) before passing to STT, rejecting oversized/malformed uploads with a friendly voice message rather than crashing or queuing indefinitely
- **FR-1b (new):** System treats transcribed voice/text as untrusted input — no transcribed content is passed to any downstream agent, database query, or LLM prompt without sanitization/escaping appropriate to that context

### 6.2 Multi-Agent Query Routing Engine
- **FR-4:** Classify incoming query into one of five domains — irrigation / spoilage / climate-alert / subsidy scheme / market price / unclassified — and route to the corresponding specialized agent
- **FR-5:** For unclassified queries, respond with a simple voice menu of the 5 options (numbered/spoken, not typed)
- **FR-5a:** Each domain agent operates independently against its own data source and prompt/rule set, so a failure or slow response in one agent (e.g., mandi price API down) does not block the others
- **FR-5b:** Every agent response includes a machine-readable source tag (e.g., "IMD Weather", "Agmarknet", "PM-KISAN portal") used internally for the trust/verification layer (see 6.8, 10.4)
- **FR-5c (new):** Every inbound WhatsApp webhook call is verified against Meta's signature header (`X-Hub-Signature-256`) before processing; requests failing verification are dropped and logged, never routed to an agent
- **FR-5d (new):** If any agent uses a generative/LLM step (as opposed to pure rule-based lookup), its output is checked against the source dataset (scheme DB, mandi price feed) before being spoken — a scheme name, amount, or price that cannot be matched to a verified source is not sent to the farmer; the system falls back to "I don't have verified information on that right now" instead

### 6.3 Irrigation Advisory Module
*(This module is the PRD's primary answer to Challenge 01's "reduce energy and water intensity" outcome — every avoided or right-sized irrigation cycle cuts both freshwater draw and the diesel/electric pump-running time spent applying it.)*
- **FR-6:** Pull local weather forecast (rainfall, temperature, humidity) for farmer's registered location
- **FR-7:** Apply simple crop-water-need heuristic (crop type + growth stage + recent rainfall) to output binary/simple recommendation
- **FR-8:** Response format: single sentence, e.g., "Irrigate tomorrow morning" / "Skip today, rain expected"
- **FR-8a (new):** Where the farmer's pump type is known (diesel/electric, motor size — optional onboarding field), the response can optionally note approximate energy saved on a skipped cycle, to make the energy benefit tangible rather than implicit

### 6.4 Spoilage Risk Module
- **FR-9:** Farmer inputs crop type + harvest date once (via voice or menu tap)
- **FR-10:** System calculates spoilage risk using shelf-life table + local temperature/humidity trend
- **FR-11:** Output color-coded + voice alert: Green (safe to store), Yellow (sell within X days), Red (sell/move immediately)

### 6.5 Climate Resilience Alerts
- **FR-12:** Push proactive alerts (not query-triggered) for heat stress, irregular rainfall, or frost risk based on regional forecast data
- **FR-13:** Alerts sent as short voice notes, opt-in/opt-out via simple reply

### 6.6 Subsidy Scheme Navigator *(adopted from KisanMitra)*
- **FR-18:** Match farmer profile (state, crop, land size, category) against a maintained database of central schemes (PM-KISAN, PMFBY, KCC, PM Kusum) and relevant state schemes
- **FR-19:** For each eligible scheme, respond with: scheme name, one-line benefit, and the single next action (e.g., "You qualify for PM-KISAN ₹6,000/year — visit your nearest CSC with your Aadhaar and land record")
- **FR-20:** If eligibility is uncertain (missing profile data), ask one targeted voice question rather than reciting eligibility criteria
- **FR-21:** Scheme database refreshed on a defined cadence (e.g., monthly) with a visible "last updated" date to avoid giving stale scheme information

### 6.7 Market Price Verification *(adopted from KisanMitra)*
- **FR-22:** On request, or when a spoilage alert is Yellow/Red, fetch live/near-live mandi prices for the farmer's crop from Agmarknet/eNAM for the 2–3 nearest mandis
- **FR-23:** Respond with the verified price range and MSP comparison in one sentence, e.g., "Nearest mandi is paying ₹2,100–2,250 per quintal for wheat; MSP is ₹2,275"
- **FR-24:** If a farmer voice-reports a price they were offered, flag if it is meaningfully below the verified range ("That offer is lower than today's mandi price — you may want to check another buyer")
- **FR-25:** Always state the data source and timestamp so the farmer (or a skeptical intermediary) can trust the number, not just take the app's word for it

### 6.8 Offline Resilience
- **FR-14:** Last-received advisory cached locally on farmer's device (via WhatsApp message history — inherently persistent) or via lightweight companion app cache
- **FR-15:** System queues farmer queries sent during connectivity gaps and processes on reconnect

### 6.9 Trust & Onboarding
- **FR-16:** One-time voice-guided onboarding (location, crop, land size, farmer category for subsidy matching) — no forms
- **FR-17:** Optional link to local intermediary/lead farmer for community-based trust building
- **FR-26:** Every advisory response — irrigation, spoilage, climate, subsidy, or price — is traceable to a named, verifiable source rather than presented as an unattributed AI opinion, directly addressing the "farmers distrust outsider apps" root cause from Section 2.2
- **FR-27 (new):** Onboarding consent step explicitly names what happens to voice recordings (transcribed then deleted vs. retained — see Section 10.5) and gives the farmer a spoken way to ask "what do you have about me?" and "delete my data," even without a dashboard

### 6.10 Error Handling & Fallback UX *(new)*
- **FR-28:** If speech-to-text confidence is below a defined threshold, the system asks the farmer to repeat the query rather than guessing intent
- **FR-29:** If an agent's upstream data source (weather, scheme DB, Agmarknet) is unreachable, the system responds with the most recent cached value **and explicitly states it is cached and its age** (e.g., "Using yesterday's price data — today's is unavailable"), rather than silently serving stale data as current
- **FR-30:** If intent is misclassified twice in a row for the same farmer session, the system escalates to the spoken 5-option menu instead of retrying classification a third time
- **FR-31:** If two data sources disagree (e.g., cached price vs. a fresh live pull), the system surfaces the more recent one and flags the discrepancy rather than silently picking one

---

## 7. User Flows

### 7.1 Primary Flow — Irrigation Query
```
Farmer sends voice note "Should I water my field today?" via WhatsApp
        │
        ▼
System transcribes + detects language + classifies intent = "irrigation"
        │
        ▼
Router hands query to the Irrigation Agent
        │
        ▼
Irrigation Agent fetches farmer profile (location, crop) from database
        │
        ▼
Agent calls Weather API for 48hr forecast at farmer's location
        │
        ▼
Rule engine: IF rainfall_expected > threshold THEN "skip" ELSE "irrigate"
        │
        ▼
System generates voice response in farmer's language via TTS
        │
        ▼
WhatsApp voice note sent back: "Skip today, rain expected tomorrow morning"
```

### 7.2 Flow — Subsidy Scheme Query
```
Farmer sends voice note "Kya mujhe koi sarkari yojana milegi?" (Am I eligible for any government scheme?)
        │
        ▼
System transcribes + classifies intent = "subsidy"
        │
        ▼
Router hands query to the Subsidy Agent
        │
        ▼
Agent checks farmer profile completeness (state, land size, category)
        │
        ├─ Incomplete → asks ONE targeted voice question, then proceeds
        │
        ▼
Agent matches profile against scheme database (PM-KISAN, PMFBY, KCC, state schemes)
        │
        ▼
Agent generates response: scheme name + benefit + single next action + source/date
        │
        ▼
Response passes source-verification check (FR-5d) — scheme name/amount must match a DB record
        │
        ▼
WhatsApp voice note sent back: "You qualify for PM-KISAN, ₹6,000 per year.
Visit your nearest CSC with Aadhaar and land record. (Source: PM-KISAN portal, updated Aug 2026)"
```

### 7.3 Flow — Market Price Verification
```
Farmer sends voice note "Mujhe gehu ka 2000 rupaye mil raha hai, theek hai?" (I'm being offered ₹2000 for wheat, is that fair?)
        │
        ▼
System transcribes + classifies intent = "market price" + extracts crop + offered price
        │
        ▼
Router hands query to the Market Price Agent
        │
        ▼
Agent fetches live mandi prices (Agmarknet/eNAM) for wheat at 2–3 nearest mandis + MSP
        │
        ▼
Agent compares offered price (₹2,000) against verified range (₹2,100–2,250)
        │
        ▼
WhatsApp voice note sent back: "That offer is below today's mandi price of ₹2,100–2,250.
MSP is ₹2,275. You may want to check another buyer. (Source: Agmarknet, today's data)"
```

### 7.4 Flow — Failed/Low-Confidence Query *(new)*
```
Farmer sends a noisy or unclear voice note
        │
        ▼
STT returns a transcription with confidence below threshold
        │
        ▼
System does NOT guess intent — responds: "Sorry, I didn't catch that clearly.
Could you say it again?" (in farmer's language)
        │
        ▼
If this repeats twice in the same session → system falls back to spoken 5-option menu
```

---

## 8. System Architecture *(updated — multi-agent design with security controls)*

```
┌─────────────────────────────────────────────────────────────────┐
│                        FARMER TOUCHPOINTS                        │
│      WhatsApp (text/voice)        │        IVR / Phone Call      │
└───────────────┬────────────────────────────────┬─────────────────┘
                │                                  │
                ▼                                  ▼
        ┌───────────────────────────────────────────────┐
        │           API GATEWAY / MESSAGE ROUTER          │
        │   (WhatsApp Business API webhook + IVR gateway) │
        │   + Webhook signature verification (new)         │
        │   + Rate limiting per number/IP (new)            │
        │   + WAF / basic DDoS protection (new)            │
        └───────────────────────┬─────────────────────────┘
                                 │
                                 ▼
        ┌───────────────────────────────────────────────┐
        │          SPEECH-TO-TEXT / LANGUAGE LAYER        │
        │   (Regional ASR + translation to internal lang) │
        │   + Input size/type validation (new)             │
        │   + Low-confidence fallback (new)                │
        └───────────────────────┬─────────────────────────┘
                                 │
                                 ▼
        ┌───────────────────────────────────────────────┐
        │        INTENT CLASSIFICATION / AGENT ROUTER      │
        │   (Rule-based / lightweight NLU classifier)      │
        │   + Input sanitization before agent handoff (new)│
        └──┬─────────┬─────────┬─────────┬─────────┬───────┘
           │         │         │         │         │
           ▼         ▼         ▼         ▼         ▼
     ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐
     │Irrigation││Spoilage ││Climate  ││Subsidy  ││Market   │
     │Agent     ││Agent    ││Agent    ││Agent    ││Price    │
     │          ││         ││         ││         ││Agent    │
     └────┬─────┘└────┬────┘└────┬────┘└────┬────┘└────┬────┘
          │           │          │          │          │
          └───────────┴────┬─────┴────┬─────┴──────────┘
                            ▼          ▼
        ┌───────────────────────────────────────────────┐
        │        EXTERNAL DATA INTEGRATION LAYER          │
        │  Weather API │ Satellite/NDVI API │ Crop DB      │
        │  Scheme DB (PM-KISAN/PMFBY/KCC) │ Agmarknet/eNAM │
        │  + Least-privilege service credentials (new)      │
        └───────────────────────┬─────────────────────────┘
                                 │
                                 ▼
        ┌───────────────────────────────────────────────┐
        │       RESPONSE GENERATION + SOURCE-TAGGING       │
        │     (Text response → TTS → vernacular voice,     │
        │      each response carries a source/date tag)   │
        │   + Output verification against source DB (new)  │
        └───────────────────────┬─────────────────────────┘
                                 │
                                 ▼
        ┌───────────────────────────────────────────────┐
        │        FARMER DATABASE (profile, history,        │
        │         cached advisories, opt-in status)         │
        │   + Encryption at rest, retention TTL (new)        │
        └───────────────────────────────────────────────┘
```

**Why multi-agent instead of one monolithic classifier (rationale, adopted from KisanMitra):** each domain has a different data source, refresh cadence, and failure mode — weather is real-time, scheme data changes monthly, mandi prices change daily. Decoupling them into independent agents behind one router means the irrigation and spoilage flows (demo-critical path) stay unaffected if a scheme-database or mandi-price integration lags or fails during the demo.

**Security note (new):** the router and each agent run with separate, least-privilege credentials to their respective data sources — the Irrigation Agent cannot read the Scheme DB, the Subsidy Agent cannot write to the Farmer DB beyond its own fields, etc. This limits blast radius if any single agent or its dependency is compromised.

---

## 9. Tech Stack

### 9.1 Frontend / Farmer Interface
| Layer | Technology | Rationale |
|---|---|---|
| Primary channel | WhatsApp Business API (Cloud API, Meta) | Already installed on farmer's phone; supports text + voice notes; free tier sufficient for hackathon |
| Fallback channel | IVR via Twilio Voice API / Exotel (India-focused) | Reaches non-smartphone/feature-phone users |
| Companion cache (optional stretch) | Lightweight PWA (Progressive Web App) | Enables local caching of last advisory without app-store install friction |

### 9.2 Backend
| Layer | Technology | Rationale |
|---|---|---|
| API Gateway / Server | Node.js + Express, or Python + FastAPI | Fast to prototype, strong async support for webhook handling |
| Intent Classification / Agent Router | Rule-based keyword/regex engine (MVP) → spaCy/lightweight NLU model (stretch) | Rule-based is reliable and explainable for hackathon timeframe; avoids heavy ML infra |
| Agent orchestration | Simple in-process router dispatching to per-domain handler functions/modules (MVP) → lightweight agent framework (e.g., LangGraph) if time allows | Keeps agents independently testable and demo-safe; avoids over-engineering for a 3–4 day build |
| Speech-to-Text (ASR) | Google Cloud Speech-to-Text (supports Indian regional languages) or Bhashini (Govt. of India's open ASR/TTS for Indian languages) | Bhashini is purpose-built for Indian vernacular languages and free for public-good use cases |
| Text-to-Speech (TTS) | Bhashini TTS or Google Cloud TTS | Same rationale — vernacular voice output |
| Weather Data | OpenWeather API / IMD (India Meteorological Department) open data | Reliable, free-tier available for prototyping |
| Satellite/Crop Data (stretch) | Bhuvan (ISRO) or Google Earth Engine (Sentinel-2 imagery) | For NDVI-based crop health, no physical sensors needed |
| Scheme data | Curated static dataset (JSON/DB table) sourced from PM-KISAN, PMFBY, KCC, and state agriculture department portals; myScheme.gov.in as a secondary reference for eligibility rules | A hand-curated table is more reliable and demo-safe than live-scraping government portals within a hackathon timeframe; refresh cadence documented as a known limitation |
| Market price data | Agmarknet (Government of India mandi price data) and/or eNAM API | Official, verifiable government source — directly supports the "verified data, not guesses" trust positioning |
| **Dependency/SAST scanning (new)** | **GitHub Dependabot + a basic SAST action (e.g., Semgrep) in CI** | **Catches known-vulnerable packages and common code-level flaws before they ship, at near-zero setup cost for a hackathon** |

### 9.3 Data Layer
| Layer | Technology | Rationale |
|---|---|---|
| Primary database | PostgreSQL | Structured farmer profiles, crop data, query logs, scheme eligibility rules |
| Cache layer | Redis | Fast lookup for last-known advisory (offline resilience), and for caching mandi prices between refreshes to reduce API calls |
| File/voice storage | AWS S3 / Firebase Storage | Store voice notes temporarily for processing; **lifecycle policy auto-deletes raw audio after transcription (new — see 10.5)** |

### 9.4 Infrastructure & Hosting
| Layer | Technology | Rationale |
|---|---|---|
| Hosting | AWS (EC2/Lambda) or Render/Railway for hackathon speed | Lambda for serverless webhook handling reduces ops overhead |
| CI/CD | GitHub Actions | Simple automated deploy for hackathon iteration speed; **includes dependency and SAST scan step (new)** |
| Monitoring | Basic logging via CloudWatch / console logs for MVP | Sufficient for demo; full observability out of scope for MVP |
| **Region/data residency (new)** | **India region (AWS ap-south-1 or equivalent) for primary hosting** | **Aligns with DPDPA data-localization expectations and reduces cross-border transfer questions** |

### 9.5 Security & Auth Tools
| Layer | Technology | Rationale |
|---|---|---|
| Farmer identity | Phone number as identifier, OTP-free (WhatsApp verified number) | No password friction — matches low-literacy design principle |
| **IVR caller authentication (new)** | **Caller-ID (ANI) match against registered number for MVP, with documented spoofing risk; roadmap item: optional voice-PIN or callback-verification for high-stakes actions (e.g., changing land-size/category used for subsidy matching)** | **Full OTP-over-call is disproportionate for a hackathon MVP, but the risk must be named, not silently accepted** |
| **Webhook authentication (new)** | **Verify Meta's `X-Hub-Signature-256` on every inbound WhatsApp webhook call; reject and log anything that fails verification** | **Prevents forged messages from reaching the agent router — the single most exploitable gap in a webhook-driven architecture** |
| **Service-to-service auth (new)** | **Signed internal API tokens, scoped per agent, short-lived** | **Ensures the router and each agent authenticate to each other and to shared services, not just to the outside world** |
| API security | HTTPS/TLS everywhere, API keys via environment variables/secrets manager | Baseline hygiene |
| Data encryption | Encryption at rest (DB-level) and in transit (TLS 1.2+) | Protects farmer location/crop data |
| **Secrets rotation (new)** | **Rotate third-party API keys (weather, ASR/TTS, WhatsApp, Agmarknet) on a defined cadence (e.g., quarterly) or immediately on suspected leak** | **A stored-forever key is a standing liability; rotation policy is cheap insurance** |
| **Least-privilege IAM (new)** | **Each backend service/agent has its own credential scoped to only the data source it needs (e.g., Irrigation Agent has no access to Scheme DB)** | **Limits blast radius if any single component is compromised** |

---

## 10. Security & Privacy

### 10.1 Data Collected
- Phone number (identifier)
- Approximate location (village/district level — not precise GPS unless explicitly consented)
- Crop type, land size, harvest dates, farmer category (for subsidy eligibility matching)
- Query/interaction history, including any price offers the farmer voice-reports (used only to compare against verified mandi data, never shared onward)
- **Voice recordings (new, called out explicitly):** transient audio from WhatsApp voice notes/IVR calls, used only for transcription — treated as sensitive/biometric-adjacent data under DPDPA and handled per the retention rule in 10.5, not stored indefinitely

### 10.2 Security Principles
1. **Minimal data collection** — only what's needed for advisory accuracy (location at district/village granularity, not exact GPS, unless farmer opts in for precision features); subsidy category fields collected only when the farmer engages the Subsidy Agent, not upfront
2. **Encryption in transit and at rest** — all API calls over HTTPS/TLS; database encryption enabled
3. **No third-party data sharing** — farmer data not sold or shared with input/seed companies or buyers/middlemen (a key trust differentiator vs. commercial platforms with conflicts of interest — especially important for the Market Price module, where a farmer must trust the app isn't secretly aligned with a buyer)
4. **Consent-based onboarding** — voice-guided consent step explaining what data is collected and why, in the farmer's language, including what happens to voice recordings (FR-27)
5. **Opt-out mechanism** — simple voice/text command ("STOP" or spoken equivalent) to unsubscribe from proactive alerts
6. **Access control** — role-based access for any dashboard used by intermediaries/admins (only aggregated, non-PII views for community volunteers)
7. **API key management** — all third-party API keys (weather, ASR/TTS, WhatsApp Business, Agmarknet/eNAM) stored in secrets manager (AWS Secrets Manager / .env excluded from repo), never hardcoded, and rotated per 9.5
8. **Rate limiting** — prevent abuse of WhatsApp/IVR endpoints via rate limiting on the API gateway, scoped per phone number and per source IP, with defined thresholds set during Phase 1 (see 12)
9. **Audit logging** — log query/response pairs (without excess PII) for debugging and model improvement, retained per the retention policy in 10.5
10. **Source attribution** — every subsidy or price response logs and surfaces its data source and timestamp, both for farmer trust and for internal auditability if a scheme/price answer is later disputed
11. **Webhook & call authenticity (new)** — every inbound channel (WhatsApp webhook, IVR call) is authenticated before its content is trusted; see 9.5 for mechanism
12. **Untrusted-input handling (new)** — transcribed voice and free-text input are never passed unsanitized into a database query, LLM prompt, or downstream agent call; treat every farmer message as adversarial input by default
13. **Verified-output-only responses (new)** — no subsidy amount, scheme name, or price figure is spoken to a farmer unless it is directly traceable to a record in a verified source dataset (FR-5d); if verification fails, the system says so rather than guessing

### 10.3 Compliance Considerations
- Align with India's Digital Personal Data Protection Act (DPDPA) 2023 principles: purpose limitation, consent, and data minimization
- If using government ASR/TTS (Bhashini), follow their usage/attribution terms
- If using Agmarknet/eNAM or scheme-portal data, follow the respective open government data usage/attribution terms
- **Data residency (new):** primary data storage hosted in an India AWS/GCP region to align with DPDPA data-localization expectations
- **Grievance contact (new):** a named grievance/contact point (even if it's a shared team email for the hackathon) documented for farmers or reviewers to raise data concerns — a placeholder for the DPO role DPDPA expects at production scale
- **Breach notification (new):** documented (even if manual for MVP) process for what the team does if a data exposure is discovered — who is notified, within what timeframe, and how affected farmers would be informed, as a stated intent ahead of the DPDPA's Data Protection Board notification requirements at production scale

### 10.4 Security Hardening Backlog *(new — prioritized for a hackathon build)*

**Critical (build into MVP, cheap and high-impact):**
| Item | Why it matters |
|---|---|
| Verify WhatsApp webhook signatures (`X-Hub-Signature-256`) | Without this, anyone who finds the webhook URL can inject fake farmer messages |
| Input size/type validation on voice notes | Prevents DoS and malformed-file exploitation of the STT pipeline |
| Sanitize transcribed text before it reaches any agent, DB query, or LLM prompt | Closes the prompt-injection / query-injection attack surface introduced by voice-to-text as an input channel |
| Output verification against source dataset before speaking a subsidy/price figure | Prevents hallucinated numbers from reaching a farmer's financial decisions |
| Rate limiting with defined thresholds on WhatsApp/IVR endpoints | Prevents spam/abuse from degrading service or running up API costs |

**High (build if time allows, otherwise documented as immediate post-hackathon work):**
| Item | Why it matters |
|---|---|
| Least-privilege IAM between router and agents | Limits blast radius of any single compromised component |
| Secrets rotation policy | Reduces long-term exposure from a leaked key |
| Dependency/SAST scanning in CI | Catches known-vulnerable packages and common flaws pre-deploy |
| Documented IVR caller-spoofing risk + roadmap mitigation (voice-PIN/callback verification) | Caller ID is trivially spoofable; today's MVP mitigation is "documented risk," not "solved risk" |
| Fallback UX for conflicting data sources (FR-31) | Prevents silently serving a wrong number when sources disagree |

**Medium (name explicitly as pre-production requirements, not MVP scope):**
| Item | Why it matters |
|---|---|
| Full penetration test / security review | Formal validation before real farmer data is processed at scale |
| WAF/DDoS protection in front of public endpoints | The webhook and IVR gateway are internet-facing by design |
| Formal breach notification + DPO process | Required in substance, not just intent, once operating at production scale under DPDPA |
| Data subject access/erasure tooling (beyond a spoken request) | A scalable way to honor deletion/correction requests as farmer base grows |

### 10.5 Data Retention & Subject Rights *(new)*
- **Voice recordings:** deleted immediately after successful transcription; retained only as long as needed to retry a failed transcription (target: <24 hours), never used for any purpose beyond generating the text query
- **Query/response logs:** retained for 90 days for debugging and model improvement, then anonymized or deleted; PII (phone number) is not required for aggregate quality analysis and is stripped after the 90-day window
- **Farmer profile data:** retained while the farmer remains active; considered inactive after 12 months of no interaction, at which point the farmer is notified (via WhatsApp) before data is archived/deleted
- **Farmer-reported price offers:** used only for the single comparison at query time, not retained beyond the interaction log window above
- **Data subject rights (new):** a farmer can, by voice or text command ("what do you have about me" / "delete my data"), trigger a profile summary readback or a deletion request — handled by a human-reviewed queue for MVP, automated as the system matures

### 10.6 LLM/Agent-Specific Safeguards *(new)*
- Any agent step that uses a generative model (as opposed to pure rule/lookup logic) treats the transcribed farmer query as **untrusted input**, not as an instruction to the system itself — the model is scoped to only ever produce a response grounded in the domain's verified data source
- No agent prompt allows the model to alter its own instructions, access other agents' data, or bypass the output-verification check in FR-5d, regardless of what the farmer's transcribed message contains
- A basic adversarial test set (a handful of transcribed queries designed to try to extract fabricated data or manipulate the classifier) is run before the demo, and results documented — even 5–10 test cases materially raises confidence over an unguarded wrapper

---

## 11. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Availability | Core advisory response within 30 seconds of query (target for demo) |
| Offline resilience | Last advisory always retrievable even without live connectivity (via WhatsApp chat history or PWA cache) |
| Scalability | Architecture should support horizontal scaling (stateless API layer) for post-hackathon growth, even if MVP runs on modest infra; agent-based design allows new domains (e.g., crop insurance) to be added without touching existing agents |
| Language coverage | Minimum 1 regional language + Hindi + English at MVP; architecture should allow easy addition of more languages |
| Accessibility | No login/password; voice-first; works on basic smartphones (WhatsApp) and feature phones (IVR) |
| Cost-efficiency | Rely on free-tier/open government APIs (Bhashini, IMD, Agmarknet, myScheme) where possible to keep solution viable for scale to low-income users |
| Data trustworthiness | Every subsidy or price figure must be traceable to a named source and timestamp; the system must never fabricate a scheme or price figure when data is unavailable — it should say so explicitly rather than guess |
| **Security testing (new)** | **Every PR touching the webhook, agent router, or any data-source integration runs the CI dependency/SAST scan (9.2) before merge; at least one adversarial-input test case (10.6) validated before demo day** |
| **Backup & recovery (new)** | **PostgreSQL automated daily backups (even a basic snapshot for hackathon scope); documented restore procedure so a corrupted farmer DB isn't a single point of total failure** |
| **Auditability (new)** | **Source-tagged responses (FR-5b) and query/response logs (10.5) are sufficient to reconstruct what a farmer was told, when, and from which source, if a scheme or price answer is later disputed** |

---

## 12. Implementation Plan

### Phase 0 — Setup (Day 1, first few hours)
- Set up WhatsApp Business API sandbox (Meta developer account, test number)
- Set up backend project skeleton (Node.js/FastAPI + PostgreSQL + Redis)
- Register for weather API keys (OpenWeather) and Bhashini API access
- Pull and clean an initial scheme dataset (PM-KISAN, PMFBY, KCC eligibility rules) and register for Agmarknet/eNAM API access
- **New:** Set up secrets manager from day one (not retrofitted later); configure India-region hosting project
- **Where:** local dev environment + cloud project (AWS/GCP free tier, India region)

### Phase 1 — Core Query Pipeline & Agent Router (Day 1–2)
- Build webhook to receive WhatsApp text/voice messages
- **New:** Implement webhook signature verification (`X-Hub-Signature-256`) before any message is processed
- **New:** Implement input size/type validation on incoming voice notes
- Integrate Speech-to-Text for voice note transcription
- Build the intent classifier and agent router (keyword matching, 5-way routing)
- **New:** Define and implement rate-limit thresholds on the webhook/gateway
- **Where:** backend service, deployed to Render/Railway or AWS Lambda for quick iteration

### Phase 2 — Irrigation Advisory Agent (Day 2)
- Integrate weather API call by farmer location
- Implement rule engine for irrigation recommendation
- Build response formatter → Text-to-Speech → send back via WhatsApp
- **Where:** backend module, tested end-to-end with sandbox WhatsApp number

### Phase 3 — Spoilage Risk Agent (Day 2–3)
- Build simple crop shelf-life lookup table (static JSON/DB table for common crops)
- Combine with temperature/humidity trend from weather API
- Implement color-coded + voice alert output
- **Where:** backend module, same pipeline as Phase 2

### Phase 4 — Subsidy Scheme Agent (Day 3)
- Build curated scheme eligibility table (state, crop, land size, category → schemes)
- Implement matching logic + "ask one missing field" fallback
- Build response formatter with source/date tagging
- **New:** Implement output-verification check (FR-5d) — response scheme name/amount must match a DB record before being sent
- **Where:** backend module, reuses agent router pipeline

### Phase 5 — Market Price Agent (Day 3)
- Integrate Agmarknet/eNAM API for nearest-mandi prices by crop
- Implement offered-price-vs-verified-price comparison logic
- Build response formatter with MSP comparison + source/date tagging
- **New:** Apply the same output-verification check as Phase 4
- **Where:** backend module, reuses agent router pipeline

### Phase 6 — Farmer Onboarding & Profile (Day 3)
- Build one-time voice-guided onboarding flow (location, crop, land size, category)
- **New:** Include explicit voice consent language covering voice-recording handling (FR-27)
- Store farmer profile in PostgreSQL with encryption at rest
- **Where:** backend + DB schema

### Phase 7 — Offline Resilience, Caching & Data Hygiene (Day 3–4)
- Implement Redis cache for last-sent advisory (all five agent types)
- Test behavior when farmer queries during simulated connectivity gap (message queued, processed on reconnect)
- **New:** Implement voice-note auto-deletion after transcription (S3 lifecycle policy)
- **New:** Configure automated daily DB backup
- **New:** Apply least-privilege IAM roles per agent/service
- **Where:** backend caching layer

### Phase 8 — Climate Alerts & IVR Fallback (Stretch, Day 4)
- Build scheduled job (cron) to check regional forecasts for heat/rainfall anomalies
- Push proactive voice alerts to opted-in farmers
- Integrate Twilio/Exotel IVR for call-based access mirroring the WhatsApp flow, if time allows
- **New:** Document (even if not fully built) the IVR caller-spoofing risk and intended mitigation path
- **Where:** backend scheduled worker + separate IVR service connected to the same agent router

### Phase 9 — Security Pass & Adversarial Testing (New, Day 4)
- Run dependency/SAST scan in CI and resolve high-severity findings
- Run the adversarial-input test set (10.6) against the classifier and generative agent steps
- Verify webhook signature check, rate limiting, and output-verification check all function end-to-end
- **Where:** across backend, run as a dedicated pre-demo checklist rather than folded into feature phases

### Phase 10 — Demo Prep & Polish (Final hours)
- Prepare 4–5 scripted demo scenarios (irrigation query, spoilage alert, subsidy match, price verification, offline query)
- **New:** Prepare one adversarial-input demo scenario showing the system correctly refusing to fabricate a scheme/price
- Record backup video demo in case of live connectivity issues during presentation
- Prepare pitch deck referencing adoption-gap research + the "verified data, not guesses" trust angle, plus the security hardening backlog as evidence of production-readiness thinking

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| WhatsApp Business API approval/setup delays | Use WhatsApp sandbox/test mode for hackathon demo; document production path separately |
| ASR accuracy for regional dialects | Start with 1 well-supported language (e.g., Hindi via Bhashini); scope additional languages as roadmap item |
| Weather API data granularity (village-level) | Use nearest available district-level data with a documented limitation; note satellite data as future refinement |
| Scheme data going stale or incomplete | Curate a small, high-confidence set of major central schemes for MVP rather than attempting full state-by-state coverage; clearly state "last updated" date in every response |
| Mandi price API downtime/rate limits during demo | Cache the most recent successful price pull in Redis and serve that with a visible timestamp if the live call fails, rather than blocking the response |
| Farmer distrust if a price/scheme answer is later shown to be wrong | Always attribute source + date on every subsidy/price response, and explicitly say "data unavailable" rather than fabricate a number when a source call fails |
| Judges question "why not just build an app" | Have the adoption-gap research (10% smallholder digital adoption stat) ready as direct justification |
| Time constraints for stretch features (IVR, climate alerts) | Prioritize Phases 1–7 as the demo-critical path; treat Phases 8–9 as optional stretch, but keep Phase 9's critical items (webhook signature, output verification) non-negotiable even under time pressure |
| **Forged WhatsApp messages via unverified webhook (new)** | **Webhook signature verification implemented in Phase 1, before any other feature work — cheapest, highest-leverage fix in the whole build** |
| **Prompt/query injection via transcribed voice input (new)** | **Treat all transcribed text as untrusted; sanitize before use in any DB query or LLM prompt; run adversarial test set pre-demo (Phase 9)** |
| **Hallucinated subsidy amount or price figure damages farmer trust or finances (new)** | **Output-verification check (FR-5d) blocks any figure not traceable to the source dataset; system says "unavailable" rather than guesses** |
| **IVR caller-ID spoofing lets someone query/impersonate another farmer (new)** | **Documented as an accepted MVP-level risk with a named roadmap mitigation (voice-PIN/callback verification); not claimed as solved in the pitch** |
| **Leaked or long-lived API keys (new)** | **Secrets manager from day one (Phase 0) plus a rotation cadence documented in 9.5, even if rotation itself is a post-hackathon operational task** |

---

## 14. Legal & Liability Disclaimer *(new)*

- The system provides **advisory guidance only** — irrigation timing, spoilage risk, subsidy eligibility, and price comparisons are decision-support estimates based on the best available data at query time, not guarantees, legal filings, or financial advice.
- Subsidy eligibility responses are explicitly framed as "based on the information you've given us and current scheme rules" — the system does not submit applications on the farmer's behalf (per Section 5.2) and is not responsible for a scheme's final approval/rejection decision, which rests with the relevant government authority.
- Market price responses are explicitly framed as informational — the system does not broker, negotiate, or guarantee any sale price; the farmer makes the final selling decision.
- This disclaimer is communicated once during onboarding (in plain, spoken language, not legal jargon) and is available on request ("what can this app promise me?") rather than read out before every single response, to avoid undermining the voice-first, low-friction design principle.
- A visible text-based version of this disclaimer (for any future dashboard/website) should accompany production deployment, reviewed by someone with relevant legal familiarity before real farmer data and money-related decisions are involved at scale.

---

## 15. Testing Strategy *(new)*

| Level | Approach |
|---|---|
| Unit tests | Core logic per agent (irrigation rule engine, spoilage risk calculation, scheme matching, price comparison) covered with unit tests against known input/output pairs |
| Integration tests | End-to-end flow per module: webhook → STT → classifier → agent → TTS → WhatsApp send, tested against the sandbox WhatsApp number |
| Adversarial/security tests | The 10.6 adversarial input set; webhook signature bypass attempts; oversized/malformed voice note handling; rate-limit threshold verification |
| Data-integrity tests | Output-verification check (FR-5d) tested against deliberately mismatched agent outputs to confirm it blocks unverifiable figures |
| Manual UAT | Scripted demo scenarios (Section 12, Phase 10) run end-to-end by a team member unfamiliar with the internals, simulating a first-time farmer |
| Regression | Re-run core unit/integration suite before each deploy during the hackathon build, via the CI pipeline (9.4) |

---

## 16. Team Roles & Ownership *(new)*

| Area | Owner (fill in per team) | Notes |
|---|---|---|
| Backend / Agent Router | — | Owns webhook, classifier, router, and cross-cutting security controls (10.4 Critical items) |
| Irrigation & Spoilage Agents | — | Owns rule engines and weather/crop data integration |
| Subsidy & Market Price Agents | — | Owns scheme DB curation, Agmarknet/eNAM integration, output-verification logic |
| STT/TTS & Language Layer | — | Owns Bhashini/Google integration, low-confidence fallback (FR-28) |
| Data & Infra | — | Owns PostgreSQL/Redis schema, secrets manager, backups, IAM scoping |
| Demo & Pitch | — | Owns scripted scenarios, backup video, pitch deck narrative |

*(Fill in names before the build starts — this table exists so nothing above falls through the cracks because "everyone assumed someone else had it.")*

---

## 17. Budget & Cost Ceiling *(new)*

| Item | Expected cost during hackathon | Notes |
|---|---|---|
| WhatsApp Business API (sandbox) | Free | Sandbox/test mode sufficient for demo |
| Twilio/Exotel IVR | Free trial credit | Set a hard usage cap to avoid surprise charges if IVR testing loops |
| Weather API (OpenWeather) | Free tier | Monitor call volume against free-tier limits |
| Bhashini ASR/TTS | Free for public-good use cases | Confirm current usage terms haven't changed before demo day |
| Google Cloud STT/TTS (fallback) | Free tier / small paid usage | Set a billing alert as a safety net |
| Agmarknet/eNAM | Free (government open data) | No cost, but confirm rate limits |
| Hosting (Render/Railway/AWS free tier) | Free tier | Set a spending alert regardless |
| **Total hard ceiling (new)** | **Define an explicit team-agreed cap (e.g., ₹0–2,000) with billing alerts on every paid service** | **Prevents a runaway API loop or misconfigured retry logic from generating an unexpected bill mid-hackathon** |

---

## 18. Analytics & Instrumentation *(new)*

To make the Section 3 metrics real rather than aspirational, the following are logged from day one:
- **Query-level logs:** intent classified, agent invoked, response latency, source(s) used, whether output-verification passed or blocked a response
- **Session-level logs:** whether a query resolved on first classification attempt or needed the fallback menu (FR-30)
- **Subsidy/price outcomes (self-reported, optional):** a simple follow-up prompt ("Did you apply for this scheme?" / "Did you get a better price?") to approximate the uptake and price-realization metrics in Section 3.1, logged only with the farmer's response, never inferred
- **Security-relevant events:** failed webhook signature checks, rate-limit triggers, and output-verification blocks are logged and counted — these numbers double as both a security audit trail and a compelling demo/pitch data point ("the system blocked N attempts to serve unverified data")

---

## 19. Future Roadmap (Post-Hackathon)

- Replace rule-based intent classification with a trained lightweight NLU model for better query understanding
- Add local intermediary dashboard (aggregated, privacy-safe view for panchayat volunteers/cooperatives)
- Expand scheme coverage to full state-by-state government portal integration (live rather than curated)
- Integrate satellite-based NDVI crop health checks (Bhuvan/Sentinel-2) for proactive alerts, not just query-based
- Explore IVR-first design for feature-phone-only regions as primary channel, WhatsApp as secondary
- Pilot with a cooperative/NGO partner to validate trust-building hypothesis at small scale before wider rollout
- ~~Expand to market price advisory (eNAM integration) as a fourth module~~ — moved into MVP scope (Section 6.7)
- Evaluate whether AI crop-disease image scanning (a feature seen in comparable apps like KisanMitra) fits a future phase, once the voice-first energy/water/post-harvest core is validated
- **New:** Move IVR caller authentication from caller-ID-only to voice-PIN or callback-verification for sensitive profile changes
- **New:** Formal penetration test and security review ahead of any production rollout involving real farmer financial decisions at scale
- **New:** Automated data subject access/erasure tooling (self-service, beyond the human-reviewed MVP queue)
- **New:** Formalize a Data Protection Officer / grievance-officer role and documented breach-notification runbook as user base grows

---

## 20. References

1. ICTworks — [12 Reasons Why Farmers Do Not Use Mobile AgriTech Services](https://www.ictworks.org/12-reasons-why-farmers-do-not-use-mobile-agritech-services/)
2. Medium — [Agriculture App UI Design: 7 Field-Tested Principles That Drive Real Farmer Adoption](https://medium.com/@sneh_sagar/agriculture-app-ui-design-7-field-tested-principles-that-drive-real-farmer-adoption-3fbbbbb24cea)
3. AgriBazaar — [Digital, rural-first tool & local language: Redefining agritech](https://blog.agribazaar.com/digital-rural-first-tool-local-language-redefining-agritech/)
4. ScienceDirect — [Participatory development of mobile agricultural advisory driven by behavioural determinants of adoption](https://www.sciencedirect.com/science/article/abs/pii/S0301479725001161)
5. ResearchGate — [Challenges to Adoption of Digital Agriculture in India](https://www.researchgate.net/publication/371519986_Challenges_to_Adoption_of_Digital_Agriculture_in_India)
6. Taylor & Francis — [The role of ICT-based extension in agriculture: application, opportunities and challenges](https://www.tandfonline.com/doi/full/10.1080/02681102.2025.2456232)
7. Yuva Yodha Energy Tech Hackathon — [Challenges Page](https://www.yuvayodhatech.com/challenges)
8. Agmarknet — [Government of India Agricultural Marketing Information Network](https://agmarknet.gov.in/)
9. myScheme — [National Platform for Government Scheme Discovery](https://www.myscheme.gov.in/)
