import json
import os
import re
from typing import Dict, List, Optional, Tuple
from core.models import ScholarshipItem, StudentProfile

# Path to verified scholarship data
_base_dir = os.path.dirname(__file__) if "__file__" in globals() or "__file__" in locals() else os.getcwd()
DATA_PATH = os.path.join(_base_dir, "..", "data", "scholarships.json")

# State and UT Aliases mapping to canonical state name
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
    "jk": "Jammu and Kashmir", "j&k": "Jammu and Kashmir", "jammu & kashmir": "Jammu and Kashmir", "jammu and kashmir": "Jammu and Kashmir", "kashmir": "Jammu and Kashmir",
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
    "all": "All", "pan-india": "All", "india": "All"
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
    "PhD / Doctorate": ["phd", "doctorate", "research", "fellowship"]
}

SHORT_STATE_CODES = {
    "up", "mp", "ap", "hp", "uk", "dl", "rj", "mh", "ka", "tn",
    "kl", "gj", "pb", "hr", "br", "jh", "od", "as", "ch", "ga",
    "sk", "tr", "ml", "mn", "nl", "mz", "ar", "py", "an", "jk", "ts", "ct"
}
AMBIGUOUS_COURSE_ALIASES = {"be", "it", "ba", "ug", "pg"}

def normalize_state(text: str) -> str:
    cleaned = text.strip().lower()
    
    # If the input is exactly a known alias or code
    if cleaned in STATE_ALIASES and len(cleaned) <= 3:
        return STATE_ALIASES[cleaned]
    
    # 1. Unambiguous full state names and multi-word aliases (e.g. "bihar", "rajasthan", "uttar pradesh")
    for alias, canonical in STATE_ALIASES.items():
        if len(alias) <= 3 or alias in ["all", "india", "pan-india"]:
            continue
        if re.search(r'\b' + re.escape(alias) + r'\b', cleaned):
            return canonical

    # 2. Short 2-letter state codes require explicit context patterns:
    # - "from UP", "in MP", "state: UP", "domicile: UP", "living in UP"
    # - "UP se", "main UP se hu", "MP se"
    # - "UP state", "UP board", "UP domicile"
    # - dotted: "u.p.", "m.p.", "a.p.", "h.p."
    for code in SHORT_STATE_CODES:
        if code not in STATE_ALIASES:
            continue
        pattern = (
            r'\b(?:from|state|in|resident\s+of|domicile|location|hail\s+from|living\s+in)\s*[:=]?\s*' + re.escape(code) + r'\b|'
            r'\b' + re.escape(code) + r'\s+(?:se\b|state\b|resident\b|domicile\b|board\b)|'
            r'\b(?:main|i\s+am)\s+' + re.escape(code) + r'\s+se\b|'
            r'\bstate\s*[:=]\s*' + re.escape(code) + r'\b'
        )
        if re.search(pattern, cleaned):
            return STATE_ALIASES[code]

    if re.search(r'\bu\.p\.\b', cleaned):
        return "Uttar Pradesh"
    if re.search(r'\bm\.p\.\b', cleaned):
        return "Madhya Pradesh"
    if re.search(r'\ba\.p\.\b', cleaned):
        return "Andhra Pradesh"
    if re.search(r'\bh\.p\.\b', cleaned):
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
    
    # Check exact match first
    for canonical, synonyms in COURSE_KEYWORDS.items():
        if cleaned == canonical.lower() or cleaned in synonyms:
            return canonical

    # 1. Unambiguous keywords first (mbbs, btech, diploma, law, etc.)
    unambiguous_map = {
        "MBBS / BDS / Medical": ["mbbs", "bds", "medical", "nursing", "b.pharm", "pharma", "dentist", "doctor", "ayush"],
        "B.Tech / B.E.": ["b.tech", "btech", "engineering", "cse", "ece", "mech", "civil"],
        "Diploma / Polytechnic": ["diploma", "polytechnic", "iti"],
        "Law (LLB / LLM)": ["law", "llb", "llm", "ba llb"],
        "MBA / M.Tech / M.Sc": ["mba", "m.tech", "mtech", "m.sc", "msc", "mca", "postgraduate", "master"],
        "B.Sc / BCA / B.Com / BA": ["bsc", "b.sc", "bca", "bcom", "b.com", "degree", "graduation", "undergraduate"],
        "Class 11th - 12th": ["11th", "12th", "inter", "intermediate", "higher secondary", "+2"],
        "Class 10th": ["10th", "matric", "high school", "secondary"],
        "PhD / Doctorate": ["phd", "doctorate", "research", "fellowship"]
    }
    for canonical, syns in unambiguous_map.items():
        for syn in syns:
            if re.search(r'\b' + re.escape(syn) + r'\b', cleaned):
                return canonical

    # 2. Ambiguous short course codes (be, it, ba, ug, pg) require explicit dots or educational context
    if re.search(r'\bb\.e\.?\b|\b(?:doing|studying|course\s*[:=]?|branch\s*[:=]?|in)\s+be\b|\bbe\s+(?:degree|engineering)\b', cleaned):
        return "B.Tech / B.E."
    if re.search(r'\bi\.t\.?\b|\binformation\s+technology\b|\b(?:doing|studying|course\s*[:=]?|branch\s*[:=]?|in)\s+it\b', cleaned):
        return "B.Tech / B.E."
    if re.search(r'\bb\.a\.?\b|\bbachelor\s+of\s+arts\b|\b(?:doing|studying|course\s*[:=]?|in)\s+ba\b|\bba\s+degree\b', cleaned):
        return "B.Sc / BCA / B.Com / BA"
    if re.search(r'\bu\.g\.?\b|\bug\s+(?:course|degree|student)\b', cleaned):
        return "B.Sc / BCA / B.Com / BA"
    if re.search(r'\bp\.g\.?\b|\bpg\s+(?:course|degree|student)\b', cleaned):
        return "MBA / M.Tech / M.Sc"

    return ""

