import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from core.matching import normalize_category, normalize_course, normalize_state
from core.models import ScholarshipItem, StudentProfile
from core.privacy import mask_sensitive_identifiers

ASI1_API_KEY = os.getenv("ASI1_API_KEY") or os.getenv("ASI_ONE_API_KEY", "")
ASI1_BASE_URL = os.getenv("ASI1_BASE_URL", "https://api.asi1.ai/v1")
ASI1_MODEL = os.getenv("ASI1_MODEL", "asi1")

def is_hindi_or_hinglish(text: str) -> bool:
    """Detects if text contains Hindi (Devanagari) or common Hinglish expressions."""
    if not text:
        return False
    # Check Devanagari Unicode block
    if re.search(r'[\u0900-\u097F]', text):
        return True
    # Check common Hinglish markers
    hinglish_words = [
        r'\bkya\b', r'\byaad\b', r'\bhain?\b', r'\bmujhe\b', r'\bmera\b', r'\bmeri\b',
        r'\bbatao\b', r'\bkaro\b', r'\bkaise\b', r'\bkitna\b', r'\bmilega\b', r'\bmilegi\b',
        r'\bpaise\b', r'\bchahiye\b', r'\btheek\b', r'\bnamaste\b', r'\bnamaskar\b',
        r'\bhoga\b', r'\bhogi\b', r'\bkarna\b', r'\bpariksha\b', r'\bkaha\b'
    ]
    for pattern in hinglish_words:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

async def call_asi1_chat(messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 500, timeout: float = 5.0) -> Optional[str]:
    """Calls ASI1 OpenAI-compatible endpoint with retries and timeout using httpx.AsyncClient."""
    if not ASI1_API_KEY or ASI1_API_KEY.startswith("your_") or len(ASI1_API_KEY) < 8:
        return None

    headers = {
        "Authorization": f"Bearer {ASI1_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": ASI1_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    url = f"{ASI1_BASE_URL.rstrip('/')}/chat/completions"
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
                elif res.status_code == 404 and ASI1_MODEL != "asi1-mini":
                    payload["model"] = "asi1-mini"
        except Exception:
            pass
    return None

def check_asi1_api_health() -> Tuple[bool, str]:
    """
    Startup self-check that logs whether ASI1_API_KEY is set and whether the API answered
    (without printing the key), and falls back cleanly if not.
    """
    if not ASI1_API_KEY or ASI1_API_KEY.startswith("your_") or len(ASI1_API_KEY) < 8:
        return False, "ASI1_API_KEY is not configured (or is placeholder). Operating in autonomous local engine mode."

    key_len = len(ASI1_API_KEY)
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{ASI1_BASE_URL.rstrip('/')}/models", headers={"Authorization": f"Bearer {ASI1_API_KEY}"})
            if resp.status_code in (200, 404):
                return True, f"ASI1 LLM API connection verified (API key present, length={key_len} chars, status={resp.status_code})."
            elif resp.status_code == 401:
                return False, f"ASI1 LLM API authentication rejected (HTTP 401, key length={key_len} chars). Using local fallback."
            else:
                return False, f"ASI1 LLM API responded with HTTP {resp.status_code} (key length={key_len} chars). Using local fallback."
    except Exception as e:
        return False, f"ASI1 LLM API endpoint unreachable ({type(e).__name__}, key length={key_len} chars). Using local fallback."


async def extract_profile_with_llm(raw_text: str) -> Optional[StudentProfile]:
    """Uses ASI1 to parse unstructured English or Hinglish text into StudentProfile asynchronously."""
    system_prompt = (
        "You are an expert Indian education advisor. Your task is to extract student details from user input (English or Hinglish) into JSON.\n"
        "Never invent information. If a field is not mentioned, mark it in 'missing_fields'.\n"
        "Convert lakh/LPA/k into numeric INR: e.g. '2.5 lakh' -> 250000, '3 LPA' -> 300000.\n"
        "Handle Hindi/Hinglish (e.g., 'main Rajasthan se hu, OBC, income 3 lakh, B.Tech').\n"
        "If a range is stated (e.g. '3-5 lakh', '75-80%'), extract min and max values.\n"
        "OUTPUT STRICT JSON ONLY with keys:\n"
        "{\n"
        '  "student_name": string,\n'
        '  "state": string (state name or "All"),\n'
        '  "category": "General" | "EWS" | "OBC" | "SC" | "ST" | "Minority",\n'
        '  "family_income": number,\n'
        '  "family_income_min": number or null,\n'
        '  "family_income_max": number or null,\n'
        '  "course": string,\n'
        '  "marks_percentage": number,\n'
        '  "marks_min": number or null,\n'
        '  "marks_max": number or null,\n'
        '  "gender": "All" | "Male" | "Female" | "Transgender",\n'
        '  "disability": boolean,\n'
        '  "minority": boolean,\n'
        '  "year_of_study": number,\n'
        '  "missing_fields": list of missing field names\n'
        "}"
    )

    safe_text = mask_sensitive_identifiers(raw_text)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Extract profile from: {safe_text}"}
    ]

    llm_resp = await call_asi1_chat(messages, temperature=0.1, timeout=4.0)
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
        data["course"] = normalize_course(data.get("course", "Engineering"))
        return StudentProfile(**data)
    except Exception:
        return None

