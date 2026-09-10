"""
Named Entity Recognition (NER) module.
Extracts cybercrime-relevant entities from free text using regex + spaCy patterns.
Handles: phone numbers, UPI IDs, amounts, transaction IDs, bank names,
         dates, times, URLs, email addresses, account numbers.
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta


# ─── Regex Patterns ────────────────────────────────────────────────────────────

PATTERNS = {
    "phone_numbers": re.compile(
        r"(?<!\d)(?:\+91[\-\s]?)?[6-9]\d{9}(?!\d)"
    ),
    "upi_ids": re.compile(
        r"[a-zA-Z0-9.\-_+]+@(?:okaxis|oksbi|okicici|okhdfcbank|ybl|ibl|axl|upi|paytm|"
        r"apl|freecharge|indus|kotak|rbl|sbi|icici|hdfc|axis|airtel|jio|"
        r"okbizaxis|ikwik|timecosmos|hdfcbank|[a-zA-Z0-9]+)"
    ),
    "amounts": re.compile(
        r"(?:₹|Rs\.?|INR|rupees?)\s*[\d,]+(?:\.\d{1,2})?|"
        r"[\d,]+(?:\.\d{1,2})?\s*(?:₹|Rs\.?|INR|rupees?)|"
        r"(?:(?:lost|transferred|sent|paid|debited|loss\s*(?:of)?|amount\s*(?:of|is|:)?)\s*(?:₹|Rs\.?|INR|rupees?)?\s*([\d,]+(?:\.\d{1,2})?))",
        re.IGNORECASE,
    ),
    "transaction_ids": re.compile(
        r"(?:txn(?:\s*id)?|transaction\s*(?:id|no\.?|number|ref(?:erence)?)|"
        r"utr(?:\s*no\.?|\s*number)?|rrn|upi\s*ref(?:erence)?|ref(?:erence)?\s*(?:id|no\.?|number)|order\s*(?:id|no\.?))"
        r"[\s:=#]*([A-Z0-9]{6,25})",
        re.IGNORECASE,
    ),
    "urls": re.compile(
        r"https?://[^\s\"'<>)]+|www\.[^\s\"'<>)]+"
    ),
    "emails": re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    ),
    "account_numbers": re.compile(
        r"(?:account\s*(?:no\.?|number|num))[\s:]*(\d{9,18})",
        re.IGNORECASE,
    ),
    "ifsc_codes": re.compile(
        r"\b[A-Z]{4}0[A-Z0-9]{6}\b"
    ),
    "dates": re.compile(
        r"\b(?:"
        r"\d{4}[-\/\.]\d{1,2}[-\/\.]\d{1,2}|"  # 2024-05-10
        r"\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4}|"  # 10/05/2024
        r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+\d{1,2}(?:st|nd|rd|th)?,?(?:\s*\d{4})?|"  # March 10 or March 10, 2024
        r"\d{1,2}(?:st|nd|rd|th)?\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"(?:,?\s*\d{4})?"  # 10th March or 10 March 2024
        r")\b",
        re.IGNORECASE,
    ),
    "times": re.compile(
        r"\b(?:"
        r"\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?|"  # 3:30 PM, 14:30
        r"(?:[01]?\d|2[0-3])\s*(?:AM|PM|am|pm)|"  # 3 PM, 3pm, 11 am
        r"\d{1,2}\s*o'clock"  # 3 o'clock
        r")\b",
        re.IGNORECASE,
    ),
    "pan_numbers": re.compile(
        r"\b[A-Z]{5}\d{4}[A-Z]\b"
    ),
    "aadhaar_numbers": re.compile(
        r"\b\d{4}\s?\d{4}\s?\d{4}\b"
    ),
}

BANK_NAMES = [
    "SBI", "State Bank of India", "State Bank", "HDFC Bank", "HDFC", "ICICI Bank", "ICICI",
    "Axis Bank", "Axis", "Kotak Mahindra", "Kotak", "Punjab National Bank", "PNB",
    "Bank of Baroda", "BOB", "Canara Bank", "Union Bank of India", "Union Bank",
    "IndusInd Bank", "IndusInd", "Yes Bank", "IDFC First Bank", "IDFC", "Federal Bank",
    "UCO Bank", "Indian Bank", "IOB", "Paytm Payments Bank", "Airtel Payments Bank",
]

PAYMENT_APPS = [
    "PhonePe", "Google Pay", "GPay", "Paytm", "BHIM UPI", "BHIM", "Amazon Pay",
    "WhatsApp Pay", "Cred", "Slice", "MobiKwik", "Freecharge",
]

PLATFORMS = [
    "LinkedIn", "Instagram", "Facebook", "WhatsApp", "Telegram", "Twitter", "X",
    "Snapchat", "Gmail", "Google", "Yahoo", "Outlook", "YouTube", "Discord", "Reddit",
]

BANK_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(b) for b in BANK_NAMES) + r")\b",
    re.IGNORECASE,
)

PAYMENT_APP_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in PAYMENT_APPS) + r")\b",
    re.IGNORECASE,
)

PLATFORM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in PLATFORMS) + r")\b",
    re.IGNORECASE,
)


def _deduplicate(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _clean_amount(raw: str) -> str:
    """Normalize amount strings to a consistent format."""
    num = re.sub(r"[^\d.]", "", raw).strip(".")
    try:
        val = float(num)
        return f"₹{val:,.2f}"
    except ValueError:
        return raw.strip()


def extract_entities(text: str) -> Dict[str, Any]:
    """
    Extract all cybercrime-relevant entities from text.
    """
    entities: Dict[str, Any] = {}

    # Phone numbers
    entities["phone_numbers"] = _deduplicate(PATTERNS["phone_numbers"].findall(text))

    # UPI IDs
    entities["upi_ids"] = _deduplicate(PATTERNS["upi_ids"].findall(text))

    # Financial amounts
    raw_amounts = []
    # 1. Regex matches
    for match in PATTERNS["amounts"].finditer(text):
        matched_str = match.group(1) if match.group(1) else match.group(0)
        raw_amounts.append(matched_str)

    # 2. Standalone number detection (e.g. user just enters "25000" or "50000")
    trimmed = text.strip().replace(",", "")
    if re.fullmatch(r"\d{3,8}(?:\.\d{1,2})?", trimmed):
        raw_amounts.append(trimmed)

    entities["amounts"] = _deduplicate([_clean_amount(a) for a in raw_amounts if a])

    # Transaction IDs / UTRs
    tx_ids = []
    for match in PATTERNS["transaction_ids"].finditer(text):
        tx_ids.append(match.group(1).strip())

    # Standalone 12-digit UTR detection (common in Indian banking/UPI)
    utr_candidates = re.findall(r"\b\d{12}\b", text)
    for c in utr_candidates:
        # ensure not a phone number or part of aadhaar
        if not c.startswith(("6", "7", "8", "9")):
            tx_ids.append(c)

    entities["transaction_ids"] = _deduplicate(tx_ids)

    # URLs
    entities["urls"] = _deduplicate(PATTERNS["urls"].findall(text))

    # Emails — filter out UPI IDs already found
    all_emails = _deduplicate(PATTERNS["emails"].findall(text))
    entities["emails"] = [e for e in all_emails if "@" not in e or not any(
        e == u for u in entities["upi_ids"]
    )]

    # Account numbers
    entities["account_numbers"] = _deduplicate(PATTERNS["account_numbers"].findall(text))

    # IFSC codes
    entities["ifsc_codes"] = _deduplicate(PATTERNS["ifsc_codes"].findall(text))

    # Dates and times
    found_dates = PATTERNS["dates"].findall(text)
    text_lower = text.lower()
    now = datetime.now()
    if "day before yesterday" in text_lower:
        found_dates.append((now - timedelta(days=2)).strftime("%d %B %Y"))
    elif "yesterday" in text_lower or "last night" in text_lower:
        found_dates.append((now - timedelta(days=1)).strftime("%d %B %Y"))
    elif "today" in text_lower or "this morning" in text_lower or "just now" in text_lower:
        found_dates.append(now.strftime("%d %B %Y"))
    else:
        days_ago = re.findall(r"\b(\d+)\s+days?\s+ago\b", text_lower)
        for d in days_ago:
            try:
                found_dates.append((now - timedelta(days=int(d))).strftime("%d %B %Y"))
            except ValueError:
                pass

    entities["dates"] = _deduplicate(found_dates)
    entities["times"] = _deduplicate(PATTERNS["times"].findall(text))

    # Bank names
    entities["banks"] = _deduplicate(BANK_PATTERN.findall(text))

    # Payment apps
    entities["payment_apps"] = _deduplicate(PAYMENT_APP_PATTERN.findall(text))

    # Social media & tech platforms
    entities["platforms"] = _deduplicate(PLATFORM_PATTERN.findall(text))

    # PAN numbers (mask for privacy)
    pans = PATTERNS["pan_numbers"].findall(text)
    entities["pan_numbers"] = [p[:2] + "***" + p[-1] for p in _deduplicate(pans)]

    return {k: v for k, v in entities.items() if v}


def merge_entities(existing: Dict, new: Dict) -> Dict:
    """Merge two entity dicts, deduplicating lists."""
    merged = dict(existing)
    for key, value in new.items():
        if key in merged and isinstance(merged[key], list):
            merged[key] = _deduplicate(merged[key] + value)
        else:
            merged[key] = value
    return merged


def entities_to_summary(entities: Dict) -> str:
    """Convert extracted entities to a human-readable summary string."""
    parts = []
    label_map = {
        "phone_numbers": "📞 Phone Numbers",
        "upi_ids": "💳 UPI IDs",
        "amounts": "💰 Amounts",
        "transaction_ids": "🔖 Transaction IDs",
        "urls": "🔗 URLs",
        "emails": "📧 Emails",
        "account_numbers": "🏦 Account Numbers",
        "ifsc_codes": "🔢 IFSC Codes",
        "dates": "📅 Dates",
        "times": "⏰ Times",
        "banks": "🏛️ Banks",
        "payment_apps": "📱 Payment Apps",
        "platforms": "🌐 Affected Platforms",
    }
    for key, label in label_map.items():
        if key in entities and entities[key]:
            parts.append(f"{label}: {', '.join(str(v) for v in entities[key])}")
    return "\n".join(parts) if parts else "No specific entities detected."


def parse_datetime_flexible(date_val: Any, time_val: Optional[Any] = None) -> Optional[datetime]:
    """
    Flexibly parse date and optional time from strings or existing datetimes into a valid datetime object.
    Supports ISO formats, standard Indian/UK and US formats, textual month names, and relative phrases.
    """
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        dt = date_val
    elif isinstance(date_val, date):
        dt = datetime(date_val.year, date_val.month, date_val.day)
    else:
        raw_str = str(date_val).strip()
        dt = None
        
        # 1. Try ISO fromisoformat
        try:
            iso_clean = raw_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_clean)
        except (ValueError, TypeError):
            pass

        # 2. Check relative dates
        if dt is None:
            raw_lower = raw_str.lower()
            now = datetime.now()
            if "day before yesterday" in raw_lower:
                dt = now - timedelta(days=2)
            elif "yesterday" in raw_lower or "last night" in raw_lower:
                dt = now - timedelta(days=1)
            elif "today" in raw_lower or "this morning" in raw_lower or "just now" in raw_lower:
                dt = now
            else:
                days_ago_match = re.search(r"(\d+)\s+days?\s+ago", raw_lower)
                if days_ago_match:
                    dt = now - timedelta(days=int(days_ago_match.group(1)))

        # 3. Try standard formats
        if dt is None:
            cleaned_date = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", raw_str)
            cleaned_date = re.sub(r"[,\s]+", " ", cleaned_date).strip()
            date_formats = [
                "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
                "%d/%m/%y", "%d-%m-%y", "%m/%d/%Y", "%m/%d/%y",
                "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y",
                "%d %B", "%d %b", "%B %d", "%b %d",
                "%Y/%m/%d", "%Y.%m.%d",
            ]
            for fmt in date_formats:
                try:
                    parsed = datetime.strptime(cleaned_date, fmt)
                    if "%Y" not in fmt and "%y" not in fmt:
                        parsed = parsed.replace(year=datetime.now().year)
                    dt = parsed
                    break
                except ValueError:
                    continue

    if dt is None:
        return None

    # Parse and combine time if provided
    if time_val:
        time_str = str(time_val).strip()
        time_cleaned = re.sub(r"\s+", " ", time_str).upper()
        time_cleaned = re.sub(r"(\d+)(AM|PM)", r"\1 \2", time_cleaned)
        time_formats = [
            "%I:%M %p", "%I:%M:%S %p", "%I %p",
            "%H:%M", "%H:%M:%S",
        ]
        for tfmt in time_formats:
            try:
                t = datetime.strptime(time_cleaned, tfmt)
                dt = dt.replace(hour=t.hour, minute=t.minute, second=t.second)
                break
            except ValueError:
                continue

    return dt


if __name__ == "__main__":
    sample = """
    Yesterday I received a call from 9876543210. They said they were from SBI.
    I transferred ₹25,000 to xyz@oksbi at 4:32 PM. 
    Transaction ID: UTR123456789. My account number is 1234567890.
    They sent me a link: https://fake-bank.com/login
    """
    result = extract_entities(sample)
    for k, v in result.items():
        print(f"{k}: {v}")
