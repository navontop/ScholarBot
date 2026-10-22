# 🎬 ScholarBot 4-Minute Hackathon Demo Script
> **Fetch-A-Thon 3.0: ASI:One Agent Challenge – From Intent to Action**  
> Use this exact script to record your winning 3-5 minute demo video.

---

## ⏱️ Video Timeline Overview

| Timestamp | Phase | What to Show |
| :--- | :--- | :--- |
| **0:00 - 0:35** | **The Hook & Problem** | Intro: 40M Indian students need aid, 40% rejected due to avoidable doc errors. |
| **0:35 - 1:15** | **Natural Intent -> Structured Cards** | Free-text message -> ASI1 extraction -> Review Screen -> Carousel results. |
| **1:15 - 2:00** | **Multi-Agent Message Flow** | Show terminal logs: Coordinator orchestrating Scheme Matching & Compliance agents. |
| **2:00 - 2:50** | **Anti-Rejection Document Audit** | Paste stale certificate -> Engine catches 6-month rule -> Actionable fix. |
| **2:50 - 3:30** | **Deadline Alarms & ICS Calendar** | Countdown timers -> Downloadable RFC-5545 `.ics` with 7, 3, 1 day reminders. |
| **3:30 - 4:10** | **Payment Protocol (Concierge Pack)** | RequestPayment -> CommitPayment -> Unlocks Application Pack with Custom SOP. |
| **4:10 - 4:40** | **Personal AI & "What-If" Simulation** | Session memory across chats + "What-if income was ₹4.5L" scenario. |

---

## 📝 Step-by-Step Recording Instructions

### Scene 1: The Problem & Opening Hook (0:00 - 0:35)
* **What to say:**  
  *"Every year, millions of Indian college students miss out on hundreds of crores in scholarship funds. Not because they weren't eligible, but because schemes are scattered across dozens of portals, and over 40% of applications are rejected due to unlinked NPCI bank accounts or stale certificates. We built ScholarBot: an autonomous multi-agent system on Fetch.ai and ASI:One that guides students from natural intent to confident action."*
* **What to type in ASI:One:**
  ```text
  Hi, can you help me find scholarships?
  ```
* **What appears on screen:**  
  ScholarBot responds instantly with the **Action Hub Carousel** showing options for Matching, Document Audit, Deadlines, and Concierge Pack.

---

### Scene 2: Free-Text Profile Extraction (0:35 - 1:15)
* **What to say:**  
  *"Instead of forcing students through tedious multi-page forms, ScholarBot uses the ASI1 LLM to extract a complete profile from natural language, including regional aliases and income figures."*
* **What to type in ASI:One:**
  ```text
  I'm from Rajasthan, OBC, doing B.Tech, family income 2.2 lakh, 82% marks, my name is Priyanshu
  ```
* **What appears on screen:**  
  ScholarBot displays the **Profile Review Screen Card** summarizing:  
  `Priyanshu | Rajasthan | B.Tech | OBC | ₹2,20,000 | 82.0%`.
* **Action:** Click **"✅ Confirm & Find Scholarships"**.

---

### Scene 3: Multi-Agent Collaboration in Terminal (1:15 - 2:00)
* **What to say:**  
  *"When the student confirms, the Coordinator agent doesn't do a naive database lookup. It dispatches a typed SchemeMatchRequest to our specialized SchemeMatchingAgent running on port 8002."*
* **What to show on screen:**  
  Switch window briefly to your running terminal (`python run_all.py`):
  ```
  INFO: [Coordinator] Orchestrating scheme match for Priyanshu...
  INFO: [Matcher] Received match request for Priyanshu from Coordinator
  INFO: [Matcher] Evaluation complete: 7 eligible schemes, 2 close misses.
  ```
* **Switch back to ASI:One:**  
  The **Scholarships Carousel** renders 7 matching scholarships, sorted by match percentage:
  1. *Reliance Foundation UG Scholarship (Eligible · Ends Oct 31)*
  2. *Rajasthan Post-Matric Uttarmatric (Eligible · Ends Dec 15)*
  3. *Tata Trusts Higher Education Grant (Eligible · Ends Nov 25)*
  Plus close misses: *Kotak Kanya (Requires 85% marks; student has 82%)*.

---

### Scene 4: Real Anti-Rejection Document Audit (2:00 - 2:50)
* **What to say:**  
  *"Here is our core innovation: the DocComplianceAgent. Let's see what happens if a student uploads an outdated income certificate dated August 2025."*
* **What to type in ASI:One:**
  ```text
  Income Certificate
  Applicant: Priyanshu Verma
  Total Annual Income: Rs 220000
  Date of Issue: 10/08/2025
  Tehsildar Signed
  ```
* **What appears on screen:**  
  ScholarBot renders the **Document Pre-Check Audit Card**:
  - **Status:** `WARN (Score: 65/100)`
  - **Flagged Problem:** Certificate is dated 14 months ago; Rajasthan SJMS mandates Form I/K/M issued within the last 6 months.
  - **Actionable Remedy:** *"Apply for a fresh certificate via local E-Mitra kiosk or Tehsildar before portal cutoff."*
  - **Privacy:** Notice that any Aadhaar or PAN numbers are masked as `XXXX-XXXX-1234`.

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

### Scene 6: Fetch.ai Payment Protocol Concierge Pack (3:30 - 4:10)
* **What to say:**  
  *"While scholarship search and document checklists are 100% free, we monetized an Application Concierge Pack using the official Fetch.ai Payment Protocol."*
* **What to type in ASI:One:**
  ```text
  I want the Application Concierge Pack
  ```
* **What appears on screen:**  
  ScholarBot issues an official `RequestPayment` (0.01 USDC / 0.05 FET) with payment reference and metadata clearly marked as `DEMO / TESTNET`.
* **Action:**
  The student's uAgents wallet/client sends `CommitPayment` with a transaction hash (e.g. `demo-tx-priyanshu-2026`).
* **What appears on screen:**  
  The Coordinator verifies the payment on testnet, replies with `CompletePayment`, and delivers:
  - Complete pre-filled student dossier.
  - Step-by-step portal submission workflow.
  - **Personalized 250-word Statement of Purpose (SOP / Application Essay)** drafted for Priyanshu's B.Tech aspirations and financial need.
  - Copyable `.ics` calendar alarms.

---

### Scene 7: Personal AI & "What-If" Simulation (4:10 - 4:40)
* **What to say:**  
  *"For the Best Personal AI prize, ScholarBot persists user state across sessions and allows what-if simulations."*
* **What to type in ASI:One:**
  ```text
  What if my family income was 4.5 lakh instead of 2.2 lakh?
  ```
* **What appears on screen:**  
  ScholarBot simulates both scenarios instantly:  
  *At ₹2.2L, you qualify for full state tuition fee waivers. At ₹4.5L, state waivers close, but Central Sector and Tata Trusts remain fully open.*
* **Closing:**  
  *"From natural intent to decisive action: ScholarBot helps every Indian student claim the education funding they deserve. Thank you!"*
