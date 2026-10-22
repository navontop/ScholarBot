"""
ScholarBot - Standalone Agentverse Hosted Agent
Single self-contained file (zero local imports). Paste it into agent.py in the Agentverse editor.
Set ASI1_API_KEY (optional) and PAYMENT_DEMO_MODE=true in the hosted agent's .env / Secrets.
Card icons: Twemoji graphics (c) Twitter / jdecked, licensed CC-BY 4.0.
"""
import asyncio
import difflib
import hashlib
import json
import logging
import os
import re
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

try:  # httpx is not in the documented hosted-package list, so never crash without it
    import httpx
except Exception:  # pragma: no cover
    httpx = None

from pydantic.v1 import Field
from uagents import Agent, Context, Protocol, Model
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    MetadataContent,
    ResourceContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)
from uagents_core.contrib.protocols.payment import (
    CommitPayment,
    CompletePayment,
    Funds,
    RejectPayment,
    RequestPayment,
    payment_protocol_spec,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
logger = logging.getLogger("ScholarBotHosted")

# ==============================================================================
# EMBEDDED DATASETS (all records are unverified until checked on official portals)
# ==============================================================================
EMBEDDED_SCHOLARSHIPS = json.loads('[{"id": "nsp_central_sector", "name": "Central Sector Scheme of Scholarships for College & University Students", "provider": "Department of Higher Education, Govt of India", "portal": "National Scholarship Portal (NSP)", "portal_url": "https://scholarships.gov.in", "source_url": "https://www.education.gov.in/scholarships-education-loan-0", "amount": "\\u20b912,000 to \\u20b920,000 per year directly in bank", "amount_value": 20000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 75.0, "max_family_income": 450000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "MBA / M.Tech / M.Sc", "Law (LLB / LLM)", "Degree"], "states": ["All", "Pan-India"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-11-30", "last_verified": null, "verified": false, "description": "Financial assistance by Ministry of Education for meritorious low-income students in top 20th percentile of their 12th board."}, {"id": "aicte_pragati_girls", "name": "AICTE Pragati Scholarship Scheme for Girl Students", "provider": "AICTE / Ministry of Education, Govt of India", "portal": "National Scholarship Portal (NSP)", "portal_url": "https://scholarships.gov.in", "source_url": "https://www.aicte-india.org/schemes/students-development-schemes/Pragati", "amount": "\\u20b950,000 per year towards tuition & technical tools support", "amount_value": 50000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 50.0, "max_family_income": 800000, "courses": ["B.Tech / B.E.", "Diploma / Polytechnic", "Engineering"], "states": ["All", "Pan-India"], "gender": "Female", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-31", "last_verified": null, "verified": false, "description": "Empowers female students admitted to 1st year AICTE-approved degree/diploma technical programs with \\u20b950,000 annual aid."}, {"id": "aicte_saksham", "name": "AICTE Saksham Scholarship Scheme for Specially Abled Students", "provider": "AICTE / Govt of India", "portal": "National Scholarship Portal (NSP)", "portal_url": "https://scholarships.gov.in", "source_url": "https://www.aicte-india.org/schemes/students-development-schemes/Saksham", "amount": "\\u20b950,000 per year assistance for technical degree/diploma", "amount_value": 50000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 50.0, "max_family_income": 800000, "courses": ["B.Tech / B.E.", "Diploma / Polytechnic", "Engineering"], "states": ["All", "Pan-India"], "gender": "All", "disability_required": true, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-31", "last_verified": null, "verified": false, "description": "Financial aid for students with >= 40% benchmark disability enrolled in technical courses at AICTE-approved institutes."}, {"id": "post_matric_sc_central", "name": "Centrally Sponsored Post-Matric Scholarship for SC Students", "provider": "Ministry of Social Justice & Empowerment, GoI", "portal": "National Scholarship Portal (NSP)", "portal_url": "https://scholarships.gov.in", "source_url": "https://socialjustice.gov.in", "amount": "100% Compulsory Non-Refundable Fee + Monthly Maintenance Allowance", "amount_value": 45000, "eligibility": {"categories": ["SC"], "min_marks": 45.0, "max_family_income": 250000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "MBA / M.Tech / M.Sc", "Diploma / Polytechnic", "Class 11th - 12th", "Degree", "Engineering"], "states": ["All", "Pan-India"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-15", "last_verified": null, "verified": false, "description": "Full fee reimbursement and monthly allowance for Scheduled Caste students pursuing post-matric and higher studies."}, {"id": "post_matric_st_central", "name": "National Fellowship and Scholarship for Higher Education of ST Students", "provider": "Ministry of Tribal Affairs, Govt of India", "portal": "National Scholarship Portal (NSP)", "portal_url": "https://scholarships.gov.in", "source_url": "https://tribal.nic.in", "amount": "Full Tuition Fees + Books & Computer Allowance (Up to \\u20b945,000)", "amount_value": 45000, "eligibility": {"categories": ["ST"], "min_marks": 50.0, "max_family_income": 600000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "MBA / M.Tech / M.Sc", "PhD / Doctorate", "Degree", "Engineering"], "states": ["All", "Pan-India"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-11-25", "last_verified": null, "verified": false, "description": "Covers actual tuition fees and academic expenses for Scheduled Tribe students in top institutes like IITs, NITs, and central universities."}, {"id": "minority_post_matric", "name": "Post-Matric Scholarship Scheme for Minorities", "provider": "Ministry of Minority Affairs, Govt of India", "portal": "National Scholarship Portal (NSP)", "portal_url": "https://scholarships.gov.in", "source_url": "https://minorityaffairs.gov.in", "amount": "Admission & Tuition Fee Reimbursement + Monthly Maintenance", "amount_value": 25000, "eligibility": {"categories": ["Minority", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Parsi"], "min_marks": 50.0, "max_family_income": 200000, "courses": ["Class 11th - 12th", "B.Tech / B.E.", "B.Sc / BCA / B.Com / BA", "MBA / M.Tech / M.Sc", "Diploma / Polytechnic", "Degree", "Engineering"], "states": ["All", "Pan-India"], "gender": "All", "disability_required": false, "minority_required": true, "min_year_of_study": 1}, "deadline": "2026-11-20", "last_verified": null, "verified": false, "description": "Financial assistance for meritorious students from notified minority communities to pursue higher education."}, {"id": "raj_postmatric_sje", "name": "Rajasthan Post-Matric Scholarship (Uttarmatric Scheme)", "provider": "Social Justice & Empowerment Dept (SJMS Rajasthan)", "portal": "SJMS Portal Rajasthan", "portal_url": "https://sjmsnew.rajasthan.gov.in/scholarship/", "source_url": "https://sje.rajasthan.gov.in", "amount": "100% Tuition Fee Reimbursement + Monthly Maintenance Allowance", "amount_value": 60000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority", "SBC", "EBC"], "min_marks": 50.0, "max_family_income": 250000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "MBA / M.Tech / M.Sc", "Diploma / Polytechnic", "Class 11th - 12th", "Degree", "Engineering"], "states": ["Rajasthan"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-15", "last_verified": null, "verified": false, "description": "Flagship Rajasthan state scholarship granting 100% course fee waiver for domicile students via Jan Aadhaar DBT."}, {"id": "up_postmatric_dashmottar", "name": "UP Dashmottar Post-Matric Scholarship Scheme", "provider": "Social Welfare Dept, Govt of Uttar Pradesh", "portal": "UP Scholarship Portal", "portal_url": "https://scholarship.up.gov.in", "source_url": "https://scholarship.up.gov.in/Rules.aspx", "amount": "Full Tuition Fee Reimbursement + \\u20b910,000 Maintenance Allowance", "amount_value": 55000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 50.0, "max_family_income": 250000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "MBA / M.Tech / M.Sc", "Diploma / Polytechnic", "Class 11th - 12th", "Degree", "Engineering"], "states": ["Uttar Pradesh"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-11-15", "last_verified": null, "verified": false, "description": "Comprehensive scholarship for UP domicile college students covering non-refundable fees and monthly stipend."}, {"id": "maha_ebc_rajarshi_shahu", "name": "Maharashtra Rajarshi Chhatrapati Shahu Maharaj EBC Scheme", "provider": "Directorate of Higher Education, Maharashtra", "portal": "MahaDBT Portal", "portal_url": "https://mahadbt.maharashtra.gov.in", "source_url": "https://mahadbt.maharashtra.gov.in/SchemeData/SchemeData?str=4950543063675038", "amount": "50% to 100% Tuition & Exam Fee Concession", "amount_value": 40000, "eligibility": {"categories": ["General", "EWS", "OBC"], "min_marks": 50.0, "max_family_income": 800000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "MBA / M.Tech / M.Sc", "Diploma / Polytechnic", "Degree", "Engineering"], "states": ["Maharashtra"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-31", "last_verified": null, "verified": false, "description": "Fee concession scheme for students from Economically Backward Classes enrolled in professional higher education in Maharashtra."}, {"id": "bihar_post_matric", "name": "Bihar Post-Matric Scholarship Scheme (PMS Bihar)", "provider": "Education Department, Govt of Bihar", "portal": "PMS Bihar Online Portal", "portal_url": "https://pmsonline.bih.nic.in", "source_url": "https://pmsonline.bih.nic.in", "amount": "Full Course Fee Reimbursement + Book Allowance", "amount_value": 35000, "eligibility": {"categories": ["OBC", "SC", "ST", "EWS", "BC", "EBC"], "min_marks": 50.0, "max_family_income": 300000, "courses": ["B.Tech / B.E.", "Diploma / Polytechnic", "B.Sc / BCA / B.Com / BA", "MBA / M.Tech / M.Sc", "Degree", "Engineering"], "states": ["Bihar"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-10", "last_verified": null, "verified": false, "description": "Financial support for post-matric studies for domicile students of Bihar belonging to BC, EBC, SC, ST communities."}, {"id": "mp_postmatric_scholarship", "name": "Madhya Pradesh Post-Matric Scholarship (SC/ST/OBC)", "provider": "Tribal Welfare Dept, Govt of Madhya Pradesh", "portal": "MP Scholarship Portal 2.0", "portal_url": "http://scholarshipportal.mp.nic.in", "source_url": "http://scholarshipportal.mp.nic.in", "amount": "100% Govt College Fee + Hostel / Boarding Grant", "amount_value": 32000, "eligibility": {"categories": ["SC", "ST", "OBC"], "min_marks": 50.0, "max_family_income": 300000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "Diploma / Polytechnic", "Degree", "Engineering"], "states": ["Madhya Pradesh"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-20", "last_verified": null, "verified": false, "description": "Fee and hostel allowance for reserved category students in higher education institutes across Madhya Pradesh."}, {"id": "delhi_merit_scholarship", "name": "Delhi Merit Scholarship for SC/ST/OBC/Minority in Colleges", "provider": "Dept for the Welfare of SC/ST/OBC, Govt of NCT Delhi", "portal": "Delhi e-District Portal", "portal_url": "https://edistrict.delhigovt.nic.in", "source_url": "https://edistrict.delhigovt.nic.in", "amount": "\\u20b921,600 to \\u20b935,000 per year cash assistance", "amount_value": 35000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 60.0, "max_family_income": 300000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "MBA / M.Tech / M.Sc", "Diploma / Polytechnic", "Degree", "Engineering"], "states": ["Delhi"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-15", "last_verified": null, "verified": false, "description": "Merit scholarship by Delhi Govt for students securing >= 60% marks enrolled in recognized colleges/universities in NCT of Delhi."}, {"id": "wb_oasis_scholarship", "name": "West Bengal OASIS Post-Matric Scholarship", "provider": "Backward Classes Welfare Dept, Govt of West Bengal", "portal": "OASIS Portal West Bengal", "portal_url": "https://oasis.gov.in", "source_url": "https://oasis.gov.in", "amount": "Tuition Fee Waiver + \\u20b91,200/month Hosteller Allowance", "amount_value": 30000, "eligibility": {"categories": ["SC", "ST", "OBC"], "min_marks": 50.0, "max_family_income": 250000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "Diploma / Polytechnic", "Degree", "Engineering"], "states": ["West Bengal"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-10", "last_verified": null, "verified": false, "description": "Online application scholarship system for Scheduled Castes, Scheduled Tribes and OBC students of West Bengal."}, {"id": "karnataka_ssp_postmatric", "name": "Karnataka State Scholarship Portal (SSP Post-Matric)", "provider": "Social Welfare & Backward Classes Welfare Dept, Karnataka", "portal": "SSP Karnataka Portal", "portal_url": "https://ssp.postmatric.karnataka.gov.in", "source_url": "https://ssp.postmatric.karnataka.gov.in", "amount": "100% Tuition Fee Exemption + Vidyasiri Food & Accommodation", "amount_value": 45000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 50.0, "max_family_income": 250000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "Diploma / Polytechnic", "MBA / M.Tech / M.Sc", "Degree", "Engineering"], "states": ["Karnataka"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-11-30", "last_verified": null, "verified": false, "description": "Unified single-window scholarship platform in Karnataka providing tuition reimbursement and Vidyasiri hostel support."}, {"id": "reliance_ug_scholarship", "name": "Reliance Foundation Undergraduate Scholarship", "provider": "Reliance Foundation CSR", "portal": "Reliance Foundation Scholarships Portal", "portal_url": "https://www.scholarships.reliancefoundation.org", "source_url": "https://www.scholarships.reliancefoundation.org/Undergraduate_Scholarship.aspx", "amount": "Up to \\u20b92,00,000 over course duration + Mentorship & Leadership", "amount_value": 200000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 60.0, "max_family_income": 1500000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "Degree", "Engineering"], "states": ["All", "Pan-India"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-10-31", "last_verified": null, "verified": false, "description": "Merit-cum-means scholarship supporting 5,000 top first-year undergraduate students with grants and alumni network."}, {"id": "hdfc_parivartan_ecss", "name": "HDFC Bank Parivartan\'s Educational Crisis Support (ECSS)", "provider": "HDFC Bank CSR", "portal": "Buddy4Study / HDFC CSR", "portal_url": "https://www.buddy4study.com/page/hdfc-bank-parivartans-ecss-programme", "source_url": "https://www.hdfcbank.com/personal/about-us/corporate-social-responsibility", "amount": "Up to \\u20b975,000 per year direct grant", "amount_value": 75000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 55.0, "max_family_income": 250000, "courses": ["Class 10th", "Class 11th - 12th", "B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "MBA / M.Tech / M.Sc", "Diploma / Polytechnic", "Degree", "Engineering"], "states": ["All", "Pan-India"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-11-20", "last_verified": null, "verified": false, "description": "Supports students facing severe financial hardship or family crisis to prevent school and college dropouts."}, {"id": "tata_trusts_merit", "name": "Tata Trusts Means and Merit Higher Education Grant", "provider": "Tata Trusts Individual Grants Programme", "portal": "Tata Trusts Grants Portal", "portal_url": "https://www.tatatrusts.org/our-work/individual-grants-programme/education-grants", "source_url": "https://www.tatatrusts.org", "amount": "Up to 80% College Tuition Fee Support", "amount_value": 70000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 60.0, "max_family_income": 400000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "B.Sc / BCA / B.Com / BA", "MBA / M.Tech / M.Sc", "Degree", "Engineering"], "states": ["All", "Pan-India"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-11-25", "last_verified": null, "verified": false, "description": "Direct financial aid from Tata Trusts covering significant portion of tuition fees for hardworking college students."}, {"id": "ongc_scholarship", "name": "ONGC Foundation Merit Scholarship for Low Income Students", "provider": "ONGC Foundation CSR", "portal": "ONGC Foundation Portal", "portal_url": "https://ongcscholar.org", "source_url": "https://ongcscholar.org", "amount": "\\u20b948,000 per year annual financial assistance", "amount_value": 48000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST"], "min_marks": 60.0, "max_family_income": 200000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "MBA / M.Tech / M.Sc", "Degree", "Engineering"], "states": ["All", "Pan-India"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-10", "last_verified": null, "verified": false, "description": "ONGC flagship CSR scholarship disbursed annually to students enrolled in regular engineering, MBBS and MBA courses."}, {"id": "sitaram_jindal_scholarship", "name": "Sitaram Jindal Foundation Scholarship", "provider": "Sitaram Jindal Foundation Trust", "portal": "Sitaram Jindal Trust Portal", "portal_url": "https://www.sitaramjindalfoundation.org", "source_url": "https://www.sitaramjindalfoundation.org/scholarships-information.php", "amount": "\\u20b93,200/month for professional degree courses", "amount_value": 38400, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 60.0, "max_family_income": 400000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "Diploma / Polytechnic", "B.Sc / BCA / B.Com / BA", "Degree", "Engineering"], "states": ["All", "Pan-India"], "gender": "All", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-12-31", "last_verified": null, "verified": false, "description": "Monthly stipend support from Sitaram Jindal Foundation for underprivileged youth pursuing graduation and polytechnic diplomas."}, {"id": "kotak_kanya_scholarship", "name": "Kotak Kanya Scholarship for Meritorious Girls", "provider": "Kotak Education Foundation CSR", "portal": "Buddy4Study / Kotak CSR", "portal_url": "https://www.buddy4study.com/page/kotak-kanya-scholarship", "source_url": "https://kotakeducation.org/scholarships/", "amount": "\\u20b91,50,000 per year until professional graduation", "amount_value": 150000, "eligibility": {"categories": ["General", "EWS", "OBC", "SC", "ST", "Minority"], "min_marks": 85.0, "max_family_income": 600000, "courses": ["B.Tech / B.E.", "MBBS / BDS / Medical", "Law (LLB / LLM)", "Degree", "Engineering"], "states": ["All", "Pan-India"], "gender": "Female", "disability_required": false, "minority_required": false, "min_year_of_study": 1}, "deadline": "2026-11-15", "last_verified": null, "verified": false, "description": "Substantial financial grant to support meritorious girl students from low-income families pursuing professional 4-5 year degrees."}]')


EMBEDDED_DOC_RULES = json.loads('{"nsp_central_sector": {"mandatory": ["Aadhaar Card with Biometric Authentication at Institute", "Current Financial Year Income Certificate (Tehsildar signed, <= 4.5 Lakhs)", "NSP Bonafide Student Certificate (Generated from NSP portal & signed by Principal)", "Class 12th Board Marksheet (Top 20th percentile)", "Single Savings Bank Account Passbook (NPCI DBT-seeded with Aadhaar)"], "warning": "CRITICAL REJECTION ALERT: NSP requires biometric authentication at your college institute nodal officer (CNO). If your college has not completed biometric onboarding, the application is automatically frozen.", "tips": ["Verify Aadhaar-NPCI active mapping on UIDAI portal (myaadhaar.uidai.gov.in) before applying.", "Do NOT use minor, Jan Dhan zero-balance, or joint bank accounts because scholarship credits exceed limit.", "Student name, father\'s name, and DOB must match letter-for-letter between Class 10th and Aadhaar."], "portal": "https://scholarships.gov.in", "steps": ["1. Register on NSP One-Time Registration (OTR) via Face-Auth mobile app.", "2. Fill scholarship application using generated OTR ID.", "3. Download auto-generated Bonafide form and get Principal\'s seal & signature.", "4. Upload fee receipt, income certificate and marksheet.", "5. Visit college Nodal Officer for biometric verification before deadline."], "validity_months": 12}, "aicte_pragati_girls": {"mandatory": ["Aadhaar Card of the girl candidate", "Centralized Admission Process (CAP / JoSAA / State Counselling) Allotment Letter", "Current Financial Year Income Certificate (Family income <= 8 Lakhs)", "Bonafide Certificate from AICTE-approved Degree / Polytechnic Institute", "Class 10th & 12th Marksheets", "Active Single Bank Account seeded with Aadhaar DBT"], "warning": "CRITICAL: Valid only for female students admitted to the 1st year of an AICTE-approved institution through centralized admission (or lateral entry to 2nd year). Management quota admissions are disqualified.", "tips": ["Ensure maximum 2 girl children per family limit is observed (affidavit required).", "Tuition fee receipt must be clear and stamped by college accounts department."], "portal": "https://scholarships.gov.in", "steps": ["1. Log in to National Scholarship Portal (NSP).", "2. Select AICTE Schemes -> Pragati Scholarship Scheme for Girls.", "3. Upload CAP allotment letter, income certificate and bonafide.", "4. Submit and hand over physical copy to college AICTE coordinator."], "validity_months": 12}, "aicte_saksham": {"mandatory": ["UDID Card or Government Disability Certificate issued by CMO (>= 40% disability)", "CAP / State Counselling Admission Allotment Letter", "Family Income Certificate (<= 8 Lakhs/year)", "AICTE Institute Bonafide Certificate", "Class 10th and 12th Marksheets", "Aadhaar-seeded Bank Account Passbook"], "warning": "CRITICAL: The disability certificate must show minimum 40% benchmark disability and UDID number. Provisional medical slips without permanent registration are rejected.", "tips": ["Upload UDID card scan alongside Chief Medical Officer certificate.", "Keep digital copy of counselling allotment letter handy."], "portal": "https://scholarships.gov.in", "steps": ["1. Register on NSP and select AICTE Saksham Scheme.", "2. Fill disability percentage and UDID registration number.", "3. Upload CMO disability certificate, fee receipts and income certificate.", "4. Coordinate with institute verification officer for timely online approval."], "validity_months": 12}, "post_matric_sc_central": {"mandatory": ["Digital SC Caste Certificate (Verifiable online via state revenue portal)", "Income Certificate (Current year, <= 2.5 Lakhs)", "Aadhaar Card (Active mobile linked for OTP verification)", "Fee Breakdown Receipt (Compulsory Non-Refundable fees signed by Registrar)", "Active Single Savings Bank Passbook linked with NPCI"], "warning": "CRITICAL: The Centrally Sponsored SC scheme disburses the central share (60%) directly via DBT after the state government verifies and releases its 40% share. Bank DBT seeding is non-negotiable.", "tips": ["Old offline non-digitized caste certificates without barcode/number are rejected.", "Check with your branch manager that Aadhaar mapper is set to active (not just linked)."], "portal": "https://scholarships.gov.in", "steps": ["1. Apply via your state\'s scholarship portal or NSP depending on state guidelines.", "2. Authenticate through DigiLocker to auto-verify SC certificate.", "3. Enter non-refundable course fees breakdown.", "4. Submit to institute and retain acknowledgement copy."], "validity_months": 12}, "post_matric_st_central": {"mandatory": ["Scheduled Tribe (ST) Certificate issued by competent revenue authority", "Income Certificate (Family income <= 6.0 Lakhs)", "Admission letter for Top-Class Education / National Fellowship", "Hostel fee / tuition fee receipt signed by Warden & Registrar", "Aadhaar Card and Bank Account with active DBT"], "warning": "CRITICAL: For National Fellowship/Top Class ST scholarship, the institute must be on the Ministry of Tribal Affairs notified list of top institutions (IITs, NITs, AIIMS, IIMs, Central Universities).", "tips": ["Ensure tribe name spelling matches Central ST schedule exactly.", "Submit before November 25 to avoid ministry portal verification freeze."], "portal": "https://scholarships.gov.in", "steps": ["1. Log in to NSP and navigate to Ministry of Tribal Affairs.", "2. Select Top Class Education for ST Students.", "3. Upload institute bonafide, fee estimate and ST certificate.", "4. Forward file to institute nodal officer."], "validity_months": 12}, "minority_post_matric": {"mandatory": ["Minority Community Self-Declaration or Certificate (Muslim, Christian, Sikh, Buddhist, Jain, Parsi)", "Previous Class Marksheet with minimum 50% marks", "Income Certificate issued by designated State Authority (<= 2.0 Lakhs)", "Institute Bonafide Certificate", "Aadhaar-seeded Bank Account Passbook"], "warning": "CRITICAL: For minority scholarships, renewal candidates have 1st priority over fresh applications. Fresh applicants must apply early before quota exhaustion.", "tips": ["Self-declaration format for minority community must be dated and signed by student/parent.", "Marks in qualifying exam must strictly be >= 50.0%."], "portal": "https://scholarships.gov.in", "steps": ["1. Complete NSP OTR verification.", "2. Choose Ministry of Minority Affairs -> Post-Matric Scholarship Scheme.", "3. Upload marksheet and self-declaration affidavit.", "4. Complete institute-level scrutiny."], "validity_months": 12}, "raj_postmatric_sje": {"mandatory": ["Jan Aadhaar Card (Primary family ID with student member KYC updated)", "Tehsildar signed Income Certificate (Form I/K/M, issued within last 6 months)", "Digital Caste Certificate with QR Code (Verified on Rajasthan SSO)", "College Original Fee Receipt with official Institute Seal & serial number", "Aadhaar-seeded Single Savings Bank Account in Rajasthan"], "warning": "CRITICAL REJECTION ALERT: In Rajasthan SJMS, your family annual income registered in Jan Aadhaar portal MUST match your Tehsildar Income Certificate exactly. A 1 Rupee discrepancy triggers instant automatic rejection!", "tips": ["Update Jan Aadhaar e-KYC and family income at least 3 days before submitting on SJMS.", "Ensure fee receipt shows fee breakdown with official college seal.", "Submit hard copy of application with original receipts to College Nodal Officer within 7 days."], "portal": "https://sjmsnew.rajasthan.gov.in/scholarship/", "steps": ["1. Log in to Rajasthan SSO Portal (sso.rajasthan.gov.in) with your SSOID.", "2. Open the \'SJMS Scholarship\' application drawer.", "3. Select student profile from Jan Aadhaar and verify bank DBT account.", "4. Upload scanned fee receipt and Form I/K/M income certificate.", "5. Final submit and submit printed dossier to College Nodal Officer."], "validity_months": 6}, "up_postmatric_dashmottar": {"mandatory": ["Aadhaar Card with Mobile OTP Authentication", "UP Domicile Certificate (Niwas Praman Patra verifiable on edistrict.up.gov.in)", "Income Certificate by Tehsildar (Within valid 3-year cycle, <= 2.5 Lakhs)", "Caste Certificate (Jati Praman Patra online verified)", "College Fee Receipt & Non-Refundable Fee breakdown", "Bank Account mapped with NPCI DBT in a UP bank branch"], "warning": "CRITICAL: Verify with your college that its master data is updated and affiliated on the UP Scholarship portal for the current academic session, otherwise your application cannot be forwarded by the college.", "tips": ["Lock your application online only after getting the preliminary draft checked by college.", "Keep registration printout and deliver to college within 7 calendar days."], "portal": "https://scholarship.up.gov.in", "steps": ["1. Register on scholarship.up.gov.in under Postmatric Other Than Inter.", "2. Fill academic credentials and institute code.", "3. Complete Aadhaar e-KYC authentication via OTP.", "4. Take draft print, verify with college, then lock application."], "validity_months": 36}, "maha_ebc_rajarshi_shahu": {"mandatory": ["MahaDBT User Profile & Aadhaar Authentication", "Income Certificate issued by Tahsildar (<= 8 Lakhs)", "CAP Allotment Letter for Engineering / Medical / Professional course", "Maharashtra State Domicile Certificate", "Declaration of 2 children in the family", "Bank Passbook linked to NPCI"], "warning": "CRITICAL: Beneficiary must have taken admission through CAP (Centralized Admission Process). Admissions under management or institute level quota are ineligible for fee concession.", "tips": ["Upload Tahsildar barcode income certificate; private self-declarations are not accepted.", "Attendance must be above 75% in college to qualify for reimbursement."], "portal": "https://mahadbt.maharashtra.gov.in", "steps": ["1. Register on MahaDBT portal and complete Aadhaar biometric/OTP e-KYC.", "2. Select Directorate of Higher Education -> Rajarshi Chhatrapati Shahu Maharaj Scheme.", "3. Enter CAP application ID and upload fee receipt.", "4. Submit and track scrutiny status on dashboard."], "validity_months": 12}, "bihar_post_matric": {"mandatory": ["Aadhaar Card with mobile linkage", "Residential / Domicile Certificate of Bihar", "OBC / SC / ST Caste Certificate issued by SDO / CO", "Income Certificate (Current financial year, <= 3.0 Lakhs)", "Bonafide Certificate from College with authorized signature & seal", "Fee Structure Receipt from College"], "warning": "CRITICAL: The college where you study must be verified on PMS Bihar portal. If your institution is outside Bihar, ensure it has completed physical verification with Bihar welfare department.", "tips": ["Download standard Bonafide and Fee Structure formats directly from PMS Bihar portal.", "Ensure all uploaded documents are in clear PDF format under 400KB."], "portal": "https://pmsonline.bih.nic.in", "steps": ["1. Open pmsonline.bih.nic.in and register under Student Registration.", "2. Fill personal and bank details and wait for account verification SMS.", "3. Log in with user ID and upload bonafide and fee structure.", "4. Submit and hand over physical copy to institute coordinator."], "validity_months": 12}, "mp_postmatric_scholarship": {"mandatory": ["MP Samagra ID (9-digit Member ID & 8-digit Family ID)", "Digital Caste Certificate (SC/ST/OBC) verified on MP e-District", "Current Year Income Certificate (<= 3.0 Lakhs)", "College Admission & Fee Receipt with enrollment number", "Aadhaar Card seeded with MP bank account"], "warning": "CRITICAL: Samagra ID eKYC and Aadhaar must be linked on Samagra portal before applying. Unlinked Samagra records result in portal submission errors.", "tips": ["Check Samagra e-KYC status at samagra.gov.in prior to filling scholarship form.", "Keep digital copy of 12th marksheet ready for percentage verification."], "portal": "http://scholarshipportal.mp.nic.in", "steps": ["1. Log in to MP Scholarship Portal 2.0 with Samagra ID.", "2. Verify institutional course registration code.", "3. Upload current year fee receipt and caste certificate.", "4. Submit application for college level scrutiny."], "validity_months": 12}, "delhi_merit_scholarship": {"mandatory": ["Delhi e-District Registration & Citizen ID", "Proof of continuous residence in Delhi for last 3 years (Voter ID, Electricity bill, Domicile)", "Income Certificate issued by SDM Delhi (<= 3.0 Lakhs/year)", "SC/ST/OBC Certificate issued by Revenue Dept Delhi", "Previous Exam Marksheet with minimum 60% marks", "College Fee Receipt & Verification Letter"], "warning": "CRITICAL: Income certificate must be issued specifically by the SDM of the concerned Delhi subdivision. Certificates issued outside NCT Delhi are not accepted for Delhi state schemes.", "tips": ["Apply for SDM income certificate on edistrict.delhigovt.nic.in well before scholarship deadline.", "Bank account IFSC must match active Delhi branch or home branch."], "portal": "https://edistrict.delhigovt.nic.in", "steps": ["1. Register on Delhi e-District portal.", "2. Select Department for Welfare of SC/ST/OBC -> Merit Scholarship in Colleges.", "3. Attach e-District verified income certificate number.", "4. Submit form and print acknowledgment slip for college submission."], "validity_months": 12}, "wb_oasis_scholarship": {"mandatory": ["OASIS Online Application Acknowledgement Form", "West Bengal Digital Caste Certificate (SC/ST/OBC)", "Income Certificate issued by BDO / SDO / Municipality Executive Officer", "College Admission Receipt & Bonafide Certificate", "Aadhaar Card and Bank Account with active DBT"], "warning": "CRITICAL: The income certificate must be from an authorized Gazetted Officer (BDO/SDO/Executive Officer). Pradhan / Councillor certificates alone are rejected without official endorsement.", "tips": ["Ensure caste certificate number is successfully validated on castcertificatewb.gov.in.", "Submit physical hardcopy with documents to Block Development Office or Municipality."], "portal": "https://oasis.gov.in", "steps": ["1. Open oasis.gov.in and select Student Registration.", "2. Select primary district of college and input caste certificate details.", "3. Fill bank details and upload income certificate.", "4. Download completed form and submit to respective BDO/Municipality."], "validity_months": 12}, "karnataka_ssp_postmatric": {"mandatory": ["Karnataka SSP Student Account (Aadhaar authentication)", "RD Number (Revenue Department Number) for Caste and Income Certificate", "College Registration Number and Kutumba ID", "Hostel registration details (if claiming Vidyasiri hostel fee)", "NPCI Aadhaar-seeded Bank Account"], "warning": "CRITICAL: You must provide a valid RD Number for your Caste and Income certificate issued by Nadakacheri. If the RD number does not match your Aadhaar name, the system halts verification.", "tips": ["Verify that your college has pushed your admission data to the State Scholarship Portal.", "Ensure Kutumba ID profile is updated with family members."], "portal": "https://ssp.postmatric.karnataka.gov.in", "steps": ["1. Create account on Karnataka SSP portal with Aadhaar.", "2. Enter Nadakacheri RD numbers for caste and income.", "3. Select college and course from validated dropdown.", "4. Submit and inform college e-attestation officer for approval."], "validity_months": 12}, "reliance_ug_scholarship": {"mandatory": ["Class 12th Marksheet (Minimum 60% aggregate)", "Bonafide Student Certificate of current full-time 1st year UG degree program", "Household Income Certificate or ITR Form 16 (Family income <= 15 Lakhs)", "Aadhaar Card or Valid Government Photo ID", "Mandatory Online Aptitude Test (60 mins, camera-proctored MCQ)"], "warning": "CRITICAL: Reliance requires taking a 60-minute proctored online aptitude test within 2 weeks of application. Missing your assigned test slot leads to immediate and permanent disqualification.", "tips": ["Ensure working webcam, quiet room, and high-speed internet during the aptitude test.", "Practice basic numerical ability, verbal comprehension and logical reasoning mock tests.", "Students with family income < 2.5 Lakhs receive priority ranking."], "portal": "https://www.scholarships.reliancefoundation.org", "steps": ["1. Register on Reliance Foundation Scholarships portal.", "2. Fill academic records, college details and upload income documents.", "3. Schedule and complete 60-minute online proctored aptitude test.", "4. Shortlisted candidates are announced for grant disbursement."], "validity_months": 12}, "hdfc_parivartan_ecss": {"mandatory": ["Previous Academic Year Marksheet (Minimum 55% marks)", "Proof of Family Financial Crisis or Hardship (e.g. loss of earning parent, medical crisis, income decline)", "Income Proof (Income Certificate / Salary Slip / Affidavit, <= 2.5 Lakhs)", "Current Academic Year Admission Proof (Bonafide / ID card / Fee receipt)", "Bank Account details with passbook copy"], "warning": "CRITICAL: ECSS specifically prioritizes students facing unforeseen financial crises. Clearly uploading genuine crisis proof (medical discharge summary, death certificate of earning member, or distress certificate) dramatically increases selection probability.", "tips": ["Write a sincere, well-articulated statement explaining your family\'s financial situation.", "Upload clear color scans of fee receipts with clear breakdown."], "portal": "https://www.buddy4study.com/page/hdfc-bank-parivartans-ecss-programme", "steps": ["1. Open HDFC Parivartan ECSS application on Buddy4Study.", "2. Complete student profile and financial crisis assessment questionnaire.", "3. Upload marksheets, crisis proof, and college fee receipts.", "4. Submit before November 20 deadline."], "validity_months": 12}, "tata_trusts_merit": {"mandatory": ["All Academic Marksheets from 10th to present semester (Minimum 60% marks)", "Detailed Fee Breakdown statement on official College Letterhead", "Family Income Proof (ITR V / Income Certificate by Tehsildar, <= 4.0 Lakhs)", "Valid Student ID Card & Bonafide Certificate", "Cancelled Cheque / Bank Passbook of student\'s account"], "warning": "CRITICAL: Tata Trusts requires the fee structure breakdown explicitly signed by the College Registrar/Principal on college letterhead. Generic student portal screenshots are rejected.", "tips": ["Keep all semester marksheets in single chronological PDF file.", "Submit early as applications are processed on first-come-first-evaluated basis."], "portal": "https://www.tatatrusts.org/our-work/individual-grants-programme/education-grants", "steps": ["1. Navigate to Tata Trusts Individual Grants education portal.", "2. Fill online grant application form with exact fee breakdown.", "3. Upload consolidated marksheet PDF and registrar-signed fee estimate.", "4. Track application reference ID via email updates."], "validity_months": 12}, "ongc_scholarship": {"mandatory": ["Class 12th Marksheet for UG / Graduation Marksheet for PG (Minimum 60% marks)", "Income Certificate issued by competent revenue authority (<= 2.0 Lakhs)", "Caste / Category Certificate (General/EWS/OBC/SC/ST)", "College Admission Proof & Fee Receipt for Engineering/MBBS/MBA", "PAN Card copy and Aadhaar-seeded Bank Passbook"], "warning": "CRITICAL: Income limit is strict at \\u20b92,00,000 per annum. Applications with income certificates showing even \\u20b92,01,000 are disqualified during initial screening.", "tips": ["PAN card is mandatory for ONGC scholarship disbursement.", "Ensure applicant age is between 18 and 30 years as on date of application."], "portal": "https://ongcscholar.org", "steps": ["1. Register on ongcscholar.org portal.", "2. Choose course stream (Engineering, MBBS, MBA, Geophysics).", "3. Upload caste, income, 12th marksheet and PAN card.", "4. Submit online and download final PDF dossier."], "validity_months": 12}, "sitaram_jindal_scholarship": {"mandatory": ["Sitaram Jindal Foundation Application Form (Filled and signed)", "Previous Examination Marksheet (Minimum 60% marks)", "Income Certificate issued by Patwari / BDO / Tehsildar (<= 4.0 Lakhs)", "Fee Receipt and College Principal Recommendation Certificate", "Hostel Warden Certificate (if claiming hostel allowance)", "Bank Account details copy"], "warning": "CRITICAL: Sitaram Jindal Foundation requires physical postal submission of the application form signed by the College Principal along with attested photocopies. Online-only submissions without postal dispatch are not processed.", "tips": ["Get application form stamped and signed by the Head of Institution with college seal.", "Send speed post with tracking to Jindal Foundation Bangalore office."], "portal": "https://www.sitaramjindalfoundation.org", "steps": ["1. Download official application form from sitaramjindalfoundation.org.", "2. Fill all details and get verification signature and seal from College Principal.", "3. Attach attested copies of marksheets, income certificate and fee receipts.", "4. Dispatch via Speed Post to Sitaram Jindal Foundation, Bangalore."], "validity_months": 12}, "kotak_kanya_scholarship": {"mandatory": ["Class 12th Marksheet with minimum 85% aggregate", "Proof of admission into 1st year of professional degree (B.Tech, MBBS, Law, Design)", "Family Income Certificate / ITR / Form 16 (<= 6.0 Lakhs)", "Aadhaar Card of the student", "College Fee Receipt & Bank Passbook"], "warning": "CRITICAL: Exclusively for meritorious girl students who have secured >= 85% marks in Class 12 board examinations and gained admission to accredited professional graduation courses.", "tips": ["Highlight academic achievements and extracurriculars in the personal statement section.", "Prepare for short telephonic/video interaction if selected for final round."], "portal": "https://www.buddy4study.com/page/kotak-kanya-scholarship", "steps": ["1. Apply via Buddy4Study Kotak Kanya Scholarship page.", "2. Upload 12th marksheet, admission letter and income proof.", "3. Write personal statement on career aspirations.", "4. Shortlisted candidates attend virtual interview before final grant award."], "validity_months": 12}, "default": {"mandatory": ["Aadhaar Card (Active Mobile Linked for OTP verification)", "Current Financial Year Income Certificate (Tehsildar / Revenue Officer signed)", "Category Certificate (General / EWS / OBC / SC / ST / Minority)", "Current Academic Year College Bonafide Certificate & Fee Receipt", "Active Single Savings Bank Passbook seeded with NPCI Aadhaar DBT"], "warning": "IMPORTANT: Over 40% of scholarship grants fail due to unlinked NPCI bank mapping. Visit your home bank branch to confirm DBT activation before deadline!", "tips": ["Always submit applications at least 7 days before deadline to avoid portal crashes.", "Double check bank IFSC and ensure name matches exactly across marksheets and Aadhaar."], "portal": "https://scholarships.gov.in", "steps": ["1. Open the official scholarship portal.", "2. Complete initial registration and Aadhaar e-KYC.", "3. Fill academic and family background details.", "4. Upload verified documents and submit for college level verification."], "validity_months": 12}}')

# ==============================================================================
# CARD IMAGES - one icon per hub action, ONE graduation cap for every scholarship
# ==============================================================================
_TWEMOJI = "https://raw.githubusercontent.com/jdecked/twemoji/main/assets/72x72/{}.png"
SCHOLARSHIP_IMG = _TWEMOJI.format("1f393")  # graduation cap, used for every scholarship card
HUB_IMG = {
    "find": _TWEMOJI.format("1f50d"),
    "audit": _TWEMOJI.format("1f4c4"),
    "deadlines": _TWEMOJI.format("1f4c5"),
    "whatif": _TWEMOJI.format("1f52e"),
    "concierge": _TWEMOJI.format("26a1"),
    "profile": _TWEMOJI.format("1f464"),
    "home": _TWEMOJI.format("1f3e0"),
}

# ==============================================================================
# MODELS
# ==============================================================================
class StudentProfile(Model):
    student_name: str = "Student"
    state: str = "All"
    category: str = "General"
    family_income: float = 250000.0
    course: str = "Engineering"
    marks_percentage: float = 75.0
    gender: str = "All"
    disability: bool = False
    minority: bool = False
    year_of_study: int = 1
    income_label: str = ""   # form option key the user picked ("" = exact value typed in chat)
    marks_label: str = ""    # form option key the user picked ("" = exact value typed in chat)
    missing_fields: List[str] = Field(default_factory=list)
    raw_text: str = ""


class ScholarshipItem(Model):
    id: str
    name: str
    provider: str
    portal: str
    portal_url: str
    source_url: str = ""
    amount: str
    amount_value: float = 0.0
    category_list: List[str] = Field(default_factory=list)
    min_marks: float = 0.0
    max_family_income: float = 10000000.0
    applicable_states: List[str] = Field(default_factory=list)
    gender: str = "All"
    disability_required: bool = False
    minority_required: bool = False
    deadline: str = "2026-12-31"
    description: str = ""
    match_score: int = 80
    match_status: str = "eligible"  # eligible, close_miss, ineligible
    match_reason: str = ""
    last_verified: Optional[str] = None
    verified: bool = False


class AuditCheckItem(Model):
    check_name: str
    status: str  # PASS, WARN, FAIL, INFO
    details: str
    remedy: str = ""


class DocumentAuditRequest(Model):
    session_id: str
    scheme_id: str
    doc_type: str = "income_certificate"
    doc_text: str = ""
    profile: StudentProfile


class DocumentAuditResponse(Model):
    session_id: str
    scheme_id: str
    doc_type: str
    overall_status: str
    readiness_score: int
    extracted_fields: Dict[str, str] = Field(default_factory=dict)
    checks: List[AuditCheckItem] = Field(default_factory=list)
    action_plan: List[str] = Field(default_factory=list)
    disclaimer: str = "Pre-check advisory based on published rules. Always verify on official portal."


class DeadlineItem(Model):
    scheme_id: str
    scheme_name: str
    portal_url: str
    deadline_date: str
    days_remaining: int
    urgency_tier: str
    badge_label: str
    ics_calendar_data: str


class ConciergePackResponse(Model):
    session_id: str
    scheme_id: str
    scheme_name: str
    pack_title: str
    markdown_content: str
    sop_essay: str = ""
    ics_data: str = ""


# ==============================================================================
# DISPLAY HELPERS - show the SAME label the student picked, never a hidden number
# ==============================================================================
def format_inr(value: float) -> str:
    """Indian digit grouping: 300000 -> ₹3,00,000."""
    try:
        s = str(int(round(float(value))))
    except Exception:
        return "₹0"
    if len(s) <= 3:
        return "₹" + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return "₹" + ",".join(parts) + "," + tail


# key = value stored for matching; (label shown to the user, phrase used inside sentences)
INCOME_BANDS: Dict[str, Tuple[str, str]] = {
    "90000": ("Below ₹1.0 Lakh / year", "below ₹1.0 lakh per year"),
    "150000": ("₹1.0 - ₹1.5 Lakhs / year", "between ₹1.0 and ₹1.5 lakhs per year"),
    "250000": ("₹1.5 - ₹2.5 Lakhs / year", "between ₹1.5 and ₹2.5 lakhs per year"),
    "450000": ("₹2.5 - ₹4.5 Lakhs / year", "between ₹2.5 and ₹4.5 lakhs per year"),
    "800000": ("₹4.5 - ₹8.0 Lakhs / year", "between ₹4.5 and ₹8.0 lakhs per year"),
    "1500000": ("Above ₹8.0 Lakhs / year", "above ₹8.0 lakhs per year"),
}
MARKS_BANDS: Dict[str, Tuple[str, str]] = {
    "85": ("85% and above (8.5+ CGPA)", "85% and above"),
    "75": ("75% - 84% (7.5 - 8.4 CGPA)", "between 75% and 84%"),
    "60": ("60% - 74% (6.0 - 7.4 CGPA)", "between 60% and 74%"),
    "50": ("50% - 59% (5.0 - 5.9 CGPA)", "between 50% and 59%"),
    "45": ("Below 50% (below 5.0 CGPA)", "below 50%"),
}


def income_text(p: StudentProfile) -> str:
    if p.income_label in INCOME_BANDS:
        return INCOME_BANDS[p.income_label][0]
    return f"{format_inr(p.family_income)} / year"


def income_phrase(p: StudentProfile) -> str:
    if p.income_label in INCOME_BANDS:
        return INCOME_BANDS[p.income_label][1]
    return f"{format_inr(p.family_income)} per year"


def marks_text(p: StudentProfile) -> str:
    if p.marks_label in MARKS_BANDS:
        return MARKS_BANDS[p.marks_label][0]
    return f"{p.marks_percentage:g}%"


def marks_phrase(p: StudentProfile) -> str:
    if p.marks_label in MARKS_BANDS:
        return MARKS_BANDS[p.marks_label][1]
    return f"{p.marks_percentage:g}%"


# ==============================================================================
# PRIVACY MASKING
# ==============================================================================
def mask_sensitive_identifiers(text: str) -> str:
    """Masks Aadhaar, PAN, phone and bank-account numbers."""
    if not text:
        return ""
    text = re.sub(r"\b\d{4}[\s-]\d{4}[\s-](\d{4})\b", r"XXXX-XXXX-\1", text)
    text = re.sub(r"\b\d{8}(\d{4})\b", r"XXXX-XXXX-\1", text)
    text = re.sub(r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b", "[REDACTED_PAN]", text)
    text = re.sub(r"(?:\+91[\s-]?)?(?:\b0)?[6-9]\d{9}\b", "[REDACTED_PHONE]", text)
    text = re.sub(r"(?i)\b(?:a/c|acc(?:ount)?(?:\s*no)?\.?)\s*[:#-]?\s*\d{8,18}\b", "[REDACTED_ACCOUNT]", text)
    text = re.sub(r"\b\d{11,18}\b", "[REDACTED_ACCOUNT]", text)
    return text


# ==============================================================================
# MATCHING ENGINE
# ==============================================================================
STATE_ALIASES: Dict[str, str] = {
    "up": "Uttar Pradesh", "uttar pradesh": "Uttar Pradesh", "u.p.": "Uttar Pradesh",
    "mp": "Madhya Pradesh", "madhya pradesh": "Madhya Pradesh", "m.p.": "Madhya Pradesh",
    "rj": "Rajasthan", "rajasthan": "Rajasthan", "raj": "Rajasthan",
    "mh": "Maharashtra", "maharashtra": "Maharashtra", "bombay": "Maharashtra",
    "dl": "Delhi", "delhi": "Delhi", "dilli": "Delhi", "nct": "Delhi", "new delhi": "Delhi",
    "wb": "West Bengal", "west bengal": "West Bengal", "bengal": "West Bengal", "paschim banga": "West Bengal",
    "ka": "Karnataka", "karnataka": "Karnataka", "bangalore": "Karnataka", "bengaluru": "Karnataka",
    "tn": "Tamil Nadu", "tamil nadu": "Tamil Nadu", "tamilnadu": "Tamil Nadu", "chennai": "Tamil Nadu",
    "kl": "Kerala", "kerala": "Kerala",
    "ap": "Andhra Pradesh", "andhra pradesh": "Andhra Pradesh", "andhra": "Andhra Pradesh",
    "ts": "Telangana", "telangana": "Telangana", "hyderabad": "Telangana",
    "gj": "Gujarat", "gujarat": "Gujarat",
    "pb": "Punjab", "punjab": "Punjab",
    "hr": "Haryana", "haryana": "Haryana",
    "br": "Bihar", "bihar": "Bihar",
    "jh": "Jharkhand", "jharkhand": "Jharkhand",
    "od": "Odisha", "odisha": "Odisha", "orissa": "Odisha",
    "as": "Assam", "assam": "Assam",
    "ch": "Chandigarh", "chandigarh": "Chandigarh",
    "jk": "Jammu and Kashmir", "j&k": "Jammu and Kashmir", "jammu & kashmir": "Jammu and Kashmir",
    "jammu and kashmir": "Jammu and Kashmir", "kashmir": "Jammu and Kashmir",
    "la": "Ladakh", "ladakh": "Ladakh",
    "ga": "Goa", "goa": "Goa",
    "uk": "Uttarakhand", "uttarakhand": "Uttarakhand", "uttaranchal": "Uttarakhand",
    "hp": "Himachal Pradesh", "himachal pradesh": "Himachal Pradesh", "himachal": "Himachal Pradesh",
    "ct": "Chhattisgarh", "chhattisgarh": "Chhattisgarh", "cg": "Chhattisgarh",
    "sk": "Sikkim", "sikkim": "Sikkim",
    "tr": "Tripura", "tripura": "Tripura",
    "ml": "Meghalaya", "meghalaya": "Meghalaya",
    "mn": "Manipur", "manipur": "Manipur",
    "nl": "Nagaland", "nagaland": "Nagaland",
    "mz": "Mizoram", "mizoram": "Mizoram",
    "ar": "Arunachal Pradesh", "arunachal pradesh": "Arunachal Pradesh",
    "py": "Puducherry", "puducherry": "Puducherry", "pondicherry": "Puducherry",
    "an": "Andaman and Nicobar Islands", "andaman": "Andaman and Nicobar Islands",
    "dn": "Dadra and Nagar Haveli and Daman and Diu", "daman": "Dadra and Nagar Haveli and Daman and Diu",
    "ld": "Lakshadweep", "lakshadweep": "Lakshadweep",
    "all": "All", "pan-india": "All", "india": "All",
}

COURSE_KEYWORDS: Dict[str, List[str]] = {
    "B.Tech / B.E.": ["b.tech", "btech", "b.e.", "be", "engineering", "cse", "ece", "mech", "civil", "tech", "it"],
    "MBBS / BDS / Medical": ["mbbs", "bds", "medical", "nursing", "b.pharm", "pharma", "dentist", "doctor", "ayush"],
    "B.Sc / BCA / B.Com / BA": ["bsc", "b.sc", "bca", "bcom", "b.com", "ba", "b.a.", "degree", "graduation", "undergraduate", "ug"],
    "MBA / M.Tech / M.Sc": ["mba", "m.tech", "mtech", "m.sc", "msc", "mca", "postgraduate", "pg", "master"],
    "Diploma / Polytechnic": ["diploma", "polytechnic", "iti"],
    "Law (LLB / LLM)": ["law", "llb", "llm", "ba llb"],
    "Class 11th - 12th": ["11th", "12th", "inter", "intermediate", "higher secondary", "+2"],
    "Class 10th": ["10th", "matric", "high school", "secondary"],
    "PhD / Doctorate": ["phd", "doctorate", "research", "fellowship"],
}

SHORT_STATE_CODES = {
    "up", "mp", "ap", "hp", "uk", "dl", "rj", "mh", "ka", "tn",
    "kl", "gj", "pb", "hr", "br", "jh", "od", "as", "ch", "ga",
    "sk", "tr", "ml", "mn", "nl", "mz", "ar", "py", "an", "jk", "ts", "ct",
}


def normalize_state(text: str) -> str:
    cleaned = text.strip().lower()
    if cleaned in STATE_ALIASES and len(cleaned) <= 3:
        return STATE_ALIASES[cleaned]
    for alias, canonical in STATE_ALIASES.items():
        if len(alias) <= 3 or alias in ["all", "india", "pan-india"]:
            continue
        if re.search(r"\b" + re.escape(alias) + r"\b", cleaned):
            return canonical
    for code in SHORT_STATE_CODES:
        if code not in STATE_ALIASES:
            continue
        pattern = (
            r"\b(?:from|state|in|resident\s+of|domicile|location|hail\s+from|living\s+in)\s*[:=]?\s*" + re.escape(code) + r"\b|"
            r"\b" + re.escape(code) + r"\s+(?:se\b|state\b|resident\b|domicile\b|board\b)|"
            r"\b(?:main|i\s+am)\s+" + re.escape(code) + r"\s+se\b|"
            r"\bstate\s*[:=]\s*" + re.escape(code) + r"\b"
        )
        if re.search(pattern, cleaned):
            return STATE_ALIASES[code]
    if re.search(r"\bu\.p\.", cleaned):
        return "Uttar Pradesh"
    if re.search(r"\bm\.p\.", cleaned):
        return "Madhya Pradesh"
    if re.search(r"\ba\.p\.", cleaned):
        return "Andhra Pradesh"
    if re.search(r"\bh\.p\.", cleaned):
        return "Himachal Pradesh"
    return "All"


def normalize_category(cat: str) -> str:
    cleaned = cat.strip().lower()
    if cleaned in ["gen", "general", "open", "ur", "unreserved"]:
        return "General"
    if cleaned in ["ews", "economically weaker section"]:
        return "EWS"
    if cleaned in ["obc", "other backward class", "bc", "ebc", "sbc", "sebc"]:
        return "OBC"
    if cleaned in ["sc", "scheduled caste"]:
        return "SC"
    if cleaned in ["st", "scheduled tribe"]:
        return "ST"
    if cleaned in ["minority", "muslim", "christian", "sikh", "buddhist", "jain", "parsi"]:
        return "Minority"
    return "General"


def normalize_course(course: str) -> str:
    cleaned = course.strip().lower()
    for canonical, synonyms in COURSE_KEYWORDS.items():
        if cleaned == canonical.lower() or cleaned in synonyms:
            return canonical
    unambiguous_map = {
        "MBBS / BDS / Medical": ["mbbs", "bds", "medical", "nursing", "b.pharm", "pharma", "dentist", "doctor", "ayush"],
        "B.Tech / B.E.": ["b.tech", "btech", "engineering", "cse", "ece", "mech", "civil"],
        "Diploma / Polytechnic": ["diploma", "polytechnic", "iti"],
        "Law (LLB / LLM)": ["law", "llb", "llm", "ba llb"],
        "MBA / M.Tech / M.Sc": ["mba", "m.tech", "mtech", "m.sc", "msc", "mca", "postgraduate", "master"],
        "B.Sc / BCA / B.Com / BA": ["bsc", "b.sc", "bca", "bcom", "b.com", "degree", "graduation", "undergraduate"],
        "Class 11th - 12th": ["11th", "12th", "inter", "intermediate", "higher secondary", "+2"],
        "Class 10th": ["10th", "matric", "high school", "secondary"],
        "PhD / Doctorate": ["phd", "doctorate", "research", "fellowship"],
    }
    for canonical, syns in unambiguous_map.items():
        for syn in syns:
            if re.search(r"\b" + re.escape(syn) + r"\b", cleaned):
                return canonical
    if re.search(r"\bb\.e\.?\b|\b(?:doing|studying|course\s*[:=]?|branch\s*[:=]?|in)\s+be\b|\bbe\s+(?:degree|engineering)\b", cleaned):
        return "B.Tech / B.E."
    if re.search(r"\bi\.t\.?\b|\binformation\s+technology\b|\b(?:doing|studying|course\s*[:=]?|branch\s*[:=]?|in)\s+it\b", cleaned):
        return "B.Tech / B.E."
    if re.search(r"\bb\.a\.?\b|\bbachelor\s+of\s+arts\b|\b(?:doing|studying|course\s*[:=]?|in)\s+ba\b|\bba\s+degree\b", cleaned):
        return "B.Sc / BCA / B.Com / BA"
    if re.search(r"\bu\.g\.?\b|\bug\s+(?:course|degree|student)\b", cleaned):
        return "B.Sc / BCA / B.Com / BA"
    if re.search(r"\bp\.g\.?\b|\bpg\s+(?:course|degree|student)\b", cleaned):
        return "MBA / M.Tech / M.Sc"
    return ""


def load_scholarships() -> List[dict]:
    return EMBEDDED_SCHOLARSHIPS


def get_scheme_income_cap(scheme_id: str) -> Optional[float]:
    if not scheme_id:
        return None
    for s in load_scholarships():
        if s.get("id", "").lower() == scheme_id.lower():
            cap = s.get("eligibility", {}).get("max_family_income")
            if cap is not None:
                return float(cap)
    return None


def evaluate_scheme(item: dict, profile: StudentProfile) -> Tuple[str, int, str]:
    """Returns (status, score, reason); status is 'eligible', 'close_miss' or 'ineligible'."""
    elig = item.get("eligibility", {})
    item_states = [s.lower() for s in elig.get("states", [])]
    user_state = profile.state.strip().lower()

    is_pan_india = ("all" in item_states) or ("pan-india" in item_states)
    if not is_pan_india:
        if not user_state or user_state in ["all", "unknown", ""]:
            return ("ineligible", 0, f"Restricted to {', '.join(elig.get('states', []))} residents (state not specified).")
        if user_state not in item_states:
            return ("ineligible", 0, f"Restricted to {', '.join(elig.get('states', []))} residents.")

    scheme_gender = elig.get("gender", "All").lower()
    user_gender = profile.gender.strip().lower()
    if scheme_gender == "female":
        if user_gender in ["female", "girl", "woman"]:
            pass
        elif user_gender in ["male", "boy", "man"]:
            return ("ineligible", 0, "Exclusively reserved for female students.")
        else:
            return ("close_miss", 75, "Maybe eligible (girls only, confirm gender).")

    if elig.get("disability_required", False) and not profile.disability:
        return ("ineligible", 0, "Requires >= 40% benchmark disability (Saksham Scheme).")

    if elig.get("minority_required", False) and not profile.minority and profile.category.lower() != "minority":
        return ("ineligible", 0, "Reserved for students from notified minority communities.")

    allowed_cats = [c.lower() for c in elig.get("categories", [])]
    user_cat = profile.category.strip().lower()
    if allowed_cats and "all" not in allowed_cats and user_cat not in allowed_cats:
        return ("ineligible", 0, f"Eligible categories: {', '.join(elig.get('categories', []))}.")

    scheme_courses = [c.lower() for c in elig.get("courses", [])]
    user_course = profile.course.strip().lower()
    if scheme_courses and "all" not in scheme_courses:
        course_matched = False
        for sc in scheme_courses:
            if sc in user_course or user_course in sc:
                course_matched = True
                break
            if "engineering" in user_course and any(eng in sc for eng in ["b.tech", "be", "engineering"]):
                course_matched = True
                break
            if "medical" in user_course and any(med in sc for med in ["mbbs", "bds", "medical", "pharm"]):
                course_matched = True
                break
            if "degree" in sc and any(deg in user_course for deg in ["b.tech", "b.sc", "bca", "b.com", "ba", "degree"]):
                course_matched = True
                break
        if not course_matched:
            return ("ineligible", 0, f"Course requirement: applicable for {', '.join(elig.get('courses', []))}.")

    min_year = int(elig.get("min_year_of_study", 1))
    user_year = getattr(profile, "year_of_study", 1) or 1
    if user_year < min_year:
        return ("ineligible", 0, f"Requires minimum Year {min_year} of study (currently Year {user_year}).")

    max_income = float(elig.get("max_family_income", 10000000.0))
    user_income = float(profile.family_income)
    if user_income > max_income:
        diff = user_income - max_income
        if diff <= 60000:
            return ("close_miss", 60, f"Income {income_text(profile)} is above the {format_inr(max_income)} cap.")
        return ("ineligible", 0, f"Annual family income exceeds the maximum ceiling of {format_inr(max_income)}.")

    min_marks = float(elig.get("min_marks", 0.0))
    user_marks = float(profile.marks_percentage)
    if user_marks < min_marks:
        if min_marks - user_marks <= 5.0:
            return ("close_miss", 65, f"Marks ({marks_text(profile)}) are slightly below the required {min_marks:g}%.")
        return ("ineligible", 0, f"Academic marks ({marks_text(profile)}) are below the minimum {min_marks:g}%.")

    score = 75
    reasons = []
    if user_state in item_states and not is_pan_india:
        score += 15
        reasons.append(f"Home-state priority for {profile.state}")
    elif is_pan_india:
        score += 5
        reasons.append("Pan-India open scheme")

    if user_income <= (max_income * 0.5):
        score += 10
        reasons.append(f"High financial need (income {income_text(profile)} vs {format_inr(max_income)} limit)")
    elif user_income <= (max_income * 0.8):
        score += 5
        reasons.append("Within standard income limits")

    if user_marks >= (min_marks + 15.0):
        score += 10
        reasons.append(f"Merit distinction (score {marks_text(profile)} vs {min_marks:g}% cutoff)")
    elif user_marks >= min_marks:
        score += 5
        reasons.append(f"Meets the minimum {min_marks:g}% academic criteria")

    return ("eligible", min(score, 100), " • ".join(reasons) if reasons else "Meets all primary eligibility criteria.")


def scheme_to_item(item: dict, status: str = "eligible", score: int = 80, reason: str = "") -> ScholarshipItem:
    elig = item.get("eligibility", {})
    return ScholarshipItem(
        id=item["id"],
        name=item["name"],
        provider=item["provider"],
        portal=item["portal"],
        portal_url=item["portal_url"],
        source_url=item.get("source_url", ""),
        amount=item["amount"],
        amount_value=float(item.get("amount_value", 0.0)),
        category_list=elig.get("categories", []),
        min_marks=float(elig.get("min_marks", 0.0)),
        max_family_income=float(elig.get("max_family_income", 10000000.0)),
        applicable_states=elig.get("states", []),
        gender=elig.get("gender", "All"),
        disability_required=bool(elig.get("disability_required", False)),
        minority_required=bool(elig.get("minority_required", False)),
        deadline=item.get("deadline", "2026-12-31"),
        description=item.get("description", ""),
        match_score=score,
        match_status=status,
        match_reason=reason,
        last_verified=item.get("last_verified"),
        verified=bool(item.get("verified", False)),
    )


def match_scholarships(profile: StudentProfile) -> Tuple[List[ScholarshipItem], List[ScholarshipItem]]:
    """Returns (eligible_items, close_misses) sorted by match score."""
    eligible: List[ScholarshipItem] = []
    close_misses: List[ScholarshipItem] = []
    for item in load_scholarships():
        status, score, reason = evaluate_scheme(item, profile)
        sc_item = scheme_to_item(item, status, score, reason)
        if status == "eligible":
            eligible.append(sc_item)
        elif status == "close_miss":
            close_misses.append(sc_item)
    eligible.sort(key=lambda x: (x.match_score, x.amount_value), reverse=True)
    close_misses.sort(key=lambda x: x.match_score, reverse=True)
    return (eligible, close_misses)

# ==============================================================================
# DOCUMENT AUDITOR (deterministic, uses today's real date)
# ==============================================================================
audit_logger = logging.getLogger("DocAuditor")
DOC_RULES_DB = EMBEDDED_DOC_RULES

MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "sept": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def parse_date_flexibly(date_str: str) -> Optional[datetime]:
    """Supports 14 August 2024, 14-Aug-24, 2024-08-14, 14/08/2024, 14.08.2024."""
    if not date_str or len(date_str.strip()) < 6:
        return None
    cleaned = date_str.strip().lower()

    word_match = re.search(r"(\d{1,2})[\s/-]+([a-z]{3,9})[\s/-]+(\d{2,4})", cleaned)
    if word_match:
        day = int(word_match.group(1))
        m_str = word_match.group(2)
        yr = int(word_match.group(3))
        if yr < 100:
            yr += 2000
        month = MONTH_NAMES.get(m_str) or MONTH_NAMES.get(m_str[:3])
        if month and 1 <= day <= 31 and 1990 <= yr <= 2040:
            try:
                return datetime(yr, month, day, tzinfo=timezone.utc)
            except Exception:
                pass

    iso_match = re.search(r"(\d{4})[\s/-](\d{1,2})[\s/-](\d{1,2})", cleaned)
    if iso_match:
        yr, month, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            try:
                return datetime(yr, month, day, tzinfo=timezone.utc)
            except Exception:
                pass

    dmy_match = re.search(r"(\d{1,2})[\s/.-](\d{1,2})[\s/.-](\d{2,4})", cleaned)
    if dmy_match:
        day, month, yr = int(dmy_match.group(1)), int(dmy_match.group(2)), int(dmy_match.group(3))
        if yr < 100:
            yr += 2000
        if 1 <= month <= 12 and 1 <= day <= 31:
            try:
                return datetime(yr, month, day, tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def parse_document_text(raw_text: str) -> Dict[str, str]:
    """Extracts structured fields from pasted document text."""
    cleaned = raw_text.strip()
    extracted: Dict[str, str] = {}

    income_match = re.search(r"(?:annual\s*income|family\s*income|total\s*income|aay|aamdani|income)[\s:=₹rs.]*(\d[\d,]{4,8})", cleaned, re.IGNORECASE)
    if income_match:
        extracted["income_amount"] = income_match.group(1).replace(",", "")
    else:
        lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lpa)", cleaned, re.IGNORECASE)
        if lakh_match:
            extracted["income_amount"] = str(int(float(lakh_match.group(1)) * 100000))

    marks_match = re.search(r"(?:marks|percentage|aggregate|score)[\s:=]*(\d{1,2}(?:\.\d+)?)\s*%", cleaned, re.IGNORECASE)
    if not marks_match:
        marks_match = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%", cleaned)
    if marks_match:
        extracted["marks_percentage"] = marks_match.group(1)

    date_patterns = [
        r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,-]+\d{2,4})\b",
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        r"\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
        r"\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{2,4})\b",
    ]
    for pat in date_patterns:
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            extracted["issue_date"] = m.group(1)
            break

    cert_m = re.search(r"(?:certificate\s*(?:no|number)|praman\s*patra\s*kramank|application\s*no|rd\s*no)[\s:=]*([A-Za-z0-9/-]{5,25})", cleaned, re.IGNORECASE)
    if cert_m:
        extracted["certificate_number"] = cert_m.group(1)

    auth_m = re.search(r"\b(tehsildar|tahsildar|sdm|sub\s*divisional\s*magistrate|revenue\s*officer|bdo|collector|circle\s*officer|cno|principal|headmaster|registrar|board|cbse|icse|state\s*board|university|council|controller\s*of\s*examinations|secretary)\b", cleaned, re.IGNORECASE)
    if auth_m:
        extracted["issuing_authority"] = auth_m.group(1).title()

    cat_m = re.search(r"\b(obc|sc|st|general|ews|backward\s*class|scheduled\s*caste|scheduled\s*tribe|minority)\b", cleaned, re.IGNORECASE)
    if cat_m:
        extracted["category"] = cat_m.group(1).upper()

    name_m = re.search(r"(?:student\s*name|applicant\s*name|name\s*of\s*applicant|name|shri|smt|kumari)[\s:=]*([A-Za-z\s]{3,30})(?:\n|,|father|s/o|d/o)", cleaned, re.IGNORECASE)
    if name_m:
        cand = name_m.group(1).strip()
        if len(cand) > 3 and not any(w in cand.lower() for w in ["income", "certificate", "government", "revenue", "marksheet"]):
            extracted["student_name"] = cand.title()

    has_qr = bool(re.search(r"\b(qr|qr-code|barcode|digitally\s*signed|e-sign(?:ed)?|verification\s*(?:code|marker|seal)|net\s*verified|seal|stamp)\b", cleaned, re.IGNORECASE))
    extracted["verification_marker"] = "Appears Present (Digital QR / e-Sign detected)" if has_qr else "Not clearly visible in text"
    return extracted