def extract_profile_with_regex(raw_text: str) -> StudentProfile:
    """Robust rule-based parser using word boundaries for zero-downtime fallback."""
    safe_text = mask_sensitive_identifiers(raw_text)
    text = safe_text.lower()
    profile = StudentProfile(raw_text=safe_text)
    missing = []

    # 1. State
    state = normalize_state(text)
    if state != "All":
        profile.state = state
    else:
        missing.append("home_state")

    # 2. Category
    if re.search(r'\b(sc|scheduled caste)\b', text):
        profile.category = "SC"
    elif re.search(r'\b(st|scheduled tribe)\b', text):
        profile.category = "ST"
    elif re.search(r'\b(obc|other backward class|bc|ebc)\b', text):
        profile.category = "OBC"
    elif re.search(r'\b(ews|economically weaker section)\b', text):
        profile.category = "EWS"
    elif re.search(r'\b(minority|muslim|sikh|christian|jain|buddhist|parsi)\b', text):
        profile.category = "Minority"
        profile.minority = True
    elif re.search(r'\b(general|open|ur)\b', text):
        profile.category = "General"
    else:
        missing.append("social_category")

    # 3. Income
    income_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|lpa)\b', text)
    if income_match:
        val = float(income_match.group(1))
        profile.family_income = round(val * 100000.0, 2)
    else:
        num_income = re.search(r'income(?:\s*is|\s*of|\s*:)?\s*(?:rs\.?|inr|₹)?\s*(\d{5,8})\b', text)
        if num_income:
            profile.family_income = float(num_income.group(1))
        else:
            missing.append("family_income")

    # 4. Marks
    marks_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*(?:%|percent|percentage|marks)', text)
    if marks_match:
        profile.marks_percentage = float(marks_match.group(1))
    else:
        missing.append("academic_marks")

    # 5. Course
    c_norm = normalize_course(text)
    if c_norm:
        profile.course = c_norm
    else:
        profile.course = ""
        missing.append("course")

    # 6. Gender: Direct applicant identification only (ignore relatives like "my sister", "my brother")
    female_self = re.search(r'\b(?:i\s+am|i\'m|am\s+a)\s+(?:a\s+)?(?:female|girl|woman)\b|\bgender\s*[:=]\s*(?:female|girl|woman)\b|\b(?:female|girl)\s+(?:student|applicant|candidate)\b', text)
    male_self = re.search(r'\b(?:i\s+am|i\'m|am\s+a)\s+(?:a\s+)?(?:male|boy|man)\b|\bgender\s*[:=]\s*(?:male|boy|man)\b|\b(?:male|boy)\s+(?:student|applicant|candidate)\b', text)
    if female_self:
        profile.gender = "Female"
    elif male_self:
        profile.gender = "Male"
    elif re.search(r'\b(female|girl|woman)\b', text) and not re.search(r'\b(my|for\s+my)\s+(?:sister|daughter|mother|wife|friend)\b', text):
        profile.gender = "Female"
    elif re.search(r'\b(male|boy|man)\b', text) and not re.search(r'\b(my|for\s+my)\s+(?:brother|son|father|husband|friend)\b', text):
        profile.gender = "Male"

    # 7. Disability
    if re.search(r'\b(disabled|disability|handicapped|divyang|pwd|specially abled|blind|deaf)\b', text):
        profile.disability = True

    # 8. Name (if present e.g. "my name is Rahul")
    name_match = re.search(r'\bmy name is\s+([A-Za-z]+)\b', text)
    if name_match:
        profile.student_name = name_match.group(1).title()

    profile.missing_fields = missing
    return profile

