"""
Timeline Generator — constructs a chronological incident timeline
from extracted entities across all chat messages and evidence files.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from app.ml.ner_extractor import parse_datetime_flexible


# ─── Event Types ───────────────────────────────────────────────────────────────

EVENT_TYPE_ICONS = {
    "payment": "💸",
    "call": "📞",
    "message": "💬",
    "login": "🔐",
    "document": "📄",
    "threat": "⚠️",
    "discovery": "🔍",
    "report": "📋",
    "other": "📌",
}

# Keywords that suggest event types
EVENT_TYPE_KEYWORDS = {
    "payment": ["paid", "transferred", "debited", "transaction", "upi", "payment", "withdrew", "scammed", "loss", "sent"],
    "call": ["called", "received call", "phone call", "spoke to", "caller", "incoming call"],
    "message": ["message", "sms", "whatsapp", "telegram", "email", "received message", "sent message"],
    "login": ["logged in", "otp", "password", "credential", "login", "access", "anydesk", "teamviewer", "link", "clicked"],
    "document": ["received document", "offer letter", "receipt", "screenshot uploaded", "statement"],
    "threat": ["threatened", "blackmail", "demanded", "extortion", "nude", "video", "police", "arrest", "cbi"],
    "discovery": ["noticed", "realized", "discovered", "found out", "check", "alert", "frozen"],
    "report": ["reported", "complaint", "called helpline", "informed bank", "1930"],
}


def detect_event_type(description: str) -> str:
    desc_lower = description.lower()
    for event_type, keywords in EVENT_TYPE_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return event_type
    return "other"


def parse_datetime_string(date_val: Any, time_val: Optional[Any] = None) -> Optional[str]:
    """Parse a date and optional time into a clean standardized string (e.g., 08 Sep 2026, 03:30 PM)."""
    dt = parse_datetime_flexible(date_val, time_val)
    if dt:
        has_time = bool(time_val or dt.hour != 0 or dt.minute != 0)
        return dt.strftime("%d %b %Y, %I:%M %p" if has_time else "%d %b %Y")
    return str(date_val) if date_val else None


def _to_sortable(date_val: Any, time_val: Optional[Any] = None, seq: int = 0) -> int:
    """Convert date+time to sortable integer (YYYYMMDDHHMMSS) with sequence offset."""
    dt = parse_datetime_flexible(date_val, time_val)
    if dt:
        base = int(dt.strftime("%Y%m%d%H%M%S"))
        return base + seq
    return 99999999999999 + seq


def _summarize_message_event(content: str, amounts: List[str]) -> str:
    """Create a concise description of a chat message event."""
    content_lower = content.lower()

    if "otp" in content_lower and any(k in content_lower for k in ["share", "gave", "told", "sent", "enter", "put", "provide"]):
        return "OTP entered / shared with perpetrator"
    elif any(k in content_lower for k in ["transfer", "paid", "debited", "loss", "sent money", "withdrew"]):
        amount_str = f" of {amounts[0]}" if amounts else ""
        return f"Unauthorized financial transaction{amount_str}"
    elif any(k in content_lower for k in ["call", "called", "spoke"]):
        return "Fraudulent phone call received"
    elif any(k in content_lower for k in ["link", "clicked", "url", "website"]):
        return "Phishing link accessed / credentials entered"
    elif any(k in content_lower for k in ["anydesk", "teamviewer", "rustdesk", "quicksupport", "apk", "app"]):
        return "Remote access / suspicious app installed"
    elif any(k in content_lower for k in ["threat", "blackmail", "extort", "video", "photos", "police", "arrest"]):
        return "Threat / blackmail received from perpetrator"
    elif any(k in content_lower for k in ["noticed", "realized", "discovered", "found out", "bank alert"]):
        return "Fraudulent activity discovered / bank alerted"
    elif any(k in content_lower for k in ["message", "sms", "whatsapp", "telegram", "email"]):
        return "Fraudulent message / email received"
    elif amounts:
        return f"Amount {amounts[0]} involved in incident"
    else:
        return content[:80].strip() + ("..." if len(content) > 80 else "")


def build_timeline(
    chat_messages: List[Dict],
    evidence_files: List[Any],
    extracted_entities: Dict,
    incident_date: Optional[Any] = None,
) -> List[Dict]:
    """
    Build a chronological timeline of the incident from all sources.

    Args:
        chat_messages: List of chat message dicts with content and entities
        evidence_files: Evidence file records
        extracted_entities: Combined entities from all sources
        incident_date: Primary incident datetime if already known

    Returns:
        Sorted list of timeline events: [{datetime, description, source, event_type, icon}]
    """
    events = []

    # Primary incident datetime fallback
    default_dt = None
    if incident_date:
        default_dt = parse_datetime_flexible(incident_date)
    if not default_dt and extracted_entities.get("dates"):
        default_dt = parse_datetime_flexible(
            extracted_entities["dates"][0],
            extracted_entities.get("times", [None])[0] if extracted_entities.get("times") else None
        )

    seen_events = set()
    seq = 0

    # Extract events from chat messages
    for msg in chat_messages:
        if msg.get("role") != "user":
            continue
        content = msg.get("content", "").strip()
        if not content:
            continue
        msg_entities = msg.get("extracted_entities", {}) or {}

        dates = msg_entities.get("dates", [])
        times = msg_entities.get("times", [])
        amounts = msg_entities.get("amounts", [])

        desc = _summarize_message_event(content, amounts)
        event_type = detect_event_type(content)

        # Only add meaningful cybercrime events
        if event_type == "other" and not dates and not amounts:
            continue

        if desc in seen_events:
            continue
        seen_events.add(desc)

        seq += 1
        if dates:
            for i, date_val in enumerate(dates):
                time_val = times[i] if i < len(times) else (times[0] if times else None)
                dt_str = parse_datetime_string(date_val, time_val)
                events.append({
                    "datetime": dt_str,
                    "description": desc,
                    "source": "Your description",
                    "event_type": event_type,
                    "icon": EVENT_TYPE_ICONS.get(event_type, "📌"),
                    "sortable": _to_sortable(date_val, time_val, seq),
                })
        elif default_dt:
            time_val = times[0] if times else (default_dt.strftime("%I:%M %p") if default_dt.hour != 0 else None)
            dt_str = parse_datetime_string(default_dt, time_val)
            events.append({
                "datetime": dt_str,
                "description": desc,
                "source": "Your description",
                "event_type": event_type,
                "icon": EVENT_TYPE_ICONS.get(event_type, "📌"),
                "sortable": _to_sortable(default_dt, time_val, seq),
            })
        else:
            events.append({
                "datetime": "Date not specified",
                "description": desc,
                "source": "Your description",
                "event_type": event_type,
                "icon": EVENT_TYPE_ICONS.get(event_type, "📌"),
                "sortable": 99999999999999 + seq,
            })

    # Extract events from evidence files
    for ef in evidence_files:
        ef_entities = getattr(ef, "extracted_entities", {}) or {}
        filename = getattr(ef, "original_filename", "Evidence file")
        doc_type = getattr(ef, "document_type", "document") or "document"

        dates = ef_entities.get("dates", [])
        times = ef_entities.get("times", [])
        amounts = ef_entities.get("amounts", [])

        amount_str = f" | Amount: {amounts[0]}" if amounts else ""
        desc = f"{doc_type.replace('_', ' ').title()} from {filename}{amount_str}"
        seq += 1

        if dates:
            date_val = dates[0]
            time_val = times[0] if times else None
            dt_str = parse_datetime_string(date_val, time_val)
            events.append({
                "datetime": dt_str,
                "description": desc,
                "source": f"Uploaded: {filename}",
                "event_type": "document",
                "icon": EVENT_TYPE_ICONS.get("document", "📄"),
                "sortable": _to_sortable(date_val, time_val, seq),
            })
        elif default_dt:
            dt_str = parse_datetime_string(default_dt)
            events.append({
                "datetime": dt_str,
                "description": desc,
                "source": f"Uploaded: {filename}",
                "event_type": "document",
                "icon": EVENT_TYPE_ICONS.get("document", "📄"),
                "sortable": _to_sortable(default_dt, None, seq),
            })

    # Sort chronologically
    events.sort(key=lambda x: x.get("sortable", 99999999999999))

    # Remove internal sortable key from output
    for e in events:
        e.pop("sortable", None)

    return events
