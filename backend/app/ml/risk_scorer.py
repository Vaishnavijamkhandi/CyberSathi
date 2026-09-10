"""
Cybercrime Risk Scorer.
Estimates urgency/priority of a cybercrime incident using a weighted scoring model.
Outputs: CRITICAL / HIGH / MEDIUM / LOW with a detailed breakdown.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RiskInput:
    """All factors contributing to risk/urgency scoring."""
    # Financial impact
    financial_loss: float = 0.0        # Amount in ₹
    # Account/credential status
    account_compromised: bool = False
    otp_shared: bool = False
    password_shared: bool = False
    pin_shared: bool = False
    credentials_exposed: bool = False
    # Ongoing threat
    ongoing_attack: bool = False       # Attack still happening
    # Identity
    identity_exposed: bool = False     # Aadhaar, PAN, etc. shared
    # Threat level
    extortion_threat: bool = False     # Threats / blackmail
    malware_present: bool = False      # Device infected
    # Time
    hours_since_incident: Optional[float] = None  # Hours elapsed
    # Extra context
    crime_category: str = ""


@dataclass
class RiskOutput:
    level: str          # CRITICAL / HIGH / MEDIUM / LOW
    score: float        # 0-100
    breakdown: Dict[str, float] = field(default_factory=dict)
    immediate_actions: list = field(default_factory=list)
    explanation: str = ""


# ─── Scoring Weights ───────────────────────────────────────────────────────────

CRIME_CATEGORY_BASE_SCORES = {
    # Critical categories (35-50 pts)
    "malware / ransomware": 45,
    "cyber extortion": 45,
    "ransomware": 45,
    "extortion": 45,
    "sextortion": 45,
    "child sexual abuse material (csam)": 50,
    "digital arrest scam": 40,
    "cyber espionage / corporate hack": 40,

    # High severity categories (20-30 pts)
    "banking fraud": 28,
    "banking fraud / upi fraud": 28,
    "upi / payment fraud": 20,
    "otp / social engineering": 24,
    "identity theft": 28,
    "sim swap fraud": 30,
    "investment fraud": 24,
    "investment / trading scam": 24,
    "cryptocurrency fraud": 24,
    "crypto fraud": 24,
    "loan app scam": 24,

    # Medium severity categories (12-18 pts)
    "phishing": 18,
    "phishing / spoofing": 18,
    "job / employment fraud": 16,
    "job / task scam": 16,
    "account compromise": 18,
    "impersonation": 18,
    "social media fraud": 14,
    "social media crime / impersonation": 14,
    "e-commerce fraud": 10,
    "e-commerce / lottery fraud": 10,
    "other / unknown": 0,
}

FINANCIAL_THRESHOLDS = [
    (500_000, 35),   # >= ₹5 Lakh  → 35 pts
    (100_000, 30),   # >= ₹1 Lakh  → 30 pts
    (50_000,  25),   # >= ₹50k     → 25 pts
    (20_000,  20),   # >= ₹20k     → 20 pts
    (5_000,   15),   # >= ₹5k      → 15 pts
    (1_000,   10),   # >= ₹1k      → 10 pts
    (1,        5),   # > ₹0        →  5 pts
]

BOOLEAN_WEIGHTS = {
    "account_compromised": 20,
    "otp_shared":          18,
    "password_shared":     18,
    "pin_shared":          18,
    "credentials_exposed": 16,
    "ongoing_attack":      25,
    "identity_exposed":    12,
    "extortion_threat":    22,
    "malware_present":     20,
}

TIME_BONUSES = [
    (2,  12),   # <= 2 hrs  → extra 12 pts (golden window for 1930 / bank freeze)
    (6,   8),   # <= 6 hrs  → extra 8 pts
    (24,  5),   # <= 24 hrs → extra 5 pts
]

RISK_THRESHOLDS = {
    "CRITICAL": 60,
    "HIGH":     38,
    "MEDIUM":   18,
    "LOW":       0,
}

IMMEDIATE_ACTION_MAP = {
    "CRITICAL": [
        "🚨 Call the National Cybercrime Helpline: 1930 immediately",
        "🔒 Block all affected bank cards/accounts immediately",
        "📱 Change passwords for all compromised accounts NOW",
        "🏦 Contact your bank's fraud department immediately",
        "📋 Do NOT delete any messages, screenshots, or evidence",
        "🌐 Report on cybercrime.gov.in immediately",
    ],
    "HIGH": [
        "📞 Report on cybercrime.gov.in within the next few hours",
        "🔒 Freeze/block affected payment instruments",
        "📱 Change passwords for affected accounts",
        "💾 Save all evidence (screenshots, messages, transaction IDs)",
        "🏦 Inform your bank about the fraud",
    ],
    "MEDIUM": [
        "📋 File a complaint on cybercrime.gov.in",
        "💾 Preserve all digital evidence",
        "📱 Review and secure your account settings",
        "📸 Collect all relevant screenshots and documents",
    ],
    "LOW": [
        "📋 Document the incident thoroughly",
        "📞 Consider reporting to cybercrime.gov.in for awareness",
        "⚠️ Stay alert for follow-up scam attempts",
        "💡 Educate yourself on similar fraud patterns",
    ],
}


def calculate_risk(inp: RiskInput) -> RiskOutput:
    """
    Calculate a risk score from 0–100 and return a risk level.
    """
    breakdown: Dict[str, float] = {}
    total_score = 0.0

    # 1. Crime Category base urgency
    cat_score = 0.0
    if inp.crime_category:
        cat_lower = inp.crime_category.lower().strip()
        for cat_key, pts in CRIME_CATEGORY_BASE_SCORES.items():
            if cat_key in cat_lower or cat_lower in cat_key:
                cat_score = max(cat_score, pts)
    if cat_score > 0:
        breakdown["crime_category_urgency"] = float(cat_score)
        total_score += cat_score

    # 2. Financial impact
    fin_score = 0.0
    for threshold, pts in FINANCIAL_THRESHOLDS:
        if inp.financial_loss >= threshold:
            fin_score = float(pts)
            break
    breakdown["financial_impact"] = fin_score
    total_score += fin_score

    # 3. Boolean risk factors
    for factor, weight in BOOLEAN_WEIGHTS.items():
        if getattr(inp, factor, False):
            breakdown[factor] = float(weight)
            total_score += weight

    # 4. Time-based urgency bonus
    time_bonus = 0.0
    if inp.hours_since_incident is not None:
        for hours, bonus in TIME_BONUSES:
            if inp.hours_since_incident <= hours:
                time_bonus = float(bonus)
                break
    breakdown["time_urgency"] = time_bonus
    total_score += time_bonus

    # Cap at 100
    total_score = min(total_score, 100.0)

    # 5. Determine level
    level = "LOW"
    for lvl, threshold in RISK_THRESHOLDS.items():
        if total_score >= threshold:
            level = lvl
            break

    # 6. Build explanation
    top_factors = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
    top_3 = [f for f in top_factors if f[1] > 0][:3]
    factor_labels = {
        "crime_category_urgency": "crime category severity",
        "financial_impact": "significant financial loss",
        "account_compromised": "account compromise",
        "otp_shared": "OTP disclosure",
        "password_shared": "password exposure",
        "pin_shared": "PIN disclosure",
        "credentials_exposed": "credential exposure",
        "ongoing_attack": "ongoing attack",
        "identity_exposed": "identity information exposure",
        "extortion_threat": "active extortion threat",
        "malware_present": "malware / ransomware presence",
        "time_urgency": "recent incident (time-critical)",
    }
    reason_parts = [factor_labels.get(k, k) for k, _ in top_3]
    explanation = f"Risk classified as {level} (score: {total_score:.0f}/100)."
    if reason_parts:
        explanation += f" Key factors: {', '.join(reason_parts)}."

    return RiskOutput(
        level=level,
        score=round(total_score, 1),
        breakdown=breakdown,
        immediate_actions=IMMEDIATE_ACTION_MAP[level],
        explanation=explanation,
    )


def risk_from_dict(data: dict) -> RiskOutput:
    """Convenience wrapper accepting a plain dict."""
    inp = RiskInput(**{k: v for k, v in data.items() if hasattr(RiskInput, k)})
    return calculate_risk(inp)


def detect_risk_signals(text: str) -> Dict[str, bool]:
    """
    Extract boolean risk indicators from text using comprehensive cybercrime terminology.
    """
    text_lower = (text or "").lower()
    return {
        "account_compromised": any(k in text_lower for k in [
            "account hacked", "lost access", "locked out", "compromised", "hacked",
            "can't login", "cannot login", "unable to login", "unauthorized access",
            "account takeover", "password changed", "stolen account",
        ]),
        "otp_shared": any(k in text_lower for k in [
            "shared otp", "gave otp", "told otp", "otp share", "entered otp",
            "sent otp", "provided otp", "submitted otp", "given otp", "put otp",
            "entered the otp", "shared the otp", "asked for otp", "asked for the otp",
            "gave the otp", "told the otp", "one time password",
        ]),
        "password_shared": any(k in text_lower for k in [
            "shared password", "gave password", "entered password", "told password",
            "sent password", "provided password",
        ]),
        "pin_shared": any(k in text_lower for k in [
            "shared pin", "entered pin", "gave pin", "mpin", "atm pin", "cvv",
            "card pin", "transaction pin", "upi pin",
        ]),
        "credentials_exposed": any(k in text_lower for k in [
            "entered credentials", "login details", "username password", "netbanking",
            "card details", "debit card details", "credit card details", "atm card",
            "entered card", "banking credentials",
        ]),
        "ongoing_attack": any(k in text_lower for k in [
            "still happening", "ongoing", "right now", "currently", "money is still being debited",
            "they are calling again", "active now", "in progress", "just debited again",
        ]),
        "identity_exposed": any(k in text_lower for k in [
            "aadhaar", "pan card", "identity", "passport", "voter id", "driving license",
            "kyc documents",
        ]),
        "extortion_threat": any(k in text_lower for k in [
            "threatening", "blackmail", "threat", "extortion", "threatened", "defame",
            "leak", "nude", "private photos", "private video", "police case",
            "digital arrest", "demanding money", "cbi arrest", "customs notice",
        ]),
        "malware_present": any(k in text_lower for k in [
            "virus", "malware", "ransomware", "hacked device", "anydesk", "teamviewer",
            "rustdesk", "quicksupport", "screen share", "remote access", "downloaded apk",
            "installed apk", "malicious app",
        ]),
    }


def calculate_risk_score(
    crime_category: str = "",
    financial_loss: float = 0.0,
    text: str = "",
    extracted_entities: Optional[dict] = None,
    hours_since_incident: Optional[float] = None,
) -> dict:
    """Calculate risk score and return as dictionary."""
    signals = detect_risk_signals(text)
    inp = RiskInput(
        financial_loss=financial_loss,
        crime_category=crime_category,
        hours_since_incident=hours_since_incident,
        **signals,
    )
    res = calculate_risk(inp)
    return {
        "level": res.level,
        "score": res.score,
        "breakdown": res.breakdown,
        "immediate_actions": res.immediate_actions,
        "explanation": res.explanation,
    }


def identify_missing_info(crime_category: str, entities: Optional[dict] = None) -> list:
    """Identify missing info fields for a given category and extracted entities."""
    from app.services.gemini_service import MISSING_INFO_CATEGORIES
    required_fields = MISSING_INFO_CATEGORIES.get(crime_category, [])
    entities = entities or {}
    present_keys = set(entities.keys())
    missing = []
    for field in required_fields:
        if field not in present_keys:
            missing.append({"field": field, "description": field.replace("_", " ").title()})
    return missing



if __name__ == "__main__":
    sample = RiskInput(
        financial_loss=40000,
        otp_shared=True,
        account_compromised=True,
        hours_since_incident=0.5,
    )
    result = calculate_risk(sample)
    print(f"Level: {result.level}")
    print(f"Score: {result.score}")
    print(f"Explanation: {result.explanation}")
    print("Immediate actions:")
    for action in result.immediate_actions:
        print(f"  {action}")