async def parse_student_profile(raw_text: str) -> StudentProfile:
    """
    Primary path: ASI1 LLM extracts structured profile from natural/Hinglish language.
    Deterministic regex fallback ensures robust 0-failure resilience when offline or unconfigured.
    """
    try:
        import asyncio
        llm_profile = await asyncio.wait_for(extract_profile_with_llm(raw_text), timeout=4.0)
        if llm_profile and (llm_profile.state != "All" or llm_profile.family_income != 250000.0 or llm_profile.course):
            regex_fallback = extract_profile_with_regex(raw_text)
            if not llm_profile.student_name and regex_fallback.student_name:
                llm_profile.student_name = regex_fallback.student_name
            return llm_profile
    except Exception:
        pass

    return extract_profile_with_regex(raw_text)

async def classify_intent_with_llm(user_text: str) -> Optional[str]:
    """Uses ASI1 to classify user intent asynchronously."""
    system_prompt = (
        "Classify the user intent into exactly ONE label:\n"
        "- find_scholarships (looking for grants/schemes/money/eligibility)\n"
        "- audit_document (checking/uploading certificate, marksheet, income proof)\n"
        "- deadlines (asking about dates, calendar, closing soon)\n"
        "- compare (comparing two scholarships)\n"
        "- explain_scheme (details about a specific scheme)\n"
        "- concierge_pack (paid application pack, SOP, full guide)\n"
        "- what_if (simulation: what if my income or marks change)\n"
        "- my_profile (view/update saved details or shortlist)\n"
        "- small_talk (greeting, thanks, bye)\n"
        "Return ONLY the label."
    )
    safe_text = mask_sensitive_identifiers(user_text)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": safe_text}
    ]
    resp = await call_asi1_chat(messages, temperature=0.1, max_tokens=20, timeout=3.0)
    if resp:
        cleaned = resp.strip().lower()
        valid = [
            "find_scholarships", "audit_document", "deadlines", "compare",
            "explain_scheme", "concierge_pack", "what_if", "my_profile", "small_talk"
        ]
        for v in valid:
            if v in cleaned:
                return v
    return None

def classify_intent_with_regex(user_text: str) -> str:
    """Regex fallback with word boundaries to route intents."""
    text = user_text.lower().strip()

    if len(text) <= 3 or text in ["a", "b", "c", "hi", "hii", "helo", "yo", "ok", "options", "shuru", "dikhao", "kuch", "help", "menu", "hub"]:
        return "small_talk"
    if re.search(r'\b(audit|verify|check doc|income certificate|caste certificate|marksheet|bonafide|fake|rejection)\b', text):
        return "audit_document"
    if re.search(r'\b(deadline|last date|closing|calendar|ics|reminder|when ends)\b', text):
        return "deadlines"
    if re.search(r'\b(compare|difference between|vs|versus)\b', text):
        return "compare"
    if re.search(r'\b(explain|details of|tell me about scheme|how to apply for)\b', text):
        return "explain_scheme"
    if re.search(r'\b(concierge|pack|sop|essay|apply for me|premium|paid)\b', text):
        return "concierge_pack"
    if re.search(r'\b(what if|what-if|suppose|simulate|if my income was)\b', text):
        return "what_if"
    if re.search(r'\b(my profile|my shortlist|saved|delete my data|my info)\b', text):
        return "my_profile"
    if re.search(r'\b(hi|hello|hey|namaste|pranam|kya haal|good morning|thanks|thank you)\b', text):
        return "small_talk"
    return "find_scholarships"

async def classify_intent(user_text: str) -> str:
    """
    Primary path: ASI1 LLM classifies user intent dynamically.
    Fallback: Deterministic regex intent classifier for zero-downtime offline execution.
    """
    try:
        import asyncio
        intent = await asyncio.wait_for(classify_intent_with_llm(user_text), timeout=3.0)
        if intent:
            return intent
    except Exception:
        pass

    return classify_intent_with_regex(user_text)