def audit_document_compliance(req: DocumentAuditRequest, scheme_income_cap: float = 250000.0) -> DocumentAuditResponse:
    """Deterministic pre-check. Any FAIL => overall FAIL. INFO checks never raise the score."""
    raw_doc = mask_sensitive_identifiers(req.doc_text)
    audit_logger.info(f"[DocAuditor] Auditing (doc_type='{req.doc_type}', scheme='{req.scheme_id}', text_len={len(raw_doc)})")

    extracted = parse_document_text(raw_doc)
    profile = req.profile
    checks: List[AuditCheckItem] = []
    action_plan: List[str] = []
    score = 100

    rule = DOC_RULES_DB.get(req.scheme_id, DOC_RULES_DB.get("default", {}))
    validity_limit_months = rule.get("validity_months", 12)

    if not raw_doc or len(raw_doc.strip()) < 15:
        return DocumentAuditResponse(
            session_id=req.session_id, scheme_id=req.scheme_id, doc_type=req.doc_type,
            overall_status="WARN", readiness_score=40, extracted_fields={},
            checks=[AuditCheckItem(
                check_name="Document Text Analysis", status="WARN",
                details="No readable text was provided.",
                remedy="Paste the text from your certificate to run the automated pre-check.")],
            action_plan=["Paste your certificate details to run the automated pre-check."],
        )

    now = datetime.now(timezone.utc)
    issue_date_str = extracted.get("issue_date")
    parsed_date = parse_date_flexibly(issue_date_str) if issue_date_str else None

    if parsed_date:
        diff_days = (now - parsed_date).days
        if diff_days < 0:
            score -= 40
            checks.append(AuditCheckItem(
                check_name="Certificate Validity Window", status="FAIL",
                details=f"Issue date ({issue_date_str}) is in the future.",
                remedy="Check the date printed on your certificate; future-dated certificates are rejected."))
            action_plan.append("Correct the invalid future issue date before submitting.")
        else:
            months_old = max(0, diff_days // 30)
            if months_old > validity_limit_months:
                score -= 40
                checks.append(AuditCheckItem(
                    check_name="Certificate Validity Window", status="FAIL",
                    details=f"Document is dated ~{months_old} months ago ({issue_date_str}), exceeding the {validity_limit_months}-month validity rule for this scheme.",
                    remedy=f"Obtain a fresh certificate issued within the last {validity_limit_months} months."))
                action_plan.append(f"Renew your certificate: it is older than {validity_limit_months} months.")
            elif months_old > 12 and validity_limit_months > 12:
                score -= 15
                checks.append(AuditCheckItem(
                    check_name="Certificate Validity Window", status="WARN",
                    details=f"Certificate is from an earlier financial year ({issue_date_str}, ~{months_old} months old).",
                    remedy="Confirm with your college Nodal Officer whether the portal accepts previous-FY certificates."))
                action_plan.append("Verify the current-FY certificate requirement with your Nodal Officer.")
            else:
                checks.append(AuditCheckItem(
                    check_name="Certificate Validity Window", status="PASS",
                    details=f"Issue date ({issue_date_str}) is within the {validity_limit_months}-month window.",
                    remedy="No action needed."))
    else:
        score -= 20
        checks.append(AuditCheckItem(
            check_name="Certificate Validity Window", status="WARN",
            details="Could not detect a valid issue date in the pasted text.",
            remedy="Make sure the certificate shows a clear issue date."))
        action_plan.append("Make sure the issue date is clearly legible on your certificate.")

    doc_type_clean = req.doc_type.lower()
    if doc_type_clean in ["income_certificate", "general"]:
        extracted_income = extracted.get("income_amount")
        if extracted_income:
            try:
                val = float(extracted_income)
                if val > scheme_income_cap:
                    score -= 40
                    checks.append(AuditCheckItem(
                        check_name="Economic Criteria (Income Ceiling)", status="FAIL",
                        details=f"Document shows annual income of {format_inr(val)}, above this scheme's ceiling of {format_inr(scheme_income_cap)}.",
                        remedy="This scheme will reject the application on income. Consider schemes with higher income caps (e.g. Reliance UG, Tata Trusts)."))
                    action_plan.append(f"Explore other schemes: income {format_inr(val)} exceeds the {format_inr(scheme_income_cap)} cap.")
                else:
                    checks.append(AuditCheckItem(
                        check_name="Economic Criteria (Income Ceiling)", status="PASS",
                        details=f"Stated income {format_inr(val)} is within the scheme ceiling ({format_inr(scheme_income_cap)}).",
                        remedy="Enter exactly the same amount on the official portal."))
            except Exception:
                pass
        else:
            score -= 15
            checks.append(AuditCheckItem(
                check_name="Economic Criteria (Income Ceiling)", status="WARN",
                details="No family income figure was detected in the pasted text.",
                remedy="Check that the certificate states the gross annual family income clearly."))
    elif doc_type_clean == "marksheet":
        extracted_marks = extracted.get("marks_percentage")
        if extracted_marks:
            try:
                marks_val = float(extracted_marks)
                if marks_val < 50.0:
                    score -= 30
                    checks.append(AuditCheckItem(
                        check_name="Academic Cutoff Verification", status="FAIL",
                        details=f"Marksheet shows {marks_val:.1f}%, below the usual 50% minimum.",
                        remedy="Look at schemes that accept your academic tier."))
                else:
                    checks.append(AuditCheckItem(
                        check_name="Academic Cutoff Verification", status="PASS",
                        details=f"Marks ({marks_val:.1f}%) meet the common minimum.",
                        remedy="Keep a clear scan of the original marksheet ready."))
            except Exception:
                pass
    elif doc_type_clean == "caste_certificate":
        extracted_cat = extracted.get("category")
        if extracted_cat and profile.category and profile.category.upper() not in ["GENERAL", "ALL"]:
            if extracted_cat != profile.category.upper() and profile.category.upper() not in extracted_cat:
                score -= 35
                checks.append(AuditCheckItem(
                    check_name="Social Category Verification", status="FAIL",
                    details=f"Certificate category ({extracted_cat}) does not match your profile ({profile.category}).",
                    remedy="Upload the certificate that matches the category you applied under."))

    doc_name = extracted.get("student_name")
    prof_name = profile.student_name.strip()
    if doc_name and prof_name and prof_name.lower() not in ["student", ""]:
        ratio = difflib.SequenceMatcher(None, doc_name.lower(), prof_name.lower()).ratio()
        if ratio < 0.6:
            score -= 30
            checks.append(AuditCheckItem(
                check_name="Applicant Name Verification", status="FAIL",
                details=f"Name on document ('{doc_name}') differs a lot from your profile name ('{prof_name}').",
                remedy="Use the exact legal name from your Class 10th marksheet and Aadhaar."))
            action_plan.append("Resolve the name mismatch (affidavit / correction) before applying.")
        elif ratio < 0.85:
            score -= 10
            checks.append(AuditCheckItem(
                check_name="Applicant Name Verification", status="WARN",
                details=f"Small spelling difference between document ('{doc_name}') and profile ('{prof_name}').",
                remedy="Portals match character by character against Aadhaar."))
        else:
            checks.append(AuditCheckItem(
                check_name="Applicant Name Verification", status="PASS",
                details=f"Name matches ({doc_name}).", remedy="No action needed."))
    else:
        checks.append(AuditCheckItem(
            check_name="Applicant Name Verification", status="INFO",
            details="Name check skipped (no name detected). Make sure it matches Aadhaar letter by letter.",
            remedy="Check Class 10th name = Aadhaar name = bank account name."))

    auth = extracted.get("issuing_authority")
    marker = extracted.get("verification_marker")
    has_qr = bool(marker and "Appears Present" in marker)
    if auth and has_qr:
        checks.append(AuditCheckItem(
            check_name="Issuing Authority & Digital Stamp", status="PASS",
            details=f"Issued by a designated officer ({auth}); a verification marker was detected.",
            remedy="Keep the digital PDF copy handy."))
    elif auth:
        score -= 15
        checks.append(AuditCheckItem(
            check_name="Issuing Authority & Digital Stamp", status="WARN",
            details=f"Issued by a designated officer ({auth}), but no QR / digital sign / seal was detected in the text.",
            remedy="Make sure the certificate has a visible QR, digital signature or official seal."))
        action_plan.append("Confirm the QR code or official seal is present on the certificate.")
    else:
        score -= 20
        checks.append(AuditCheckItem(
            check_name="Issuing Authority & Digital Stamp", status="WARN",
            details="Could not verify the issuing officer or a digital stamp.",
            remedy="Make sure the certificate carries the officer's signature and seal."))

    checks.append(AuditCheckItem(
        check_name="Bank Account NPCI DBT Mapping", status="INFO",
        details="Advisory: many scholarship rejections happen because the bank account is not NPCI/DBT mapped.",
        remedy="Check your NPCI mapping status on myaadhaar.uidai.gov.in (Bank Seeding Status)."))

    has_fail = any(c.status == "FAIL" for c in checks)
    has_warn = any(c.status == "WARN" for c in checks)
    if has_fail:
        overall, score = "FAIL", min(score, 55)
    elif has_warn:
        overall, score = "WARN", min(score, 75)
    else:
        overall = "PASS"
    score = max(min(score, 100), 20)

    if not action_plan:
        action_plan = [
            "Your document passed the primary pre-check criteria.",
            "Verify NPCI Aadhaar bank seeding before final submission.",
            "Keep stamped fee receipts from your institute.",
        ]
    return DocumentAuditResponse(
        session_id=req.session_id, scheme_id=req.scheme_id, doc_type=req.doc_type,
        overall_status=overall, readiness_score=score, extracted_fields=extracted,
        checks=checks, action_plan=action_plan,
    )


# ==============================================================================
# DEADLINES & CALENDAR
# ==============================================================================
def calculate_deadline_metrics(deadline_iso_str: str) -> Tuple[int, str, str]:
    try:
        parts = [int(p) for p in deadline_iso_str.split("-")]
        deadline_dt = datetime(parts[0], parts[1], parts[2], 23, 59, 59, tzinfo=timezone.utc)
    except Exception:
        deadline_dt = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    days = (deadline_dt - datetime.now(timezone.utc)).days
    if days < 0:
        return (days, "CLOSED", "Portal Closed for Current Session")
    if days <= 7:
        return (days, "CRITICAL_UNDER_7_DAYS", f"Closing in {days} Days (Urgent)")
    if days <= 15:
        return (days, "EXPIRING_UNDER_15_DAYS", f"Closing in {days} Days (Apply Soon)")
    return (days, "OPEN", f"{days} Days Remaining")


def generate_ics_calendar(scheme_name: str, deadline_iso_str: str, portal_url: str) -> str:
    """RFC-5545 calendar entry with 7, 3 and 1 day reminders and a stable UID."""
    now = datetime.now(timezone.utc)
    dt_stamp = now.strftime("%Y%m%dT%H%M%SZ")
    try:
        p = [int(x) for x in deadline_iso_str.split("-")]
        dt_start = f"{p[0]:04d}{p[1]:02d}{p[2]:02d}T090000Z"
        dt_end = f"{p[0]:04d}{p[1]:02d}{p[2]:02d}T180000Z"
    except Exception:
        dt_start, dt_end = "20261231T090000Z", "20261231T180000Z"
    uid = hashlib.sha256(f"{scheme_name}-{deadline_iso_str}".encode()).hexdigest()[:16]
    summary = scheme_name.replace(",", "\\,").replace(";", "\\;")
    desc = f"Application deadline for {summary}. Apply at: {portal_url}. Confirm NPCI DBT bank linking before submitting.".replace(",", "\\,").replace(";", "\\;")

    def alarm(trigger: str, text: str) -> str:
        return f"BEGIN:VALARM\r\nTRIGGER:{trigger}\r\nACTION:DISPLAY\r\nDESCRIPTION:{text}\r\nEND:VALARM\r\n"

    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//ScholarBot//Indian Scholarship Calendar//EN\r\n"
        "CALSCALE:GREGORIAN\r\nMETHOD:PUBLISH\r\nBEGIN:VEVENT\r\n"
        f"UID:scholarship-{uid}@scholarbot.asi1.ai\r\nDTSTAMP:{dt_stamp}\r\nDTSTART:{dt_start}\r\nDTEND:{dt_end}\r\n"
        f"SUMMARY:[DEADLINE] {summary}\r\nDESCRIPTION:{desc}\r\nURL:{portal_url}\r\nSTATUS:CONFIRMED\r\n"
        + alarm("-P7D", f"7 days left to apply for {summary}")
        + alarm("-P3D", f"3 days left for {summary}")
        + alarm("-P1D", f"Last day tomorrow for {summary}")
        + "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )


def build_deadline_items(schemes: List[Any]) -> List[DeadlineItem]:
    items: List[DeadlineItem] = []
    for s in schemes:
        get = (lambda k, d="": s.get(k, d)) if isinstance(s, dict) else (lambda k, d="": getattr(s, k, d))
        s_deadline = get("deadline", "2026-12-31")
        days, tier, badge = calculate_deadline_metrics(s_deadline)
        items.append(DeadlineItem(
            scheme_id=get("id"), scheme_name=get("name"), portal_url=get("portal_url"),
            deadline_date=s_deadline, days_remaining=days, urgency_tier=tier, badge_label=badge,
            ics_calendar_data=generate_ics_calendar(get("name"), s_deadline, get("portal_url")),
        ))
    items.sort(key=lambda x: (x.days_remaining < 0, x.days_remaining))
    return items


# ==============================================================================
# LLM & INTENT (ASI1 optional - everything has a regex fallback)
# ==============================================================================
ASI1_API_KEY = os.getenv("ASI1_API_KEY") or os.getenv("ASI_ONE_API_KEY", "")
ASI1_BASE_URL = os.getenv("ASI1_BASE_URL", "https://api.asi1.ai/v1")
ASI1_MODEL = os.getenv("ASI1_MODEL", "asi1")


def is_hindi_or_hinglish(text: str) -> bool:
    if not text:
        return False
    if re.search(r"[\u0900-\u097F]", text):
        return True
    words = [r"\bkya\b", r"\byaad\b", r"\bhain?\b", r"\bmujhe\b", r"\bmera\b", r"\bmeri\b", r"\bbatao\b",
             r"\bkaro\b", r"\bkaise\b", r"\bkitna\b", r"\bmilega\b", r"\bmilegi\b", r"\bpaise\b",
             r"\bchahiye\b", r"\btheek\b", r"\bnamaste\b", r"\bnamaskar\b", r"\bhoga\b", r"\bhogi\b", r"\bkarna\b"]
    return any(re.search(w, text, re.IGNORECASE) for w in words)


async def call_asi1_chat(messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 500, timeout: float = 2.0) -> Optional[str]:
    if httpx is None or not ASI1_API_KEY or ASI1_API_KEY.startswith("your_") or len(ASI1_API_KEY) < 8:
        return None
    headers = {"Authorization": f"Bearer {ASI1_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": ASI1_MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    url = f"{ASI1_BASE_URL.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
            if res.status_code == 404 and ASI1_MODEL != "asi1-mini":
                payload["model"] = "asi1-mini"
                res2 = await client.post(url, headers=headers, json=payload)
                if res2.status_code == 200:
                    return res2.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
    return None


async def extract_profile_with_llm(raw_text: str) -> Optional[StudentProfile]:
    system_prompt = (
        "You are an expert Indian education advisor. Extract student details from the user input into JSON.\n"
        "Never invent information. If a field is not mentioned, list it in 'missing_fields'.\n"
        "Convert lakh/LPA into numeric INR: '2.5 lakh' -> 250000.\n"
        "OUTPUT STRICT JSON ONLY with keys: student_name, state, category (General|EWS|OBC|SC|ST|Minority), "
        "family_income (number), course, marks_percentage (number), gender (All|Male|Female), disability (bool), "
        "minority (bool), year_of_study (number), missing_fields (list)."
    )
    safe_text = mask_sensitive_identifiers(raw_text)
    llm_resp = await call_asi1_chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Extract profile from: {safe_text}"}],
        temperature=0.1, timeout=4.0)
    if not llm_resp:
        return None
    try:
        clean = re.sub(r"^```json\s*", "", llm_resp.strip())
        clean = re.sub(r"^```\s*", "", clean)
        clean = re.sub(r"```$", "", clean).strip()
        data = json.loads(clean)
        data["raw_text"] = safe_text
        data["state"] = normalize_state(data.get("state", "All"))
        data["category"] = normalize_category(data.get("category", "General"))
        data["course"] = normalize_course(data.get("course", ""))
        return StudentProfile(**data)
    except Exception:
        return None


def extract_profile_with_regex(raw_text: str) -> StudentProfile:
    """Rule-based parser (word boundaries). Fields it cannot find are listed in missing_fields."""
    safe_text = mask_sensitive_identifiers(raw_text)
    text = safe_text.lower()
    profile = StudentProfile(raw_text=safe_text)
    missing = []

    state = normalize_state(text)
    if state != "All":
        profile.state = state
    else:
        missing.append("home_state")

    if re.search(r"\b(sc|scheduled caste)\b", text):
        profile.category = "SC"
    elif re.search(r"\b(st|scheduled tribe)\b", text):
        profile.category = "ST"
    elif re.search(r"\b(obc|other backward class|bc|ebc)\b", text):
        profile.category = "OBC"
    elif re.search(r"\b(ews|economically weaker section)\b", text):
        profile.category = "EWS"
    elif re.search(r"\b(minority|muslim|sikh|christian|jain|buddhist|parsi)\b", text):
        profile.category = "Minority"
        profile.minority = True
    elif re.search(r"\b(general|open|ur)\b", text):
        profile.category = "General"
    else:
        missing.append("social_category")

    income_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|lpa)\b", text)
    if income_match:
        profile.family_income = round(float(income_match.group(1)) * 100000.0, 2)
    else:
        num_income = re.search(r"income(?:\s*is|\s*of|\s*:)?\s*(?:rs\.?|inr|₹)?\s*(\d{5,8})\b", text)
        if num_income:
            profile.family_income = float(num_income.group(1))
        else:
            missing.append("family_income")

    marks_match = re.search(r"(\d{1,2}(?:\.\d+)?)\s*(?:%|percent|percentage|marks)", text)
    if marks_match:
        profile.marks_percentage = float(marks_match.group(1))
    else:
        missing.append("academic_marks")

    c_norm = normalize_course(text)
    if c_norm:
        profile.course = c_norm
    else:
        profile.course = ""
        missing.append("course")

    female_self = re.search(r"\b(?:i\s+am|i'm|am\s+a)\s+(?:a\s+)?(?:female|girl|woman)\b|\bgender\s*[:=]\s*(?:female|girl|woman)\b|\b(?:female|girl)\s+(?:student|applicant|candidate)\b", text)
    male_self = re.search(r"\b(?:i\s+am|i'm|am\s+a)\s+(?:a\s+)?(?:male|boy|man)\b|\bgender\s*[:=]\s*(?:male|boy|man)\b|\b(?:male|boy)\s+(?:student|applicant|candidate)\b", text)
    if female_self:
        profile.gender = "Female"
    elif male_self:
        profile.gender = "Male"
    elif re.search(r"\b(female|girl|woman)\b", text) and not re.search(r"\b(my|for\s+my)\s+(?:sister|daughter|mother|wife|friend)\b", text):
        profile.gender = "Female"
    elif re.search(r"\b(male|boy|man)\b", text) and not re.search(r"\b(my|for\s+my)\s+(?:brother|son|father|husband|friend)\b", text):
        profile.gender = "Male"

    if re.search(r"\b(disabled|disability|handicapped|divyang|pwd|specially abled|blind|deaf)\b", text):
        profile.disability = True

    name_match = re.search(r"\bmy name is\s+([A-Za-z]+)\b", text)
    if name_match:
        profile.student_name = name_match.group(1).title()

    profile.missing_fields = missing
    return profile


