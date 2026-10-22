# 🎬 ScholarBot 4-Minute Hackathon Demo Script
> **Fetch-A-Thon 3.0: ASI:One Agent Challenge – From Intent to Action**  
> Use this exact script to record your winning 3-5 minute demo video.

---

## ⏱️ Video Timeline Overview

| Timestamp | Phase | What to Show |
| :--- | :--- | :--- |
| **0:00 - 0:35** | **The Hook & Problem** | Intro: 40M Indian students need aid, 40% rejected due to avoidable doc errors. 129 real schemes across all 28 states & 8 UTs. |
| **0:35 - 1:15** | **Natural Hinglish Intent -> Structured Cards** | Free-text message ("main Rajasthan se hu...") -> ASI1 extraction -> Review Screen -> Carousel results. |
| **1:15 - 2:00** | **Multi-Agent Message Flow & Provability** | Visible attribution line: *"Matched by Scheme Matching Agent (agent1q...)"* + Top Picks & Stacking Benefit. |
| **2:00 - 2:50** | **Anti-Rejection Document Audit** | Paste stale certificate -> Engine catches 6-month rule -> Actionable fix with Privacy Aadhaar Masking. |
| **2:50 - 3:30** | **Deadline Alarms & ICS Calendar** | Countdown timers -> Downloadable RFC-5545 `.ics` with 7, 3, 1 day reminders + proactive alerts. |
| **3:30 - 4:10** | **Verified Apply Links & Live Portal Verifier** | Tap detail card -> Official verified Apply Link (`apply_url`) + "Checked today / Portal Active" status. |
| **4:10 - 4:45** | **Payment Protocol (Concierge Pack)** | RequestPayment -> CommitPayment -> Unlocks Application Pack with Custom ASI1 SOP & portal roadmap. |

---

## 📝 Step-by-Step Recording Instructions

### Scene 1: The Problem & Opening Hook (0:00 - 0:35)
* **What to say:**  
  *"Every year, millions of Indian college students miss out on hundreds of crores in scholarship funds. Not because they weren't eligible, but because schemes are scattered across dozens of central and state portals, and over 40% of applications are rejected due to unlinked NPCI bank accounts or stale certificates. We built ScholarBot: an autonomous multi-agent system on Fetch.ai and ASI:One that guides students from natural intent to confident action across 129 cataloged central, state, and foundation schemes."*
* **What to type in ASI:One:**
  ```text
  Hi, can you help me find scholarships?
  ```
* **What appears on screen:**  
  ScholarBot responds instantly with the **Action Hub Carousel** with custom 512x512 high-res cards showing options for Matching, Document Audit, Deadlines, and Concierge Pack.

---

### Scene 2: Free-Text Hinglish Profile Extraction (0:35 - 1:15)
* **What to say:**  
  *"Instead of forcing students through tedious multi-page forms, ScholarBot uses the ASI1 LLM as its core brain to extract structured profile criteria from natural Hindi, Hinglish, or English messages."*
* **What to type in ASI:One:**
  ```text
  main Rajasthan se hu, OBC category, doing B.Tech 2nd year, family income 2.5 lakh, 82% marks, my name is Priyanshu
  ```
* **What appears on screen:**  
  ScholarBot displays the **Profile Review Screen Card** summarizing:  
  `Priyanshu | Rajasthan | B.Tech | OBC | ₹2,50,000 | 82.0%`.
* **Action:** Click **"✅ Confirm & Find Scholarships"**.

---

### Scene 3: Multi-Agent Collaboration & Top Picks (1:15 - 2:00)
* **What to say:**  
  *"When the student confirms, the Coordinator agent doesn't do a simple database lookup. It dispatches a typed SchemeMatchRequest to our specialized SchemeMatchingAgent. Notice the live attribution right in the chat showing the specialist agent's cryptographic address."*
* **What to show on screen:**  
  1. The response clearly states:
     ```text
     🤖 Matched by Scheme Matching Agent (agent1qvkqmzdv8m9n63m23zv76p7kx5uky5s8fkvzfvd5qf5ug7ptx0vnyjmxjj2)
     💰 Stacking Benefit: Up to ₹70,000/year combinable aid across state & merit schemes!
     ```
  2. Switch window briefly to your running terminal (`python run_all.py`):
     ```
     INFO: [Coordinator] Orchestrating scheme match for Priyanshu...
     INFO: [Matcher] Received match request for Priyanshu from Coordinator
     INFO: [Matcher] Range evaluation: 8 eligible schemes, 2 close misses.
     ```
