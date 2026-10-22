import re

def mask_sensitive_identifiers(text: str) -> str:
    """
    Masks sensitive identifiers to protect user privacy:
    - 12-digit Aadhaar numbers (with spaces, hyphens, or continuous)
    - 10-character PAN card numbers
    - 10-digit Indian phone numbers (optionally with +91 or 0 prefix)
    - 9-18 digit bank account numbers
    """
    if not text:
        return ""
    
    # 1. Aadhaar: 12 digits in groups of 4 or continuous 12 digits -> masked as XXXX-XXXX-<last4>
    text = re.sub(r'\b\d{4}[\s-]\d{4}[\s-](\d{4})\b', r'XXXX-XXXX-\1', text)
    text = re.sub(r'\b\d{8}(\d{4})\b', r'XXXX-XXXX-\1', text)
    
    # 2. PAN card (5 letters, 4 digits, 1 letter)
    text = re.sub(r'\b[A-Za-z]{5}\d{4}[A-Za-z]\b', '[REDACTED_PAN]', text)
    
    # 3. Phone numbers (10 digits starting with 6-9, optional +91 or 0 prefix)
    text = re.sub(r'(?:\+91[\s-]?)?(?:\b0)?[6-9]\d{9}\b', '[REDACTED_PHONE]', text)
    
    # 4. Bank Account numbers (prefixed by A/C or account, or standalone 11-18 digit numbers)
    text = re.sub(r'(?i)\b(?:a/c|acc(?:ount)?(?:\s*no)?\.?)\s*[:#-]?\s*\d{8,18}\b', '[REDACTED_ACCOUNT]', text)
    text = re.sub(r'\b\d{11,18}\b', '[REDACTED_ACCOUNT]', text)
    
    return text