async def parse_student_profile(raw_text: str) -> StudentProfile:
    regex_profile = extract_profile_with_regex(raw_text)
    if not regex_profile.missing_fields or len(raw_text.strip()) < 50:
        return regex_profile
    try:
        llm_profile = await asyncio.wait_for(extract_profile_with_llm(raw_text), timeout=1.5)
        if llm_profile:
            return llm_profile
    except Exception:
        pass
    return regex_profile


async def classify_intent_with_llm(user_text: str) -> Optional[str]:
    system_prompt = (
        "Classify the user intent into exactly ONE label: find_scholarships, audit_document, deadlines, compare, "
        "explain_scheme, concierge_pack, what_if, my_profile, small_talk. Return ONLY the label."
    )
    resp = await call_asi1_chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": mask_sensitive_identifiers(user_text)}],
        temperature=0.1, max_tokens=20, timeout=1.5)
    if resp:
        cleaned = resp.strip().lower()
        for v in ["find_scholarships", "audit_document", "deadlines", "compare", "explain_scheme",
                  "concierge_pack", "what_if", "my_profile", "small_talk"]:
            if v in cleaned:
                return v
    return None


def classify_intent_with_regex(user_text: str) -> str:
    text = user_text.lower().strip()
    if len(text) <= 3 or text in ["a", "b", "c", "hi", "hii", "helo", "yo", "ok", "options", "shuru", "dikhao", "kuch", "help", "menu", "hub"]:
        return "small_talk"
    if re.search(r"\b(audit|verify|check doc|income certificate|caste certificate|marksheet|bonafide|fake|rejection)\b", text):
        return "audit_document"
    if re.search(r"\b(deadline|last date|closing|calendar|ics|reminder|when ends)\b", text):
        return "deadlines"
    if re.search(r"\b(compare|difference between|vs|versus)\b", text):
        return "compare"
    if re.search(r"\b(explain|details of|tell me about scheme|how to apply for)\b", text):
        return "explain_scheme"
    if re.search(r"\b(concierge|pack|sop|essay|apply for me|premium|paid)\b", text):
        return "concierge_pack"
    if re.search(r"\b(what if|what-if|suppose|simulate|if my income was)\b", text):
        return "what_if"
    if re.search(r"\b(my profile|my shortlist|saved|delete my data|my info)\b", text):
        return "my_profile"
    if re.search(r"\b(hi|hello|hey|namaste|pranam|kya haal|good morning|thanks|thank you)\b", text):
        return "small_talk"
    return "find_scholarships"


