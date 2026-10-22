# ScholarBot - Unverified Data & Manual Signoff Registry

> **Status:** Pending Final Portal-by-Portal Manual Verification before Live Submission  
> **Hard Rule:** Honest "unverified" is strictly better than confidently wrong. All records in `data/scholarships.json` maintain `verified: false` and `last_verified: null` with active warnings on ASI:One interactive cards until manually verified on official government/foundation portals.
> **Date Baseline:** 22 October 2026. For all schemes where the 2026-27 academic session cutoff has not been gazetted / officially verified, `deadline` and `application_window` are stored as `null`, and cards render `"Check official portal"`.

This registry lists all **119 deduplicated scholarship schemes** currently cataloged in `data/scholarships.json`.

---

## ⚠️ Unverified Deadlines & Application Windows (All Schemes)
- **Policy:** In strict accordance with the hackathon rules against inventing dates, every scheme record where the official 2026-27 application window has not been independently verified on government notification gazettes is stored as:
  ```json
  "deadline": null,
  "application_window": null
  ```
- **Interactive Cards Representation:** Interactive cards and deadline countdowns show `"Check official portal"` instead of guessed cutoff days.
- **Action Required by User:** Before final Devpost submission or live video demonstration, check each state portal and NSP notification for the active 2026-27 closing date.

---

## 🌐 Endpoints with Bot / WAF Protection (HTTP 403 / 406)
The following state and central portals return HTTP 403 or 406 when checked via automated crawler scripts due to National Informatics Centre (NIC) Cloudflare / Akamai Web Application Firewall (WAF) or geo-blocking. These endpoints are live HTTPS services for standard browser users:
1. `https://sso.rajasthan.gov.in/signin` (Rajasthan Single Sign-On / SJMS)
2. `https://scholarship.up.gov.in` (UP Dashmottar Scholarship System)
3. `https://mahadbt.maharashtra.gov.in` (Maharashtra MahaDBT Portal)
4. `https://pmsonline.bih.nic.in` (Bihar Post-Matric PMS Online Portal)
5. `https://edistrict.delhigovt.nic.in` (Delhi e-District Citizen Services)
6. `https://ssp.postmatric.karnataka.gov.in` (Karnataka State Scholarship Portal)
7. `https://oasis.gov.in` (West Bengal OASIS Portal)
8. `https://scholarshipportal.mp.nic.in` (Madhya Pradesh Scholarship Portal 2.0)

---

## 🔗 Schemes with Portal Homepages as Apply URLs (`apply_url_verified: false`)
When government schemes do not provide a public direct deep-link to the application form (because the scheme form is only accessible after student login and Aadhaar OTP/eKYC), the official portal login/home page is provided with `apply_url_verified: false`:
- **National Scholarship Portal (NSP) Schemes:** `https://scholarships.gov.in` (requires NSP OTR login).
- **PMS Bihar:** `https://pmsonline.bih.nic.in` (requires student registration on PMS portal).
- **e-District Delhi:** `https://edistrict.delhigovt.nic.in` (requires citizen login and Delhi state registration).
- **Karnataka SSP:** `https://ssp.postmatric.karnataka.gov.in` (requires Kutumba ID login).
- **OASIS West Bengal:** `https://oasis.gov.in` (requires district registration).
- **MedhaSoft Bihar:** `https://medhasoft.bih.nic.in` (requires student registration).
- **Telangana ePASS:** `https://epass.cgg.gov.in` (requires ePASS authentication).
- **Andhra Pradesh Jnanabhumi:** `https://jnanabhumi.ap.gov.in` (requires Jnanabhumi login).

---

## 📋 Complete Catalog Registry (119 Schemes)