* **Switch back to ASI:One:**  
  The **Scholarships Carousel** renders top-ranked scholarships with type-specific badges:
  1. *Rajasthan Post-Matric Uttarmatric (State · Full Fee Waiver + Maintenance)*
  2. *Reliance Foundation UG Scholarship (CSR · Up to ₹2,00,000)*
  3. *Tata Trusts Higher Education Grant (CSR · Need-Based Tuition)*

---

### Scene 4: Real Anti-Rejection Document Audit (2:00 - 2:50)
* **What to say:**  
  *"Here is our anti-rejection innovation: the DocComplianceAgent. Let's see what happens if a student uploads an outdated income certificate dated August 2025."*
* **What to type in ASI:One:**
  ```text
  Income Certificate
  Applicant: Priyanshu Verma
  Aadhaar Number: 4892 1234 5678
  Total Annual Income: Rs 250000
  Date of Issue: 10/08/2025
  Tehsildar Signed, Rajasthan
  ```
* **What appears on screen:**  
  ScholarBot renders the **Document Pre-Check Audit Card**:
  - **Status:** `WARN (Score: 65/100)`
  - **Flagged Problem:** Certificate was issued over 14 months ago; Rajasthan SJMS mandates Form I/K/M issued within the last 6 months.
  - **Actionable Remedy:** *"Apply for a fresh certificate via local E-Mitra kiosk or Tehsildar before portal cutoff."*
  - **Privacy:** Notice the Aadhaar number is strictly masked as `XXXX-XXXX-5678` in the audit card.

---

### Scene 5: Deadlines & Downloadable ICS Calendar (2:50 - 3:30)
* **What to say:**  
  *"Missed deadlines cause thousands of students to lose aid every year. Our DeadlineTrackerAgent computes dynamic countdowns against real 2026 cutoffs and generates standard calendar events."*
* **What to type in ASI:One:**
  ```text
  Show me closing deadlines and calendar
  ```
* **What appears on screen:**  
  The **Deadlines & Calendar Card** appears:
  - Reliance Foundation: *Closing in 10 Days (Urgent)*
  - Rajasthan Post-Matric: *55 Days Remaining*
  - AICTE Pragati: *71 Days Remaining*
  - Includes a 1-click downloadable RFC-5545 `.ics` file containing pre-configured alarms for 7 days, 3 days, and 1 day before cutoff.

---

### Scene 6: Verified Apply Links & Live Portal Verifier (3:30 - 4:00)
* **What to say:**  
  *"Unlike chatbots that provide vague advice, ScholarBot gives students direct, verified Apply Links and runs real-time gateway checks against official portals."*
* **What to do:**
  Tap on the **"View Details"** action for *Rajasthan Post-Matric*.
* **What appears on screen:**  
  The **Detail Guide Card** shows:
  - **Apply Link:** `https://sjmsnew.rajasthan.gov.in/`
  - **Live Verification Status:** `Gateway Reachable (Checked today)`
  - **Portal Steps Hint:** *"Register on SSO Rajasthan, select SJMS portal, and link Bhamashah/Jan Aadhaar."*
  - Follow-up message provides the clickable link directly in chat so the student can apply on the official government portal immediately.

---

### Scene 7: Fetch.ai Payment Protocol Concierge Pack (4:00 - 4:45)
* **What to say:**  
  *"While scholarship search and document checklists are 100% free, we monetized an Application Concierge Pack using the official Fetch.ai Payment Protocol."*
* **What to type in ASI:One:**
  ```text
  I want the Application Concierge Pack
  ```
* **What appears on screen:**  
  ScholarBot issues an official `RequestPayment` (0.01 USDC / 0.05 FET) with payment reference and metadata clearly marked as `DEMO / TESTNET`.
* **Action:**
  The student's uAgents wallet sends `CommitPayment` with a transaction hash (e.g. `demo-tx-priyanshu-2026`).
* **What appears on screen:**  
  The Coordinator verifies the payment on testnet, replies with `CompletePayment`, and delivers:
  - Complete pre-filled student dossier.
  - Step-by-step portal submission workflow with direct official application URL.
  - **Personalized 250-word Statement of Purpose (SOP / Application Essay)** drafted by the ASI1 LLM.
  - Copyable `.ics` calendar alarms.
* **Closing:**  
  *"From natural intent to decisive action: ScholarBot helps every Indian student claim the education funding they deserve. Thank you!"*