async def classify_intent(user_text: str) -> str:
    regex_intent = classify_intent_with_regex(user_text)
    if regex_intent != "find_scholarships":
        return regex_intent
    low = user_text.lower().strip()
    if len(low) < 50 or any(k in low for k in ["scholarship", "scheme", "grant", "yojana", "paisa", "fee", "college", "school", "btech", "degree", "eligible", "help", "apply"]):
        return "find_scholarships"
    try:
        intent = await asyncio.wait_for(classify_intent_with_llm(user_text), timeout=1.5)
        if intent:
            return intent
    except Exception:
        pass
    return regex_intent


async def generate_grounded_explanation(scheme: ScholarshipItem, profile: StudentProfile, lang_hindi: bool = False) -> str:
    """2-3 line explanation grounded ONLY in scheme data and what the student actually selected."""
    if scheme.match_status in ["ineligible", "close_miss"]:
        reason_msg = scheme.match_reason or "Does not satisfy the eligibility criteria."
        if lang_hindi:
            return f"Aap filhal is scheme ke liye eligible nahi hain: {reason_msg} Dusri schemes check kar sakte hain."
        return f"You are currently not eligible for {scheme.name}: {reason_msg} Please explore the other schemes."

    inc, mk = income_phrase(profile), marks_phrase(profile)
    prompt = (
        f"Write a concise 2-sentence explanation of why the student qualifies for {scheme.name}.\n"
        f"Facts (use ONLY these): provider {scheme.provider}; benefit {scheme.amount}; required marks >= {scheme.min_marks:g}%; "
        f"income limit {format_inr(scheme.max_family_income)}; student's income {inc}; student's score {mk}; state {profile.state}.\n"
        f"Language: {'Hinglish' if lang_hindi else 'English'}. Do not invent amounts or dates."
    )
    try:
        llm_resp = await asyncio.wait_for(
            call_asi1_chat([{"role": "system", "content": "You are a factual scholarship advisor."},
                            {"role": "user", "content": prompt}], temperature=0.2, max_tokens=150, timeout=3.0),
            timeout=3.0)
        if llm_resp:
            allowed = {int(scheme.amount_value), int(scheme.max_family_income), int(profile.family_income)}
            nums = re.findall(r"₹\s*(\d[\d,]+)", llm_resp)
            if all(int(n.replace(",", "")) in allowed for n in nums):
                return llm_resp.strip()
    except Exception:
        pass

    if lang_hindi:
        return (f"Aapki family income ({inc}) is scheme ki limit ({format_inr(scheme.max_family_income)}) ke andar hai, "
                f"aur aapka score ({mk}) required {scheme.min_marks:g}% cutoff ko pura karta hai. "
                f"Benefit: {scheme.amount}. Official portal: {scheme.portal}.")
    return (f"Your family income ({inc}) is within the {format_inr(scheme.max_family_income)} limit, and your score ({mk}) "
            f"meets the {scheme.min_marks:g}% requirement. Benefit: {scheme.amount}, via {scheme.portal}.")