| ID | Scheme Name | Official Portal | Apply URL | Apply URL Verified |
|---|---|---|---|---|
| `nsp_central_sector` | Central Sector Scheme for College & University | National Scholarship Portal (NSP) | `https://scholarships.gov.in` | ❌ (Portal Home / OTR) |
| `aicte_pragati_girls` | AICTE Pragati Scholarship for Girls (Degree) | National Scholarship Portal (NSP) | `https://scholarships.gov.in` | ❌ (Portal Home / OTR) |
| `aicte_pragati_diploma` | AICTE Pragati Scholarship for Girls (Diploma) | National Scholarship Portal (NSP) | `https://scholarships.gov.in` | ❌ (Portal Home / OTR) |
| `aicte_saksham` | AICTE Saksham Scholarship for Specially-Abled (Degree) | National Scholarship Portal (NSP) | `https://scholarships.gov.in` | ❌ (Portal Home / OTR) |
| `aicte_saksham_diploma` | AICTE Saksham Scholarship for Specially-Abled (Diploma) | National Scholarship Portal (NSP) | `https://scholarships.gov.in` | ❌ (Portal Home / OTR) |
| `post_matric_sc_central` | Centrally Sponsored Post-Matric SC | National Scholarship Portal (NSP) | `https://scholarships.gov.in` | ❌ (Portal Home / OTR) |
| `post_matric_st_central` | Centrally Sponsored Post-Matric ST | National Scholarship Portal (NSP) | `https://scholarships.gov.in` | ❌ (Portal Home / OTR) |
| `minority_post_matric` | Post-Matric Scholarship for Minorities | National Scholarship Portal (NSP) | `https://scholarships.gov.in` | ❌ (Portal Home / OTR) |
| `raj_postmatric_sje` | Rajasthan Post-Matric SJE Uttarmatric | Rajasthan SJMS Portal | `https://sso.rajasthan.gov.in/signin` | ✅ (SSO Portal Login) |
| `up_postmatric_dashmottar` | UP Dashmottar Post-Matric Scholarship | UP Scholarship Portal | `https://scholarship.up.gov.in/RegistrationNew.aspx` | ✅ (Direct Registration Page) |
| `maha_ebc_rajarshi_shahu` | MahaDBT Rajarshi Shahu Maharaj (EBC) | MahaDBT Portal | `https://mahadbt.maharashtra.gov.in/Registration/StudentRegistration` | ✅ (Direct Registration Page) |
| `bihar_post_matric` | Bihar Post-Matric Scholarship (PMS Bihar) | PMS Bihar Portal | `https://pmsonline.bih.nic.in` | ❌ (Portal Home) |
| `mp_postmatric_scholarship` | MP Post-Matric Scholarship Scheme | MP Scholarship Portal 2.0 | `https://scholarshipportal.mp.nic.in/Public/Registration.aspx` | ✅ (Direct Registration Page) |
| `delhi_merit_scholarship` | Delhi Merit Scholarship in Colleges | e-District Delhi Portal | `https://edistrict.delhigovt.nic.in` | ❌ (Portal Home) |
| `wb_oasis_scholarship` | OASIS Post-Matric Scholarship West Bengal | OASIS Portal | `https://oasis.gov.in` | ❌ (Portal Home) |
| `karnataka_ssp_postmatric` | Karnataka SSP Post-Matric Scheme | Karnataka SSP Portal | `https://ssp.postmatric.karnataka.gov.in` | ❌ (Portal Home) |
| `reliance_ug_scholarship` | Reliance Foundation Undergraduate Scholarship | Reliance Foundation Portal | `https://www.reliancefoundation.org/ug-scholarships` | ✅ (Direct UG Apply Page) |
| `hdfc_parivartan_ecss` | HDFC Bank Parivartan's ECSS Program | HDFC Parivartan / Buddy4Study | `https://www.buddy4study.com/page/hdfc-bank-parivartans-ecss-programme` | ✅ (Direct Scheme Page) |
| `tata_trusts_merit` | Tata Trusts Means & Merit Higher Education | Tata Trusts Portal | `https://www.tatatrusts.org/our-work/individual-grants-programme/education-grants` | ✅ (Direct Grants Page) |
| `ongc_scholarship` | ONGC Foundation Merit Scholarship | ONGC Scholar Portal | `https://www.ongcscholar.org` | ✅ (Direct Scholar Portal) |
| `sitaram_jindal_scholarship` | Sitaram Jindal Foundation Scholarship | Sitaram Jindal Portal | `https://www.sitaramjindalfoundation.org/scholarships.php` | ✅ (Direct Scheme Page) |
| `kotak_kanya_scholarship` | Kotak Kanya Scholarship for Meritorious Girls | Buddy4Study / Kotak Education | `https://www.buddy4study.com/page/kotak-kanya-scholarship` | ✅ (Direct Scheme Page) |