def load_scholarships() -> List[dict]:
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {DATA_PATH}: {e}")
        return []

def get_scheme_income_cap(scheme_id: str) -> Optional[float]:
    """Retrieves the exact income ceiling from data/scholarships.json for a given scheme ID."""
    if not scheme_id:
        return None
    for s in load_scholarships():
        sid = s.get("id", "")
        if sid == scheme_id or sid.lower() == scheme_id.lower():
            elig = s.get("eligibility", {})
            if "max_family_income" in elig and elig["max_family_income"] is not None:
                return float(elig["max_family_income"])
    return None

def evaluate_scheme(item: dict, profile: StudentProfile) -> Tuple[str, int, str]:
    """
    Evaluates a single scholarship against profile.
    Returns (status, score, reason) where status is 'eligible', 'close_miss', or 'ineligible'.
    """
    elig = item.get("eligibility", {})
    item_states = [s.lower() for s in elig.get("states", [])]
    user_state = profile.state.strip().lower()

    # 1. State check: State-restricted scheme requires user_state to match
    is_pan_india = ("all" in item_states) or ("pan-india" in item_states)
    if not is_pan_india:
        if not user_state or user_state in ["all", "unknown", ""]:
            return ("ineligible", 0, f"Restricted to {', '.join(elig.get('states', []))} residents (state not specified).")
        if user_state not in item_states:
            return ("ineligible", 0, f"Restricted to {', '.join(elig.get('states', []))} residents.")

    # 2. Gender check
    scheme_gender = elig.get("gender", "All").lower()
    user_gender = profile.gender.strip().lower()
    if scheme_gender == "female":
        if user_gender in ["female", "girl", "woman"]:
            pass
        elif user_gender in ["male", "boy", "man"]:
            return ("ineligible", 0, "Exclusively reserved for female students.")
        else:
            return ("close_miss", 75, "Maybe eligible (girls only, confirm gender).")

    # 3. Disability check
    if elig.get("disability_required", False) and not profile.disability:
        return ("ineligible", 0, "Requires >= 40% benchmark disability (Saksham Scheme).")

    # 4. Minority check
    if elig.get("minority_required", False) and not profile.minority and profile.category.lower() != "minority":
        return ("ineligible", 0, "Reserved for students from notified minority communities.")

    # 5. Category check: No 'general in allowed' shortcut!
    allowed_cats = [c.lower() for c in elig.get("categories", [])]
    user_cat = profile.category.strip().lower()
    if allowed_cats and "all" not in allowed_cats and user_cat not in allowed_cats:
        return ("ineligible", 0, f"Eligible categories: {', '.join(elig.get('categories', []))}.")

    # 6. Course check
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

    # 7. Min year of study check
    min_year = int(elig.get("min_year_of_study", 1))
    user_year = getattr(profile, "year_of_study", 1) or 1
    if user_year < min_year:
        return ("ineligible", 0, f"Requires minimum Year {min_year} of study (currently Year {user_year}).")

    # 8. Income check
    max_income = float(elig.get("max_family_income", 10000000.0))
    user_income = float(profile.family_income)
    if user_income > max_income:
        diff = user_income - max_income
        if diff <= 60000:
            return ("close_miss", 60, f"Income ₹{user_income:,.0f} exceeds ₹{max_income:,.0f} cap by ₹{diff:,.0f}.")
        return ("ineligible", 0, f"Annual family income exceeds maximum ceiling of ₹{max_income:,.0f}.")

    # 9. Marks check
    min_marks = float(elig.get("min_marks", 0.0))
    user_marks = float(profile.marks_percentage)
    if user_marks < min_marks:
        diff_marks = min_marks - user_marks
        if diff_marks <= 5.0:
            return ("close_miss", 65, f"Marks {user_marks:.1f}% are slightly below required {min_marks:.1f}% ({diff_marks:.1f}% short).")
        return ("ineligible", 0, f"Academic marks {user_marks:.1f}% below minimum {min_marks:.1f}%.")

    # 8. Score calculation (Explainable & Deterministic)
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
        reasons.append(f"High financial need (Income ₹{user_income:,.0f} <= 50% of ₹{max_income:,.0f} limit)")
    elif user_income <= (max_income * 0.8):
        score += 5
        reasons.append("Within standard income limits")

    if user_marks >= (min_marks + 15.0):
        score += 10
        reasons.append(f"Merit distinction ({user_marks:.1f}% well above {min_marks:.1f}% cutoff)")
    elif user_marks >= min_marks:
        score += 5
        reasons.append(f"Meets minimum {min_marks:.1f}% academic criteria")

    score = min(score, 100)
    reason_str = " • ".join(reasons) if reasons else "Meets all primary eligibility criteria."
    return ("eligible", score, reason_str)

def match_scholarships(profile: StudentProfile) -> Tuple[List[ScholarshipItem], List[ScholarshipItem]]:
    """
    Returns (eligible_items, close_misses) sorted by match score.
    """
    raw_data = load_scholarships()
    eligible: List[ScholarshipItem] = []
    close_misses: List[ScholarshipItem] = []

    for item in raw_data:
        status, score, reason = evaluate_scheme(item, profile)
        elig = item.get("eligibility", {})

        sc_item = ScholarshipItem(
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
            last_verified=item.get("last_verified", "2026-10-15"),
            verified=item.get("verified", True)
        )

        if status == "eligible":
            eligible.append(sc_item)
        elif status == "close_miss":
            close_misses.append(sc_item)

    # Sort eligible by match_score descending, then amount descending
    eligible.sort(key=lambda x: (x.match_score, x.amount_value), reverse=True)
    close_misses.sort(key=lambda x: x.match_score, reverse=True)

    return (eligible, close_misses)