def draft_application_sop(scheme_name: str, profile: StudentProfile) -> str:
    return (
        f"To The Scholarship Selection Committee,\nSubject: Application for {scheme_name}\n\n"
        f"Respected Committee Members,\n\n"
        f"I, {profile.student_name}, am a dedicated student currently pursuing {profile.course} from {profile.state}. "
        f"My academic score is {marks_phrase(profile)}, and I have consistently prioritised my studies. "
        f"My annual family income is {income_phrase(profile)}, so managing tuition, books and other educational expenses "
        f"is a serious financial challenge for my family.\n\n"
        f"Receiving the {scheme_name} would ease this burden, letting me focus fully on my degree and contribute to society "
        f"after graduation. I promise to maintain academic excellence and honour this scholarship. "
        f"Thank you for considering my application.\n\nYours sincerely,\n{profile.student_name}"
    )


# ==============================================================================
# PAYMENT PROTOCOL HELPERS
# ==============================================================================
PAYMENT_DEMO_MODE = os.getenv("PAYMENT_DEMO_MODE", "true").lower() in ["true", "1", "yes"]
USDC_FUNDS = Funds(currency="USDC", amount="0.01", payment_method="skyfire")
FET_FUNDS = Funds(currency="FET", amount="0.05", payment_method="fet_direct")


