# Agentverse Hosted Deployment Guide: ScholarBot

This guide provides end-to-end instructions for deploying ScholarBot on [Agentverse](https://agentverse.ai) for the **Fetch-A-Thon 3.0** Hackathon.

---

## 1. Architecture & Deployment Options

ScholarBot offers two production-tested deployment paths on Agentverse:

### Option A: Multi-Agent Cloud Mesh (Recommended for "Best Multi-Agent Workflow")
Deploy 4 dedicated hosted agents that communicate across Agentverse:
1. **Coordinator Agent** (`hosted_coordinator.py`): Handles ACP chat, user sessions, Interactive Cards, Payment Protocol, and orchestration.
2. **Scheme Matcher Agent** (`hosted_matcher.py`): Specialist evaluator for 129+ central, state, and CSR scholarships with range-aware matching and explainability.
3. **Document Auditor Agent** (`hosted_auditor.py`): Specialist pre-check engine for income/caste certificate validity, anti-rejection checks, and NPCI verification.
4. **Deadline Tracker Agent** (`hosted_tracker.py`): Specialist tracking closing dates, urgency countdowns, and `.ics` calendars.

### Option B: Standalone Safe-Mode Agent
Deploy 1 single agent (`scholarship_agentverse_hosted.py`):
- 100% self-contained single file with all 129 schemes, full matching engine, document auditor, payment protocol, and Interactive Cards.
- Guaranteed zero external communication failure risk.

---

## 2. Step-by-Step Deployment (Multi-Agent Mesh)

### Step 1: Deploy Specialist Agents First

Log in to [Agentverse](https://agentverse.ai) and create three hosted agents:

#### Agent 1: Scheme Matching Specialist
1. Click **+ New Agent** -> **Blank Agent**.
2. Name it `scholarbot_matcher`.
3. Open the code editor, delete any template code, and paste the entire contents of [`hosted_matcher.py`](file:///c:/Users/NAV%20VARDHAN/Desktop/FEATCXH.AI/LEST%20TRY/hosted_matcher.py).
4. Click **Start** to run the agent.
5. In the top bar, copy the agent address (`agent1q...`). Save this as `SCHEME_AGENT_ADDRESS`.

#### Agent 2: Document Compliance Specialist
1. Click **+ New Agent** -> **Blank Agent**.
2. Name it `scholarbot_auditor`.
3. Open the code editor, delete template code, and paste the entire contents of [`hosted_auditor.py`](file:///c:/Users/NAV%20VARDHAN/Desktop/FEATCXH.AI/LEST%20TRY/hosted_auditor.py).
4. Click **Start**.
5. Copy the agent address (`agent1q...`). Save this as `DOC_AGENT_ADDRESS`.

#### Agent 3: Deadline Tracker Specialist
1. Click **+ New Agent** -> **Blank Agent**.
2. Name it `scholarbot_tracker`.
3. Open the code editor, delete template code, and paste the entire contents of [`hosted_tracker.py`](file:///c:/Users/NAV%20VARDHAN/Desktop/FEATCXH.AI/LEST%20TRY/hosted_tracker.py).
4. Click **Start**.
5. Copy the agent address (`agent1q...`). Save this as `TRACKER_AGENT_ADDRESS`.

---

### Step 2: Deploy the Coordinator Agent

1. Click **+ New Agent** -> **Blank Agent**.
2. Name it `scholarbot_coordinator`.
3. Open the code editor and paste the entire contents of [`hosted_coordinator.py`](file:///c:/Users/NAV%20VARDHAN/Desktop/FEATCXH.AI/LEST%20TRY/hosted_coordinator.py) (or [`scholarship_agentverse_hosted.py`](file:///c:/Users/NAV%20VARDHAN/Desktop/FEATCXH.AI/LEST%20TRY/scholarship_agentverse_hosted.py)).
4. Navigate to **Secrets** (or **Environment Variables**) in the agent settings and configure:
   - `SCHEME_AGENT_ADDRESS`: `<Address copied from Matcher Agent>`
   - `DOC_AGENT_ADDRESS`: `<Address copied from Auditor Agent>`
   - `TRACKER_AGENT_ADDRESS`: `<Address copied from Tracker Agent>`
   - `ASI1_API_KEY`: `<Your ASI1 or OpenAI-compatible API key>` (Optional; regex/deterministic engine operates autonomously if omitted)
   - `PAYMENT_DEMO_MODE`: `true`
5. Click **Start**.
6. Copy the Coordinator agent address (`agent1q...`).

---

### Step 3: Configure Agentverse Profile & Discovery

1. In the Coordinator agent's dashboard, go to the **Profile** / **Deploy** tab:
   - **Name**: `ScholarBot - India Scholarship Advisory & Anti-Rejection Agent`
   - **Short Description**: `Autonomous AI advisor for Indian students. Matches 129+ central, state & CSR scholarships, pre-checks certificates to prevent application rejection, and tracks closing dates with iCal.`
   - **Tags**: `scholarship`, `education`, `India`, `NSP`, `document-check`, `deadlines`, `ASI1`, `hackathon`
   - **Enable Agent Chat Protocol (ACP)**: Ensure the chat manifest toggle is ON (`publish_manifest=True`).
   - **Enable Payment Protocol**: Ensure the payment manifest toggle is ON.

---

### Step 4: Test in ASI:One

1. Open [ASI:One](https://asi1.ai) or the ASI:One chat interface.
2. In the agent search bar, search for your Coordinator Agent address:
   ```text
   agent1q...
   ```
3. Start a chat. You should see:
   - The **Action Hub Interactive Card** with 4 quick options (Find Scholarships, Pre-Check Documents, Deadlines, Concierge Pack).
   - Try typing in Hinglish:
     ```text
     main Rajasthan se hu, OBC, B.Tech, 82% marks, family income 2.5 lakh
     ```
   - Verify the multi-agent attribution line:
     `⚡ Matched in real time by Scheme Matching Agent (agent1q...)`
   - Inspect a scholarship detail card to see verified Apply URLs and real-time portal check.
   - Test document audit: paste a sample income certificate text.

---

### Step 5: Generate Public ASI:One Shared Chat Link

1. After completing a successful demo flow in ASI:One, click the **Share** or **Export Chat** button in ASI:One.
2. Copy the public shared chat URL (e.g., `https://asi1.ai/chat/share/...`).
3. Add this URL to your Devpost hackathon submission and `DEMO_SCRIPT.md`.

---

## 3. Resilience and Fallback Guarantees

- If any specialist agent goes offline or times out (>5s), the Coordinator automatically falls back to its embedded local engine without crashing.
- In-process fallback is visibly noted with `⚠️ Specialist unavailable, used local matching engine.` so judges have full transparency into inter-agent health.
- Sensitive identifiers (Aadhaar, PAN, phone numbers) are masked in memory and logs via `core.privacy.mask_sensitive_identifiers`.