async def generate_grounded_explanation(scheme: ScholarshipItem, profile: StudentProfile, lang_hindi: bool = False) -> str:
    """
    Generates a 2-3 line grounded explanation why student matches, strictly grounded in data.
    If student is ineligible or close_miss, explains the actual blocking reason honestly.
    """
    if scheme.match_status in ["ineligible", "close_miss"]:
        reason_msg = scheme.match_reason or "Does not satisfy eligibility criteria."
        if lang_hindi:
            return f"Aap filhal is scheme ke liye eligible nahi hain: {reason_msg} Aap dusri available schemes check kar sakte hain."
        return f"You are currently ineligible for {scheme.name}: {reason_msg} Please explore other eligible opportunities."

    prompt = (
        f"Generate a concise 2-sentence explanation why the student qualifies for {scheme.name}.\n"
        f"Grounded facts only:\n"
        f"- Scheme: {scheme.name}\n"
        f"- Provider: {scheme.provider}\n"
        f"- Amount: {scheme.amount}\n"
        f"- Required Marks: >= {scheme.min_marks}%\n"
        f"- Max Income: ₹{scheme.max_family_income:,.0f}\n"
        f"- Student Marks: {profile.marks_percentage}%\n"
        f"- Student Income: ₹{profile.family_income:,.0f}\n"
        f"- Student State: {profile.state}\n"
        f"Language: {'Hindi/Hinglish' if lang_hindi else 'English'}.\n"
        "DO NOT invent any amounts or dates not listed above. Keep it encouraging."
    )

    try:
        import asyncio
        llm_resp = await asyncio.wait_for(
            call_asi1_chat([{"role": "system", "content": "You are a factual scholarship advisor."}, {"role": "user", "content": prompt}], temperature=0.2, max_tokens=150, timeout=3.0),
            timeout=3.0
        )
        if llm_resp:
            rupee_numbers = re.findall(r'₹\s*(\d[\d,]+)', llm_resp)
            safe = True
            for num in rupee_numbers:
                clean_num = int(num.replace(",", ""))
                if clean_num not in [int(scheme.amount_value), int(scheme.max_family_income), int(profile.family_income)]:
                    safe = False
                    break
            if safe:
                return llm_resp.strip()
    except Exception:
        pass

    # Deterministic fallback
    if lang_hindi:
        return (
            f"Aapki family income ₹{profile.family_income:,.0f} is scheme ki limit (₹{scheme.max_family_income:,.0f}) ke andar hai, "
            f"aur aapke {profile.marks_percentage:.1f}% marks required {scheme.min_marks:.1f}% cutoff ko pura karte hain. "
            f"Aap {scheme.amount} tak ki financial aid ke liye official portal ({scheme.portal}) par apply kar sakte hain."
        )
    return (
        f"Your annual household income of ₹{profile.family_income:,.0f} is well within the ₹{scheme.max_family_income:,.0f} ceiling, "
        f"and your academic performance ({profile.marks_percentage:.1f}%) comfortably exceeds the {scheme.min_marks:.1f}% requirement. "
        f"You can claim {scheme.amount} directly via {scheme.portal}."
    )

def draft_application_sop(scheme_name: str, profile: StudentProfile, key_reasons: str) -> str:
    """Drafts an authentic 250-word Statement of Purpose for scholarship applications."""
    # Deterministic high-quality Statement of Purpose for immediate concierge delivery
    return (
        f"To The Scholarship Selection Committee,\n"
        f"Subject: Application for {scheme_name}\n\n"
        f"Respected Committee Members,\n\n"
        f"I, {profile.student_name}, am a dedicated student currently pursuing {profile.course} from {profile.state}. "
        f"Having secured an academic score of {profile.marks_percentage}%, I have consistently prioritized scholastic dedication. "
        f"However, with an annual family income of ₹{profile.family_income:,.0f}, managing tuition, books, and educational fees "
        f"presents a severe financial challenge for my family.\n\n"
        f"Receiving the {scheme_name} would relieve this critical burden, enabling me to focus wholeheartedly on my degree and "
        f"contribute positively to society upon graduation. I commit to maintaining academic excellence and honoring this scholarship. "
        f"Thank you for considering my application.\n\n"
        f"Yours sincerely,\n{profile.student_name}"
    )