def create_concierge_payment_request(recipient_address: str, scheme_name: str, session_id: str, scheme_id: str = "nsp_central_sector") -> RequestPayment:
    return RequestPayment(
        accepted_funds=[USDC_FUNDS, FET_FUNDS],
        recipient=recipient_address,
        deadline_seconds=300,
        reference=f"pay-{session_id[:8]}-{uuid4().hex[:6]}",
        description=f"ScholarBot Concierge Pack for {scheme_name[:40]} (Checklist + Guide + SOP Essay)",
        metadata={"product": "scholarship_concierge_pack", "scheme_id": scheme_id, "session_id": session_id, "mode": "DEMO / TESTNET"},
    )


def verify_transaction_onchain(tx_id: str, currency: str, expected_amount: float) -> Tuple[bool, str]:
    """Verification hook (stub). Rejects malformed hashes; a real ledger query goes here in production."""
    if not tx_id or len(tx_id.strip()) < 16:
        return False, "Transaction ID is malformed or too short."
    if not re.match(r"^(0x)?[0-9a-fA-F]{16,66}$", tx_id.strip()):
        return False, "Transaction ID must be a valid hex hash."
    return True, "Transaction hash accepted by the verification stub."


def handle_payment_commit(commit: CommitPayment, created_timestamp: Optional[float] = None):
    if created_timestamp and (time.time() - created_timestamp) > 300:
        return (False, RejectPayment(reason="Payment request expired (300s timeout)"), "Payment rejected: request expired.")
    if not commit.recipient:
        return (False, RejectPayment(reason="Missing recipient address"), "Payment rejected: no recipient address.")
    tx_id = (commit.transaction_id or "").strip()
    if not tx_id:
        return (False, RejectPayment(reason="Missing transaction ID"), "Payment rejected: missing transaction ID.")
    if commit.funds.currency not in ["USDC", "FET"] and not PAYMENT_DEMO_MODE:
        return (False, RejectPayment(reason=f"Unsupported currency: {commit.funds.currency}"), f"Currency {commit.funds.currency} not accepted.")
    if not PAYMENT_DEMO_MODE:
        amt = float(commit.funds.amount) if commit.funds and commit.funds.amount else 0.0
        ok, reason = verify_transaction_onchain(tx_id, commit.funds.currency, amt)
        if not ok:
            return (False, RejectPayment(reason=f"Verification failed: {reason}"), f"Payment rejected: {reason}")
        mode_label = "[PRODUCTION / LEDGER CHECKED]"
    else:
        mode_label = "[DEMO / TESTNET - transaction not verified on-chain]"
    return (True, CompletePayment(transaction_id=tx_id), f"{mode_label} Payment received. Transaction ID: `{tx_id}`. Preparing your Concierge Pack...")


def generate_concierge_pack(scheme: ScholarshipItem, doc_rules: dict, profile: StudentProfile) -> ConciergePackResponse:
    sop_essay = draft_application_sop(scheme.name, profile)
    ics_text = generate_ics_calendar(scheme.name, scheme.deadline, scheme.portal_url)
    checklist_md = "\n".join(f"- [ ] **{d}**" for d in doc_rules.get("mandatory", []))
    steps_md = "\n".join(doc_rules.get("steps", []))
    tips_md = "\n".join(f"- {t}" for t in doc_rules.get("tips", []))
    status_line = "Unverified - confirm every detail on the official portal" if not scheme.verified else f"Last checked: {scheme.last_verified}"
    md = f"""# 🎓 ScholarBot Application Concierge Pack
**Scheme:** {scheme.name}
**Funding Body:** {scheme.provider}
**Official Portal:** [{scheme.portal}]({scheme.portal_url})
**Application Deadline:** {scheme.deadline}
**Data status:** {status_line}

---

## 👤 1. Applicant Details (as you entered them)
- **Name:** {profile.student_name}
- **Domicile State:** {profile.state}
- **Category:** {profile.category}
- **Course:** {profile.course}
- **Academic Score:** {marks_text(profile)}
- **Annual Family Income:** {income_text(profile)}
- **NPCI DBT:** Single Aadhaar-seeded bank account required

---

## 📋 2. Document Checklist
{checklist_md}

> ⚠️ **Advisory:** {doc_rules.get("warning", "Make sure all documents are current and stamped.")}

---

## 🚀 3. Step-by-Step Portal Workflow
{steps_md}

---

## 💡 4. Anti-Rejection Tips
{tips_md}

---

## ✍️ 5. Draft Statement of Purpose
```text
{sop_essay}
```

---
*Pre-check advisory based on published rules. Always confirm on the official portal.*
"""
    return ConciergePackResponse(
        session_id=str(uuid4()), scheme_id=scheme.id, scheme_name=scheme.name,
        pack_title=f"Concierge Pack: {scheme.name}", markdown_content=md, sop_essay=sop_essay, ics_data=ics_text)

# ==============================================================================
# FORM OPTIONS (value, label) - the label is what the student sees AND what we show back
# ==============================================================================
STATE_OPTIONS: List[Tuple[str, str]] = [
    ("Andaman and Nicobar Islands", "Andaman & Nicobar Islands (UT)"), ("Andhra Pradesh", "Andhra Pradesh"),
    ("Arunachal Pradesh", "Arunachal Pradesh"), ("Assam", "Assam"), ("Bihar", "Bihar"),
    ("Chandigarh", "Chandigarh (UT)"), ("Chhattisgarh", "Chhattisgarh"),
    ("Dadra and Nagar Haveli and Daman and Diu", "Dadra & Nagar Haveli and Daman & Diu (UT)"),
    ("Delhi", "Delhi (NCT)"), ("Goa", "Goa"), ("Gujarat", "Gujarat"), ("Haryana", "Haryana"),
    ("Himachal Pradesh", "Himachal Pradesh"), ("Jammu and Kashmir", "Jammu & Kashmir (UT)"),
    ("Jharkhand", "Jharkhand"), ("Karnataka", "Karnataka"), ("Kerala", "Kerala"), ("Ladakh", "Ladakh (UT)"),
    ("Lakshadweep", "Lakshadweep (UT)"), ("Madhya Pradesh", "Madhya Pradesh"), ("Maharashtra", "Maharashtra"),
    ("Manipur", "Manipur"), ("Meghalaya", "Meghalaya"), ("Mizoram", "Mizoram"), ("Nagaland", "Nagaland"),
    ("Odisha", "Odisha"), ("Puducherry", "Puducherry (UT)"), ("Punjab", "Punjab"), ("Rajasthan", "Rajasthan"),
    ("Sikkim", "Sikkim"), ("Tamil Nadu", "Tamil Nadu"), ("Telangana", "Telangana"), ("Tripura", "Tripura"),
    ("Uttar Pradesh", "Uttar Pradesh"), ("Uttarakhand", "Uttarakhand"), ("West Bengal", "West Bengal"),
    ("All", "Other / not listed (Pan-India schemes only)"),
]
COURSE_OPTIONS: List[Tuple[str, str]] = [
    ("B.Tech / B.E.", "College: Engineering (B.Tech / B.E.)"),
    ("MBBS / BDS / Medical", "College: Medical / Healthcare (MBBS / BDS / Nursing / B.Pharm)"),
    ("B.Sc / BCA / B.Com / BA", "College: General Undergrad (B.Sc / BCA / B.Com / BA / BBA)"),
    ("MBA / M.Tech / M.Sc", "University: Postgraduate (MBA / M.Tech / M.Sc / MCA / MA)"),
    ("Diploma / Polytechnic", "Diploma / Polytechnic / ITI"),
    ("Class 11th - 12th", "School: Class 11th - 12th"),
    ("Class 10th", "School: Class 9th - 10th"),
    ("Law (LLB / LLM)", "Law (BA LLB / BBA LLB / LLB / LLM)"),
    ("PhD / Doctorate", "Doctorate: PhD / Research Scholar"),
]
CATEGORY_OPTIONS: List[Tuple[str, str]] = [
    ("General", "General / Open"), ("EWS", "EWS (Economically Weaker Section)"),
    ("OBC", "OBC (Other Backward Class)"), ("SC", "SC (Scheduled Caste)"), ("ST", "ST (Scheduled Tribe)"),
    ("Minority", "Minority (Muslim / Sikh / Christian / Jain / Buddhist / Parsi)"),
]
GENDER_OPTIONS: List[Tuple[str, str]] = [
    ("Female", "Female (unlocks AICTE Pragati & Kotak Kanya)"), ("Male", "Male"),
    ("Transgender", "Transgender / Third Gender"), ("All", "Prefer not to say"),
]
DISABILITY_OPTIONS: List[Tuple[str, str]] = [
    ("no", "No"), ("yes", "Yes (40% or more benchmark disability - unlocks Saksham)"),
]


def resolve_option(raw: Any, options: List[Tuple[str, str]]) -> str:
    """Accepts either the option value or its label (ASI:One may send either); returns the value or ''."""
    if raw is None:
        return ""
    r = str(raw).strip().lower()
    for value, label in options:
        if r == value.lower() or r == label.lower():
            return value
    return ""


def resolve_band(raw: Any, bands: Dict[str, Tuple[str, str]]) -> str:
    """Returns the band key for a form value / band label / exact number, or '' if it is not a band."""
    if raw is None:
        return ""
    r = str(raw).strip()
    if r in bands:
        return r
    for key, (label, _phrase) in bands.items():
        if r.lower() == label.lower():
            return key
    return ""


def to_number(raw: Any) -> Optional[float]:
    try:
        return float(str(raw).replace(",", "").replace("₹", "").replace("%", "").replace("Rs", "").strip())
    except Exception:
        return None


def _dump(model: Any) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


# ==============================================================================
# INTERACTIVE CARDS (payloads kept strictly inside the documented ASI:One schemas)
# ==============================================================================
def extract_action_payload(user_text: str) -> Tuple[Optional[str], Optional[dict]]:
    """Reads a card tap from the incoming text (plain JSON, fenced JSON, nested 'selection', form 'values')."""
    if not user_text:
        return None, None
    clean = re.sub(r"^@\S+\s*", "", user_text.strip()).strip()
    if clean.startswith("```json"):
        clean = clean[7:].strip()
    elif clean.startswith("```"):
        clean = clean[3:].strip()
    if clean.endswith("```"):
        clean = clean[:-3].strip()

    action_data: Optional[dict] = None
    if "{" in clean and "}" in clean:
        s_idx, e_idx = clean.find("{"), clean.rfind("}")
        if e_idx > s_idx:
            try:
                action_data = json.loads(clean[s_idx:e_idx + 1])
            except Exception:
                pass
    if not isinstance(action_data, dict):
        return None, None

    action_type: Optional[str] = None
    if isinstance(action_data.get("action"), str):
        action_type = action_data["action"]
    elif isinstance(action_data.get("selection"), dict) and "action" in action_data["selection"]:
        action_type = str(action_data["selection"]["action"])
    elif isinstance(action_data.get("selection"), str):
        action_type = str(action_data["selection"])
    elif "values" in action_data or any(f in action_data for f in ["state", "marks", "course", "category", "family_income", "gender", "disability"]):
        action_type = "submit_intake"
    return action_type, action_data


def create_text_chat(text: str) -> ChatMessage:
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(), content=[TextContent(type="text", text=text)])


def create_card_message(narration: str, card_kind: str, payload: dict, is_terminal: bool = False) -> ChatMessage:
    metadata = {
        "card_protocol_version": "1",
        "requires_card_interaction": "false" if is_terminal else "true",
        "card_kind": card_kind,
        "card_payload": json.dumps(payload),
        "preferred_drawer_width_px": "480",
    }
    if is_terminal:
        metadata["is_terminal"] = "true"
    return ChatMessage(
        timestamp=datetime.now(timezone.utc), msg_id=uuid4(),
        content=[TextContent(type="text", text=narration), MetadataContent(type="metadata", metadata=metadata)],
    )


def _cta(label: str, action: str, primary: bool = False, **extra: Any) -> dict:
    sel = {"action": action}
    sel.update(extra)
    cta = {"label": label, "selection": sel}
    if primary:
        cta["primary"] = True
    return cta


BACK_TO_HUB = _cta("🏠 Back to Menu", "back_to_hub")


def get_action_hub_card() -> dict:
    """Six actions, each with its OWN matching icon (no repeated pictures)."""
    def item(key: str, title: str, subtitle: str, secondary: str, badge: Tuple[str, str], cta: dict) -> dict:
        return {
            "id": f"action_{key}", "image": HUB_IMG[key], "title": title, "subtitle": subtitle,
            "secondary_text": secondary, "badges": [{"label": badge[0], "variant": badge[1]}], "primary_cta": cta,
        }
    return {
        "title": "ScholarBot Action Hub",
        "subtitle": "Pick an action to get started",
        "items": [
            item("find", "Find Matching Scholarships", "Central, state and CSR schemes matched to your profile",
                 "Takes about a minute", ("Smart Matching", "success"), _cta("Open Intake Form", "open_intake_form")),
            item("audit", "Anti-Rejection Document Audit", "Pre-check your income / caste certificate or marksheet",
                 "Checks date, income limit, name and stamp", ("Rejection Shield", "warning"), _cta("Audit Document", "open_doc_audit")),
            item("deadlines", "Deadlines & Calendar", "Days left for each scheme, with .ics reminders (7, 3, 1 day)",
                 "Dates are unverified - confirm on the portal", ("Live Countdown", "info"), _cta("View Deadlines", "view_deadlines")),
            item("whatif", "What-If Simulator", "See how a different income or score changes your matches",
                 "Instant re-matching", ("Personal AI", "info"), _cta("Run Simulation", "simulate_what_if")),
            item("concierge", "Application Concierge Pack", "Checklist, portal steps and a draft statement of purpose",
                 "Free preview available", ("0.01 USDC / 0.05 FET", "success"), _cta("Get Concierge Pack", "request_concierge_pack")),
            item("profile", "My Profile", "See or update the details you gave me",
                 "Saved for your next visit", ("Saved", "info"), _cta("Manage Profile", "view_profile")),
        ],
    }


def get_intake_form_card(prefill: Optional[StudentProfile] = None) -> dict:
    def opts(pairs: List[Tuple[str, str]]) -> List[dict]:
        return [{"value": v, "label": l} for v, l in pairs]
    return {
        "title": "Scholarship Eligibility Intake Form",
        "fields": [
            {"name": "state", "kind": "select", "label": "1. Home State / Domicile", "required": True, "options": opts(STATE_OPTIONS)},
            {"name": "course", "kind": "select", "label": "2. Education Level & Course", "required": True, "options": opts(COURSE_OPTIONS)},
            {"name": "category", "kind": "select", "label": "3. Social Category", "required": True, "options": opts(CATEGORY_OPTIONS)},
            {"name": "family_income", "kind": "select", "label": "4. Annual Family Income", "required": True,
             "options": [{"value": k, "label": v[0]} for k, v in INCOME_BANDS.items()]},
            {"name": "marks", "kind": "select", "label": "5. Last Exam Score (% or CGPA)", "required": True,
             "options": [{"value": k, "label": v[0]} for k, v in MARKS_BANDS.items()]},
            {"name": "gender", "kind": "select", "label": "6. Gender", "required": True, "options": opts(GENDER_OPTIONS)},
            {"name": "disability", "kind": "select", "label": "7. Specially Abled (PwD)", "required": True, "options": opts(DISABILITY_OPTIONS)},
        ],
        "submit_cta": {"label": "Review & Match Scholarships", "selection": {"action": "submit_intake"}},
    }


def get_profile_review_card(profile: StudentProfile) -> dict:
    return {
        "title": "Student Profile Verification",
        "summary_rows": [
            {"label": "Home State", "value": profile.state},
            {"label": "Education / Course", "value": profile.course or "Not specified"},
            {"label": "Social Category", "value": profile.category},
            {"label": "Annual Family Income", "value": income_text(profile)},
            {"label": "Academic Score", "value": marks_text(profile)},
            {"label": "Gender", "value": profile.gender},
            {"label": "Disability (PwD)", "value": "Yes (40% or more)" if profile.disability else "No"},
        ],
        "approve_cta": _cta("✅ Confirm & Find Scholarships", "confirm_and_match", primary=True),
        "reject_cta": BACK_TO_HUB,
    }


def get_carousel_card(matched: List[ScholarshipItem], close_misses: Optional[List[ScholarshipItem]] = None) -> dict:
    """Every scholarship card uses the SAME graduation-cap icon."""
    items = []
    for s in matched:
        items.append({
            "id": s.id, "image": SCHOLARSHIP_IMG,
            "title": s.name[:45] + ("..." if len(s.name) > 45 else ""),
            "subtitle": f"{s.provider[:35]} · {s.portal[:25]}",
            "secondary_text": s.amount,
            "badges": [{"label": f"{s.match_score}% Match", "variant": "success"}, {"label": f"Ends {s.deadline}", "variant": "info"}],
            "primary_cta": _cta("View Guide & Checklist", "view_scheme_details", scheme_id=s.id, scheme_name=s.name),
        })
    for cm in (close_misses or [])[:2]:
        items.append({
            "id": cm.id, "image": SCHOLARSHIP_IMG,
            "title": f"[Near Match] {cm.name[:32]}...",
            "subtitle": cm.portal[:40],
            "secondary_text": (cm.match_reason[:60] + "...") if len(cm.match_reason) > 60 else cm.match_reason,
            "badges": [{"label": "Near Match", "variant": "warning"}],
            "primary_cta": _cta("See What You Need", "view_scheme_details", scheme_id=cm.id, scheme_name=cm.name),
        })
    items.append({
        "id": "hub_return", "image": HUB_IMG["home"], "title": "Return to Action Hub",
        "subtitle": "Other tools: deadlines, document audit, what-if",
        "secondary_text": "ScholarBot main menu", "badges": [{"label": "Menu", "variant": "info"}],
        "primary_cta": BACK_TO_HUB,
    })
    return {"title": f"Found {len(matched)} Matching Scholarships",
            "subtitle": "Swipe to compare grants, deadlines and documents", "items": items}


def get_scheme_detail_card(scheme: ScholarshipItem, doc_guidance: dict) -> dict:
    if scheme.match_status == "eligible":
        eligibility = f"Matches your profile ({scheme.match_score}%)"
    elif scheme.match_status == "close_miss":
        eligibility = f"Near match: {scheme.match_reason}"
    else:
        eligibility = f"Not eligible: {scheme.match_reason}"
    rows = [
        {"label": "Scholarship Grant", "value": scheme.amount},
        {"label": "Your Eligibility", "value": eligibility},
        {"label": "Funding Body", "value": scheme.provider},
        {"label": "Official Portal", "value": scheme.portal},
        {"label": "Application Deadline", "value": scheme.deadline},
        {"label": "Direct Portal URL", "value": scheme.portal_url},
        {"label": "Data Status", "value": f"Last checked: {scheme.last_verified}" if scheme.verified else "Unverified, confirm on official portal"},
        {"label": "Mandatory Docs", "value": " • " + " • ".join(doc_guidance.get("mandatory", [])[:4])},
    ]
    return {
        "title": f"Guide: {scheme.name[:50]}",
        "summary_rows": rows,
        "ctas": [
            _cta("📄 Run Pre-Check Document Audit", "audit_for_scheme", primary=True, scheme_id=scheme.id, scheme_name=scheme.name),
            _cta("⚡ Concierge Pack", "request_concierge_pack", scheme_id=scheme.id),
            BACK_TO_HUB,
        ],
    }


def get_audit_result_card(audit: DocumentAuditResponse) -> dict:
    rows = [
        {"label": "Overall Audit Status", "value": f"{audit.overall_status} (Readiness: {audit.readiness_score}/100)"},
        {"label": "Document Type", "value": audit.doc_type.replace("_", " ").title()},
    ]
    icons = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "INFO": "ℹ️"}
    for c in audit.checks:
        rows.append({"label": f"{icons.get(c.status, '•')} {c.check_name}",
                     "value": f"{c.details} Remedy: {c.remedy}" if c.remedy else c.details})
    return {
        "title": f"Document Pre-Check Audit: {audit.overall_status}",
        "summary_rows": rows,
        "approve_cta": _cta("⚡ Get Concierge Pack", "request_concierge_pack", primary=True, scheme_id=audit.scheme_id),
        "reject_cta": BACK_TO_HUB,
    }


def get_deadlines_card(items: List[DeadlineItem]) -> dict:
    rows = [{"label": d.scheme_name[:35] + ("..." if len(d.scheme_name) > 35 else ""),
             "value": f"{d.badge_label} | Deadline: {d.deadline_date}"} for d in items[:6]]
    return {
        "title": "Scholarship Deadlines & Calendar",
        "summary_rows": rows,
        "approve_cta": _cta("📅 Get Calendar (.ics) Reminders", "save_reminders", primary=True),
        "reject_cta": BACK_TO_HUB,
    }


def simple_review_card(title: str, rows: List[Tuple[str, str]], primary: dict) -> dict:
    return {"title": title, "summary_rows": [{"label": l, "value": v} for l, v in rows],
            "approve_cta": primary, "reject_cta": BACK_TO_HUB}


# ==============================================================================
# AGENT
# ==============================================================================
try:
    _loop = asyncio.get_event_loop()
except RuntimeError:
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

hosted_agent = Agent(
    name="scholarbot_agentverse",
    loop=_loop,
    description="ScholarBot: India scholarship matching, anti-rejection document pre-checks and deadline tracking for students.",
    metadata={
        "tags": ["scholarship", "India", "NSP", "document check", "deadlines", "eligibility"],
        "category": "education",
        "author": "Fetch-A-Thon 3.0 ScholarBot Team",
    },
)
chat_proto = Protocol(spec=chat_protocol_spec)
payment_proto = Protocol(spec=payment_protocol_spec, role="seller")

# Hosted agents may reset globals between calls, so everything that matters lives in ctx.storage.
USER_PROFILES: Dict[str, StudentProfile] = {}


def get_or_create_profile(user_address: str, ctx: Optional[Context] = None) -> StudentProfile:
    if ctx is not None and hasattr(ctx, "storage"):
        try:
            stored = ctx.storage.get(f"profile:{user_address}")
            if stored and isinstance(stored, dict):
                USER_PROFILES[user_address] = StudentProfile(**stored)
                return USER_PROFILES[user_address]
        except Exception:
            pass
    if user_address not in USER_PROFILES:
        USER_PROFILES[user_address] = StudentProfile()
    return USER_PROFILES[user_address]


def persist_profile(user_address: str, profile: StudentProfile, ctx: Optional[Context] = None) -> None:
    USER_PROFILES[user_address] = profile
    if ctx is not None and hasattr(ctx, "storage"):
        try:
            ctx.storage.set(f"profile:{user_address}", _dump(profile))
        except Exception as e:
            logger.warning(f"profile not persisted: {e}")


def find_scheme(scheme_id: Optional[str]) -> Optional[dict]:
    for s in load_scholarships():
        if s["id"] == scheme_id:
            return s
    return None


def storage_get(ctx: Context, key: str) -> Any:
    try:
        return ctx.storage.get(key)
    except Exception:
        return None


def storage_set(ctx: Context, key: str, value: Any) -> None:
    try:
        ctx.storage.set(key, value)
    except Exception:
        pass


def profile_summary_line(p: StudentProfile) -> str:
    return f"{p.state} · {p.course or 'course not set'} · {p.category} · {income_text(p)} · score {marks_text(p)}"


async def send_hub(ctx: Context, sender: str, narration: str) -> None:
    await ctx.send(sender, create_card_message(narration, "carousel", get_action_hub_card()))


async def dispatch_action(ctx: Context, sender: str, profile: StudentProfile, action: str, data: Optional[dict], hi: bool) -> bool:
    """Handles one card action. Returns True when the action was handled."""
    data = data or {}

    if action in ("open_hub", "back_to_hub"):
        await send_hub(ctx, sender,
                       "Namaste! 🙏 Main hoon ScholarBot - aapka scholarship advisor. Action Hub se koi bhi option chunein:" if hi else
                       "Welcome! 🎓 I am ScholarBot, your scholarship and document advisor. Pick an action below:")
        return True

    if action == "open_intake_form":
        await ctx.send(sender, create_card_message(
            "Kripya apni details bharein, main published criteria ke hisaab se schemes match karunga:" if hi else
            "Please fill in your details so I can match schemes based on published criteria:",
            "form", get_intake_form_card(profile)))
        return True

    if action == "submit_intake":
        vals = data.get("values") if isinstance(data.get("values"), dict) else data
        state = resolve_option(vals.get("state"), STATE_OPTIONS)
        if state:
            profile.state = state
        course = resolve_option(vals.get("course"), COURSE_OPTIONS)
        if course:
            profile.course = course
        category = resolve_option(vals.get("category"), CATEGORY_OPTIONS)
        if category:
            profile.category = category
            profile.minority = category == "Minority"
        raw_inc = vals.get("family_income")
        if raw_inc not in (None, ""):
            key = resolve_band(raw_inc, INCOME_BANDS)
            num = float(key) if key else to_number(raw_inc)
            if num is not None:
                profile.family_income, profile.income_label = num, key
        raw_marks = vals.get("marks")
        if raw_marks not in (None, ""):
            key = resolve_band(raw_marks, MARKS_BANDS)
            num = float(key) if key else to_number(raw_marks)
            if num is not None:
                profile.marks_percentage, profile.marks_label = num, key
        gender = resolve_option(vals.get("gender"), GENDER_OPTIONS)
        if gender:
            profile.gender = gender
        if "disability" in vals:
            profile.disability = str(vals.get("disability")).strip().lower() in ["yes", "true", "1"] or \
                resolve_option(vals.get("disability"), DISABILITY_OPTIONS) == "yes"
        persist_profile(sender, profile, ctx)
        await ctx.send(sender, create_card_message(
            "Details note kar li gayi hain. Review karke 'Confirm' dabayein:" if hi else
            "Got it! Please check your details below before I match scholarships:",
            "review", get_profile_review_card(profile)))
        return True

    if action == "confirm_and_match":
        if not profile.state or profile.state in ["All", "unknown", ""]:
            await ctx.send(sender, create_card_message(
                "Kripya apna home state chunein taaki state schemes bhi match ho sakein:" if hi else
                "Please choose your home state so state schemes can be matched too:",
                "form", get_intake_form_card(profile)))
            return True
        eligible, close_misses = match_scholarships(profile)
        if not eligible:
            await ctx.send(sender, create_text_chat(
                f"No scholarships matched your profile based on published criteria, but {len(close_misses)} are near matches. "
                f"Type 'menu' to open the Action Hub."))
            return True
        await ctx.send(sender, create_card_message(
            f"🎉 Found {len(eligible)} scholarships that match your profile (based on published criteria - confirm on the official portal).\n"
            f"📌 Your details: {profile_summary_line(profile)}\n\nSwipe the cards to see grants, deadlines and required documents:",
            "carousel", get_carousel_card(eligible, close_misses)))
        return True

    if action == "back_to_list":
        if profile.state and profile.state != "All":
            eligible, close_misses = match_scholarships(profile)
            if eligible:
                await ctx.send(sender, create_card_message("Back to your results:", "carousel", get_carousel_card(eligible, close_misses)))
                return True
        return await dispatch_action(ctx, sender, profile, "open_hub", None, hi)

    if action in ("open_doc_audit", "audit_for_scheme"):
        scheme_id = data.get("scheme_id") or storage_get(ctx, f"active_audit_scheme:{sender}") or "nsp_central_sector"
        storage_set(ctx, f"active_audit_scheme:{sender}", scheme_id)
        scheme = find_scheme(scheme_id)
        scheme_name = scheme["name"] if scheme else scheme_id
        card = simple_review_card("Anti-Rejection Document Audit", [
            ("Target Scheme", scheme_name),
            ("Supported Documents", "Income certificate, caste certificate, marksheet"),
            ("Next Step", "Paste the certificate text into the chat"),
        ], _cta("🔍 Find Scholarships Instead", "open_intake_form", primary=True))
        await ctx.send(sender, create_card_message(
            f"📄 **Document pre-check for: {scheme_name}**\n\nPaste the text of your certificate here in the chat. I check:\n"
            "1. Issue date vs the scheme's validity rule\n2. Income vs the scheme's ceiling\n3. Name match\n4. Issuing officer / stamp\n\n"
            "*Aadhaar, PAN and phone numbers are masked automatically. Please do not paste real ID numbers anyway.*",
            "review", card))
        return True

    if action == "view_deadlines":
        items = build_deadline_items(load_scholarships())
        await ctx.send(sender, create_card_message(
            "📅 **Scholarship deadlines (days counted from today).**\nDates come from our unverified dataset, so confirm every date on the official portal:",
            "review", get_deadlines_card(items)))
        return True

    if action == "save_reminders":
        pool = load_scholarships()
        if profile.state and profile.state != "All":
            eligible, _ = match_scholarships(profile)
            if eligible:
                ids = {e.id for e in eligible}
                pool = [s for s in pool if s["id"] in ids]
        open_items = [d for d in build_deadline_items(pool) if d.days_remaining >= 0][:3]
        if not open_items:
            await ctx.send(sender, create_text_chat("No open deadlines found right now. Type 'menu' to go back."))
            return True
        blocks = "\n\n".join(f"**{d.scheme_name}** (deadline {d.deadline_date}, {d.days_remaining} days left)\n```\n{d.ics_calendar_data}```" for d in open_items)
        storage_set(ctx, f"reminder_schemes:{sender}", [d.scheme_id for d in open_items])
        await ctx.send(sender, create_text_chat(
            "📅 Calendar reminders for your 3 nearest deadlines. Copy a block into a text file named `deadline.ics` and open it with "
            "Google Calendar / Outlook (alerts at 7, 3 and 1 day before). This build does not push notifications by itself.\n\n" + blocks +
            "\n\nType 'menu' to return to the Action Hub."))
        return True

    if action == "view_scheme_details":
        scheme_id = data.get("scheme_id")
        selected = find_scheme(scheme_id) or load_scholarships()[0]
        status, score, reason = evaluate_scheme(selected, profile)
        sc_item = scheme_to_item(selected, status, score, reason)
        storage_set(ctx, f"active_audit_scheme:{sender}", selected["id"])
        doc_rule = DOC_RULES_DB.get(selected["id"], DOC_RULES_DB.get("default", {}))
        explanation = await generate_grounded_explanation(sc_item, profile, hi)
        await ctx.send(sender, create_card_message(
            f"📋 **{sc_item.name}**\n\n{explanation}\n\nComplete the document pre-check before applying on the official portal.",
            "detail", get_scheme_detail_card(sc_item, doc_rule)))
        return True

    if action == "simulate_what_if":
        def variant(**changes: Any) -> int:
            base = _dump(profile)
            base.update(changes)
            base["income_label"] = base.get("income_label", "") if "family_income" not in changes else ""
            base["marks_label"] = base.get("marks_label", "") if "marks_percentage" not in changes else ""
            return len(match_scholarships(StudentProfile(**base))[0])
        current = len(match_scholarships(profile)[0]) if (profile.state and profile.state != "All") else 0
        n_bpl, n_low, n_merit = variant(family_income=90000.0), variant(family_income=240000.0), variant(marks_percentage=85.0)
        card = simple_review_card("What-If Eligibility Simulator", [
            ("Your profile", f"Income {income_text(profile)} | Score {marks_text(profile)}"),
            ("Now", f"{current} matching schemes"),
            ("If income is below ₹1.0 lakh", f"{n_bpl} matching schemes"),
            ("If income is ₹2.4 lakh", f"{n_low} matching schemes"),
            ("If score is 85% or more", f"{n_merit} matching schemes"),
        ], _cta("✏️ Change My Details", "open_intake_form", primary=True))
        note = "" if current else "\n(Set your home state first for accurate numbers.)"
        await ctx.send(sender, create_card_message(
            "🔮 **What-if simulation** - how many schemes match if one detail changes (all other details stay the same):" + note,
            "review", card))
        return True

    if action in ("request_concierge_pack", "preview_concierge_pack"):
        scheme_id = data.get("scheme_id") or storage_get(ctx, f"active_audit_scheme:{sender}")
        scheme = find_scheme(scheme_id)
        scheme_name = scheme["name"] if scheme else "your chosen scholarship (pick one from the results first)"
        if action == "request_concierge_pack":
            card = simple_review_card("Application Concierge Pack", [
                ("Scholarship", scheme_name),
                ("Section 1", f"Applicant details: {profile.state} · {profile.course or 'course not set'}"),
                ("Section 2", "Document checklist for this scheme"),
                ("Section 3", "Step-by-step portal workflow"),
                ("Section 4", "Draft statement of purpose"),
                ("Price", "0.01 USDC / 0.05 FET (demo mode) - free preview available"),
            ], _cta("📄 View Free Preview", "preview_concierge_pack", primary=True, scheme_id=scheme["id"] if scheme else ""))
            await ctx.send(sender, create_card_message(
                "⚡ **Application Concierge Pack**\nThe paid flow uses the Fetch.ai Payment Protocol and currently runs in DEMO / TESTNET mode. "
                "Tap 'View Free Preview' to see a preview now:", "review", card))
            return True
        if not scheme:
            await ctx.send(sender, create_text_chat("Please open a scholarship from the results first, then tap Concierge Pack. Type 'menu' for the Action Hub."))
            return True
        rule = DOC_RULES_DB.get(scheme["id"], DOC_RULES_DB.get("default", {}))
        docs = "\n".join(f"{i}. {d}" for i, d in enumerate(rule.get("mandatory", [])[:4], 1))
        card = simple_review_card("Concierge Pack Preview", [
            ("Scholarship", scheme["name"]),
            ("Applicant", f"{profile.state} · {profile.course or 'course not set'}"),
            ("Category & Income", f"{profile.category} · {income_text(profile)}"),
            ("Key warning", rule.get("warning", "Confirm all details on the official portal.")[:160]),
        ], _cta("🔍 Find More Scholarships", "open_intake_form", primary=True))
        await ctx.send(sender, create_card_message(
            f"📄 **Free preview - {scheme['name']}**\n\n### Draft statement of purpose\n{draft_application_sop(scheme['name'], profile)}\n\n"
            f"### First documents to prepare\n{docs}\n\n*Data for this scheme is unverified - confirm on the official portal.*",
            "review", card))
        return True

    if action == "view_profile":
        card = simple_review_card("My Saved Profile", [
            ("Home State", profile.state or "Not specified"),
            ("Education / Course", profile.course or "Not specified"),
            ("Social Category", profile.category or "General"),
            ("Annual Family Income", income_text(profile)),
            ("Academic Score", marks_text(profile)),
            ("Gender", profile.gender or "All"),
            ("Specially Abled (PwD)", "Yes (40% or more)" if profile.disability else "No"),
        ], _cta("✏️ Update Profile", "open_intake_form", primary=True))
        await ctx.send(sender, create_card_message(f"👤 **Your saved profile**\n{profile_summary_line(profile)}", "review", card))
        return True

    if action == "done":
        await ctx.send(sender, create_text_chat("Best of luck with your applications! Type 'Hi' anytime to reopen ScholarBot."))
        return True

    return False


@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    try:
        await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))

        has_start = has_end = False
        resource_uri: Optional[str] = None
        for item in getattr(msg, "content", None) or []:
            if isinstance(item, StartSessionContent):
                has_start = True
            elif isinstance(item, EndSessionContent):
                has_end = True
            elif isinstance(item, ResourceContent):
                resource_uri = str(getattr(item, "uri", "") or "uploaded-file")

        if has_end:
            await ctx.send(sender, create_text_chat("Session ended. Type 'Hi' anytime to restart ScholarBot."))
            return

        user_text = msg.text().strip()
        if has_start and not user_text:
            await send_hub(ctx, sender, "Welcome to ScholarBot! 🎓 Pick an action below:")
            return
        if resource_uri and not user_text:
            await ctx.send(sender, create_text_chat(
                "I received your file, but this version cannot read images or PDFs yet. Please paste the certificate text into the chat instead."))
            return

        ctx.logger.info(f"[Hosted] message from {sender[:14]}...: length={len(user_text)}")  # never log the text itself
        user_text = mask_sensitive_identifiers(user_text)
        clean_text = re.sub(r"^@\S+\s*", "", user_text).strip()
        if clean_text:
            user_text = clean_text

        hi = is_hindi_or_hinglish(user_text)
        profile = get_or_create_profile(sender, ctx)
        action, data = extract_action_payload(user_text)

        low = user_text.lower().strip()
        greeting = bool(re.search(r"^(hi+|hello+|hey+|namaste|pranam|kya haal|good morning|start|restart|menu|hub|help|home)(\b|[^\w]|$)", low))
        short = len(low) <= 3 or low in ["back_to_hub", "back_to_menu", "new_search", "options", "shuru", "dikhao"]
        if not action:
            if greeting or short:
                action = "open_hub"
            elif low in ["done", "exit", "bye", "thank you", "thanks"]:
                action = "done"

        if action and await dispatch_action(ctx, sender, profile, action, data, hi):
            return

        # Pasted certificate text -> audit
        doc_keywords = ["certificate", "tehsildar", "annual income", "praman patra", "revenue", "validity", "marksheet", "father", "son of", "bonafide"]
        if len(user_text) > 30 and any(k in user_text.lower() for k in doc_keywords):
            target = storage_get(ctx, f"active_audit_scheme:{sender}") or "nsp_central_sector"
            req = DocumentAuditRequest(session_id=str(uuid4()), scheme_id=target, doc_type="income_certificate",
                                       doc_text=user_text, profile=profile)
            res = audit_document_compliance(req, scheme_income_cap=get_scheme_income_cap(target) or 250000.0)
            await ctx.send(sender, create_card_message(
                f"📄 **Document pre-check complete: {res.overall_status} ({res.readiness_score}/100)**",
                "review", get_audit_result_card(res)))
            return

        intent = await classify_intent(user_text)
        mapped = {"what_if": "simulate_what_if", "concierge_pack": "request_concierge_pack", "my_profile": "view_profile",
                  "deadlines": "view_deadlines"}.get(intent)
        if mapped and await dispatch_action(ctx, sender, profile, mapped, None, hi):
            return
        if intent == "small_talk":
            await send_hub(ctx, sender, "Hello! 🎓 I match scholarships to your profile, pre-check your documents and track deadlines. "
                                        "Pick an action below or describe your situation:")
            return
        if intent == "audit_document":
            await ctx.send(sender, create_text_chat("Please paste the text of your certificate (income, caste or marksheet). I will check its date, income limit, name and stamp."))
            return
        if intent in ("compare", "explain_scheme"):
            await send_hub(ctx, sender, "Open a scholarship from the search results to see its full details and compare it. Start from the Action Hub:")
            return

        # Free-text profile
        ext = await parse_student_profile(user_text)
        miss = set(ext.missing_fields)
        if ext.state != "All":
            profile.state = ext.state
        if "social_category" not in miss:
            profile.category = ext.category
            profile.minority = ext.minority
        if "family_income" not in miss:
            profile.family_income, profile.income_label = ext.family_income, ""
        if "academic_marks" not in miss:
            profile.marks_percentage, profile.marks_label = ext.marks_percentage, ""
        if ext.course:
            profile.course = ext.course
        if ext.gender != "All":
            profile.gender = ext.gender
        if ext.disability:
            profile.disability = True
        persist_profile(sender, profile, ctx)

        names = {"home_state": "home state", "social_category": "social category", "family_income": "family income",
                 "academic_marks": "last exam score", "course": "course"}
        still_missing = [names[m] for m in ext.missing_fields if m in names]
        if still_missing:
            await ctx.send(sender, create_card_message(
                f"I understood part of your details. Still missing: {', '.join(still_missing)}. Please complete the form:",
                "form", get_intake_form_card(profile)))
            return
        await ctx.send(sender, create_card_message(
            f"Great! I understood: **{profile_summary_line(profile)}**. Please verify and confirm to see matching scholarships:",
            "review", get_profile_review_card(profile)))

    except Exception as e:  # global guard: the student always gets a reply and the menu
        ctx.logger.error(f"[Hosted Error] {type(e).__name__}: {e}")
        try:
            await send_hub(ctx, sender, "Something went wrong while processing that. Please use the Action Hub below to continue:")
        except Exception:
            pass


@chat_proto.on_message(ChatAcknowledgement)
async def handle_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.debug(f"[Hosted] ACK from {sender[:14]}... for {msg.acknowledged_msg_id}")


@payment_proto.on_message(CommitPayment)
async def handle_payment_commit_msg(ctx: Context, sender: str, msg: CommitPayment):
    ctx.logger.info(f"[Hosted Payment] CommitPayment from {sender[:14]}...")
    success, reply, text_msg = handle_payment_commit(msg)
    await ctx.send(sender, reply)
    if success:
        profile = get_or_create_profile(sender, ctx)
        selected = find_scheme(storage_get(ctx, f"active_audit_scheme:{sender}")) or load_scholarships()[0]
        item = scheme_to_item(selected)
        pack = generate_concierge_pack(item, DOC_RULES_DB.get(selected["id"], DOC_RULES_DB.get("default", {})), profile)
        await ctx.send(sender, create_text_chat(f"{text_msg}\n\n{pack.markdown_content}"))


@payment_proto.on_message(RejectPayment)
async def handle_payment_reject(ctx: Context, sender: str, msg: RejectPayment):
    ctx.logger.info(f"[Hosted Payment] rejected by {sender[:14]}...: {msg.reason}")
    await ctx.send(sender, create_text_chat("Payment cancelled. Scholarship search, checklists and the free preview stay fully available!"))


hosted_agent.include(chat_proto, publish_manifest=True)
hosted_agent.include(payment_proto, publish_manifest=True)

agent = hosted_agent  # Agentverse picks up `agent`

if __name__ == "__main__":
    hosted_agent.run()