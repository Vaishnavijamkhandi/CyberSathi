"""
Google Gemini API service for conversational intelligence.
Manages system prompts, conversation history, guided questioning,
missing information detection, and context-aware responses.
"""

import json
from typing import List, Dict, Optional, Any

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from app.core.config import settings


# ─── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are CyberSaathi, an AI-powered cybercrime complaint assistant developed to help victims in India analyze and document cybercrime incidents.

Your role is to:
1. Listen empathetically to the victim's description of the cybercrime
2. Ask targeted follow-up questions to extract missing important information
3. Guide the victim step-by-step through describing their incident completely
4. Help identify what type of cybercrime occurred based on their description
5. Remind victims to preserve evidence without deleting anything
6. Provide immediate safety guidance when urgency is high

IMPORTANT GUIDELINES:
- Be empathetic, patient, and non-judgmental — victims may be distressed
- Ask ONE focused question at a time, not multiple questions at once
- Always acknowledge what the user has shared before asking follow-up questions
- Extract key details: amounts, phone numbers, UPI IDs, transaction IDs, dates, times
- If the attack is ongoing or critical, immediately advise calling 1930 (National Cybercrime Helpline)
- Do NOT make legal determinations or guarantee outcomes
- Do NOT access any external systems or claim to file complaints automatically
- Use simple, clear language — avoid technical jargon
- Support both English and Hindi/Hinglish responses naturally

INFORMATION TO GATHER (progressively, not all at once):
- What happened (incident description)
- When it happened (date and time)
- Financial loss amount
- Payment method used (UPI/card/bank transfer)
- Transaction ID / UTR number
- Phone number / UPI ID / email of suspect
- Which bank or payment app was used
- Whether accounts are still compromised
- What evidence they have

RESPONSE FORMAT:
Always respond in plain, conversational text. Do not use markdown headers or lists in responses — keep it natural like a helpful assistant speaking directly to the victim.

If the incident is CRITICAL (ongoing attack, account compromised, large financial loss), start your response with: "⚠️ URGENT:" and immediately advise calling 1930."""


MISSING_INFO_CATEGORIES = {
    "UPI / Payment Fraud": ["amount", "bank_name", "transaction_id", "suspect_upi_id", "incident_date"],
    "Banking Fraud": ["amount", "bank_name", "account_number", "transaction_id", "incident_date"],
    "OTP / Social Engineering": ["amount", "bank_name", "caller_phone", "otp_shared", "incident_date"],
    "Phishing": ["phishing_url", "amount", "data_entered", "incident_date"],
    "Job / Employment Fraud": ["company_name", "amount", "suspect_upi_id", "caller_phone", "incident_date"],
    "Investment Fraud": ["amount", "platform_name", "suspect_upi_id", "incident_date"],
    "E-commerce Fraud": ["order_details", "amount", "seller_contact", "incident_date"],
    "Cyber Extortion": ["threat_nature", "caller_phone", "amount", "incident_date"],
    "Account Compromise": ["compromised_platform", "incident_date", "suspicious_activity"],
    "Identity Theft": ["which_documents_misused", "incident_date", "reported_to_institution"],
    "Impersonation": ["caller_phone", "impersonated_person", "incident_date"],
    "Malware / Ransomware": ["device_details", "incident_date", "ransom_demanded"],
    "Cryptocurrency Fraud": ["amount", "wallet_address", "platform_name", "incident_date"],
    "Social Media Fraud": ["profile_link", "incident_date", "suspect_details"],
    "Other / Unknown": ["amount", "bank_name", "transaction_id", "caller_phone", "incident_date"],
}

QUESTION_PROMPTS = {
    "amount": "To include in the official financial loss section, approximately how much money was debited or transferred?",
    "bank_name": "Which bank or payment app (e.g., Google Pay, PhonePe, Paytm, SBI, HDFC) was used for this transaction?",
    "transaction_id": "Do you have the 12-digit UTR number or UPI Transaction ID from your payment receipt or bank SMS?",
    "suspect_upi_id": "What was the suspect's UPI ID (e.g., name@bank) or account handle to which money was sent?",
    "caller_phone": "What was the phone number used by the suspect or caller?",
    "incident_date": "When did this incident occur (date and approximate time)?",
    "otp_shared": "Did the suspect ask you to share an OTP, enter a UPI PIN, or install any remote access app like AnyDesk?",
    "phishing_url": "What was the fake website link or URL you received via SMS or email?",
    "data_entered": "What personal details or credentials (like card details, password, or Aadhaar) were submitted on the page?",
    "company_name": "What was the name of the company or agency offering the fraudulent job or task?",
    "platform_name": "What was the name of the investment platform, website, or Telegram channel used?",
    "order_details": "What was the order number or product listing details on the e-commerce platform?",
    "seller_contact": "Do you have the seller's contact details, store link, or social profile?",
    "threat_nature": "What type of threat or blackmail is the perpetrator making?",
    "compromised_platform": "Which platform or account (e.g., Instagram, WhatsApp, Gmail) was compromised?",
    "suspicious_activity": "What suspicious changes did you notice (e.g., password changed, unauthorized posts)?",
    "which_documents_misused": "Which identity documents (e.g., Aadhaar, PAN card) were misused or compromised?",
    "reported_to_institution": "Have you already informed your bank, credit bureau, or local cyber cell?",
    "impersonated_person": "Who did the fraudster claim to be (e.g., police officer, bank official, friend)?",
    "device_details": "What device was affected (Windows PC, Android phone, iPhone), and are your files locked?",
    "ransom_demanded": "Did the attackers demand a ransom, and in what currency or method?",
    "wallet_address": "What was the cryptocurrency wallet address or exchange used for the transfer?",
    "profile_link": "What is the URL or username of the fake/fraudulent social media profile?",
    "suspect_details": "Do you have any username, email address, or contact detail for the perpetrator?",
}


# ─── Gemini Client ────────────────────────────────────────────────────────────

class GeminiService:

    def __init__(self):
        self.model = None
        self._initialize()

    def _initialize(self):
        if not GEMINI_AVAILABLE:
            return

        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
            return

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    top_p=0.9,
                    max_output_tokens=600,
                ),
            )
        except Exception as e:
            self.model = None

    def chat(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        incident_context: Optional[Dict] = None,
    ) -> str:
        """
        Send a message to Gemini or generate a context-aware intelligent response.
        Ensures NO repetitive questions and tracks all extracted entities.
        """
        ctx = incident_context or {}
        crime_category = ctx.get("crime_category") or "UPI / Payment Fraud"
        entities = ctx.get("extracted_entities") or {}

        # If Gemini model is available, try with strict context constraints
        if self.model is not None:
            try:
                known_summary = self._build_known_summary(entities, ctx)
                missing_fields = self.detect_missing_info(crime_category, entities, "")
                
                context_instruction = (
                    f"\n\n[SYSTEM STATE: Current crime category: {crime_category}. "
                    f"Already recorded facts (DO NOT ASK FOR THESE): {known_summary}. "
                    f"Still missing fields: {', '.join(missing_fields[:3]) if missing_fields else 'None, ready for review'}. "
                    f"Instructions: Acknowledge the user's latest statement, do not repeat questions already answered, "
                    f"and ask ONLY ONE targeted question for the top missing field.]"
                )

                gemini_history = []
                for msg in history[:-1]:
                    gemini_history.append({
                        "role": msg["role"],
                        "parts": [msg["content"]],
                    })

                chat_session = self.model.start_chat(history=gemini_history)
                response = chat_session.send_message(user_message + context_instruction)
                if response and response.text and response.text.strip():
                    return response.text.strip()
            except Exception:
                pass

        # Fall back to stateful conversational intelligence engine
        return self._generate_stateful_response(user_message, history, ctx)

    def _build_known_summary(self, entities: Dict, ctx: Dict) -> str:
        items = []
        if ctx.get("financial_loss"):
            items.append(f"Amount: ₹{ctx['financial_loss']:,.2f}")
        elif entities.get("amounts"):
            items.append(f"Amount: {', '.join(entities['amounts'])}")
        if entities.get("banks"):
            items.append(f"Bank: {', '.join(entities['banks'])}")
        if entities.get("payment_apps"):
            items.append(f"App: {', '.join(entities['payment_apps'])}")
        if entities.get("transaction_ids"):
            items.append(f"Txn/UTR: {', '.join(entities['transaction_ids'])}")
        if entities.get("upi_ids"):
            items.append(f"UPI ID: {', '.join(entities['upi_ids'])}")
        if entities.get("phone_numbers"):
            items.append(f"Phone: {', '.join(entities['phone_numbers'])}")
        if entities.get("dates"):
            items.append(f"Date: {', '.join(entities['dates'])}")
        return "; ".join(items) if items else "None yet"

    def _generate_stateful_response(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        incident_context: Dict,
    ) -> str:
        """
        Intelligent state-machine conversational response generator.
        - Empathizes and acknowledges specific newly provided details
        - Never asks for information that was already provided
        - Asks for the highest-priority missing field
        - Advises 1930 for critical situations
        """
        from app.ml.ner_extractor import extract_entities
        
        # Current message entities
        this_entities = extract_entities(user_message)
        # All entities so far
        all_entities = incident_context.get("extracted_entities") or {}
        crime_category = incident_context.get("crime_category") or "UPI / Payment Fraud"
        risk_level = incident_context.get("risk_level") or "MEDIUM"
        
        msg_lower = user_message.lower()

        # Check what questions were already asked in assistant history
        assistant_history_text = " ".join(
            m.get("content", "").lower() for m in history if m.get("role") in ("model", "assistant")
        )
        full_convo_lower = (" ".join(m.get("content", "") for m in history) + " " + user_message).lower()

        # 1. Acknowledgment section
        ack_parts = []
        if this_entities.get("amounts"):
            ack_parts.append(f"noted the financial loss of {', '.join(this_entities['amounts'])}")
        if this_entities.get("payment_apps") or this_entities.get("banks"):
            source = ", ".join(this_entities.get("payment_apps", []) + this_entities.get("banks", []))
            ack_parts.append(f"recorded that this occurred via {source}")
        if this_entities.get("platforms"):
            ack_parts.append(f"noted the affected platform ({', '.join(this_entities['platforms'])})")
        if this_entities.get("transaction_ids"):
            ack_parts.append(f"logged Transaction/UTR reference {', '.join(this_entities['transaction_ids'])}")
        if this_entities.get("upi_ids"):
            ack_parts.append(f"added suspect UPI ID ({', '.join(this_entities['upi_ids'])}) to the complaint")
        if this_entities.get("phone_numbers"):
            ack_parts.append(f"recorded the suspect phone number ({', '.join(this_entities['phone_numbers'])})")
        if this_entities.get("urls"):
            ack_parts.append(f"captured the suspicious link ({', '.join(this_entities['urls'])})")
        if this_entities.get("dates"):
            ack_parts.append(f"documented incident date as {', '.join(this_entities['dates'])}")

        # 2. Urgent safety advice if needed
        safety_alert = ""
        otp_signals = any(kw in msg_lower for kw in ["otp", "shared otp", "entered pin", "upi pin", "password"])
        ongoing_signals = any(kw in msg_lower for kw in ["still happening", "ongoing", "remote", "anydesk", "teamviewer"])
        
        if (otp_signals or ongoing_signals or risk_level == "CRITICAL") and "1930" not in assistant_history_text:
            safety_alert = (
                "⚠️ URGENT: If you shared an OTP, PIN, or installed any remote access software, "
                "immediately call the National Cybercrime Helpline at 1930 and contact your bank "
                "to freeze your account or card immediately to prevent further loss.\n\n"
            )

        # 3. Determine next missing field to ask (strictly category-specific)
        required_fields = MISSING_INFO_CATEGORIES.get(crime_category, MISSING_INFO_CATEGORIES["UPI / Payment Fraud"])
        
        # Entity & context mappings
        has_field = {
            "amount": bool(all_entities.get("amounts") or this_entities.get("amounts") or incident_context.get("financial_loss")),
            "bank_name": bool(all_entities.get("banks") or all_entities.get("payment_apps") or this_entities.get("banks") or this_entities.get("payment_apps")),
            "transaction_id": bool(all_entities.get("transaction_ids") or this_entities.get("transaction_ids")),
            "suspect_upi_id": bool(all_entities.get("upi_ids") or this_entities.get("upi_ids")),
            "caller_phone": bool(all_entities.get("phone_numbers") or this_entities.get("phone_numbers")),
            "incident_date": bool(all_entities.get("dates") or this_entities.get("dates")),
            "phishing_url": bool(all_entities.get("urls") or this_entities.get("urls")),
            "otp_shared": any(k in full_convo_lower for k in ["otp", "pin", "shared otp", "gave otp"]),
            "account_number": bool(all_entities.get("account_numbers") or this_entities.get("account_numbers")),
            "compromised_platform": bool(all_entities.get("platforms") or this_entities.get("platforms") or any(p in full_convo_lower for p in ["linkedin", "instagram", "facebook", "whatsapp", "telegram", "twitter", "gmail", "google", "outlook"])),
            "suspicious_activity": any(k in full_convo_lower for k in ["hacked", "password", "locked", "login", "access", "unauthorized", "stolen"]),
            "company_name": any(k in full_convo_lower for k in ["company", "agency", "hr", "recruiter", "offer"]),
            "platform_name": bool(all_entities.get("platforms") or any(k in full_convo_lower for k in ["platform", "telegram", "app", "website"])),
            "data_entered": any(k in full_convo_lower for k in ["password", "credentials", "otp", "aadhaar", "pan", "card", "details"]),
            "threat_nature": any(k in full_convo_lower for k in ["blackmail", "threat", "video", "photos", "extortion", "call"]),
            "reported_to_institution": any(k in full_convo_lower for k in ["reported", "informed", "called bank", "complained"]),
            "which_documents_misused": any(k in full_convo_lower for k in ["aadhaar", "pan", "passport", "voter", "document"]),
            "order_details": any(k in full_convo_lower for k in ["order", "product", "item", "courier", "delivery"]),
            "seller_contact": any(k in full_convo_lower for k in ["seller", "store", "shop", "contact"]),
            "impersonated_person": any(k in full_convo_lower for k in ["manager", "police", "officer", "executive", "friend"]),
            "device_details": any(k in full_convo_lower for k in ["phone", "mobile", "laptop", "pc", "computer", "android", "iphone", "windows"]),
            "ransom_demanded": any(k in full_convo_lower for k in ["ransom", "bitcoin", "crypto", "pay"]),
            "wallet_address": any(k in full_convo_lower for k in ["wallet", "address", "usdt", "btc"]),
            "profile_link": bool(all_entities.get("urls") or any(k in full_convo_lower for k in ["profile", "link", "id", "handle"])),
            "suspect_details": bool(all_entities.get("phone_numbers") or all_entities.get("upi_ids") or all_entities.get("emails")),
        }

        # Count questions already asked by assistant
        questions_asked_count = sum(
            1 for m in history
            if m.get("role") in ("model", "assistant") and "?" in m.get("content", "")
        )

        # Find first field that is missing and hasn't already been asked
        # Limit to essential required fields for this specific category (max 5)
        max_questions = min(len(required_fields), 5)
        next_question = None
        if questions_asked_count < max_questions:
            for field in required_fields:
                if not has_field.get(field, False):
                    prompt = QUESTION_PROMPTS.get(field)
                    if prompt and prompt.lower()[:30] not in assistant_history_text:
                        next_question = prompt
                        break

        # Construct response
        response_text = safety_alert

        if ack_parts:
            response_text += f"I have {', and '.join(ack_parts)}. "
        elif len(history) <= 2:
            response_text += "I understand, and I am here to help you document this incident step-by-step. "
        else:
            response_text += "Thank you for sharing those details. "

        if next_question and questions_asked_count < max_questions:
            response_text += next_question
        else:
            # Everything essential has been captured!
            response_text += (
                "All essential information for your formal complaint has been collected! "
                "I have generated your official 10-section Cybercrime Complaint draft in real time. "
                "You can review the live draft on the right panel, upload any receipts or screenshots "
                "in 'Evidence Upload', and click 'Download PDF' to file with 1930 / cybercrime.gov.in."
            )

        return response_text.strip()

    def detect_missing_info(
        self,
        crime_category: str,
        extracted_entities: Dict,
        conversation_summary: str = "",
    ) -> List[str]:
        """Determine what key information is still missing from the complaint."""
        category = crime_category or "UPI / Payment Fraud"
        required_fields = MISSING_INFO_CATEGORIES.get(category, MISSING_INFO_CATEGORIES["UPI / Payment Fraud"])
        entity_values = {k: v for k, v in (extracted_entities or {}).items() if v}
        summary_lower = (conversation_summary or "").lower()

        field_map = {
            "amount": "amounts",
            "bank_name": "banks",
            "payment_app": "payment_apps",
            "transaction_id": "transaction_ids",
            "suspect_upi_id": "upi_ids",
            "caller_phone": "phone_numbers",
            "phishing_url": "urls",
            "incident_date": "dates",
            "compromised_platform": "platforms",
        }

        missing = []
        for field in required_fields:
            mapped = field_map.get(field, field)
            has_val = bool(entity_values.get(mapped))
            if not has_val:
                if field == "compromised_platform" and any(p in summary_lower for p in ["linkedin", "instagram", "facebook", "whatsapp", "telegram", "twitter", "gmail"]):
                    has_val = True
                elif field == "suspicious_activity" and any(k in summary_lower for k in ["hacked", "password", "locked", "unauthorized", "login"]):
                    has_val = True
                elif field == "otp_shared" and ("otp" in summary_lower or "pin" in summary_lower):
                    has_val = True

            if not has_val:
                missing.append(field.replace("_", " ").title())

        return missing[:5]

    def generate_complaint_description(
        self,
        incident_data: Dict,
        conversation_text: str,
    ) -> str:
        """Generate a polished incident description paragraph."""
        if self.model is not None:
            prompt = f"""Based on this cybercrime incident data, write a clear, factual, 
and detailed incident description suitable for an official police complaint in India. 
Write in first person. Include all key facts: loss amount, bank/app, transaction IDs, 
suspect identifiers, and modus operandi. Do not add fictitious details.

Incident Data:
{json.dumps(incident_data, indent=2, default=str)}

Conversation Summary:
{conversation_text[:1000]}

Write ONLY the formal incident description paragraph."""
            try:
                response = self.model.generate_content(prompt)
                if response and response.text and response.text.strip():
                    return response.text.strip()
            except Exception:
                pass

        return self._mock_complaint_description(incident_data, conversation_text)

    def _mock_complaint_description(self, data: Dict, conversation_text: str = "") -> str:
        category = data.get("crime_category") or "Cybercrime"
        amount = data.get("financial_loss") or 0
        entities = data.get("extracted_entities") or {}

        parts = [
            f"I am filing this formal cybercrime complaint regarding a {category} incident in which I was defrauded."
        ]

        if amount > 0:
            parts.append(f"The total financial loss suffered is ₹{amount:,.2f}.")

        banks = entities.get("banks", []) or entities.get("payment_apps", [])
        if banks:
            parts.append(f"The transaction was carried out through {', '.join(banks)}.")

        txns = entities.get("transaction_ids", [])
        if txns:
            parts.append(f"The relevant transaction reference / UTR number is {', '.join(txns)}.")

        upis = entities.get("upi_ids", [])
        if upis:
            parts.append(f"The fraudulent payment was directed to the suspect UPI address: {', '.join(upis)}.")

        phones = entities.get("phone_numbers", [])
        if phones:
            parts.append(f"The suspect contacted me from phone number(s): {', '.join(phones)}.")

        urls = entities.get("urls", [])
        if urls:
            parts.append(f"The fraudulent website/link provided was: {', '.join(urls)}.")

        dates = entities.get("dates", [])
        if dates:
            parts.append(f"The incident occurred on {dates[0]}.")

        parts.append(
            "I request the cybercrime investigation cell to register this complaint, trace the beneficiary accounts, "
            "issue freeze instructions under Section 91 of CrPC / BNSS, and initiate appropriate legal action under "
            "the Information Technology Act, 2000 and relevant sections of Bharatiya Nyaya Sanhita (BNS)."
        )

        return " ".join(parts)

    def get_evidence_checklist(self, crime_category: str) -> List[str]:
        """Return category-specific evidence checklist items."""
        checklists = {
            "UPI / Payment Fraud": [
                "Screenshot of UPI transaction", "Transaction ID / UTR number",
                "Suspect's UPI ID", "Bank SMS / email notification",
                "Bank statement showing debit", "Any conversation with suspect",
                "Suspect's phone number",
            ],
            "Banking Fraud": [
                "Bank statement showing unauthorized transactions",
                "Debit/credit card details (do NOT share CVV/PIN)", "ATM CCTV request",
                "Any SMS/email alerts received", "FIR copy if applicable",
            ],
            "OTP / Social Engineering": [
                "Call recordings (if any)", "SMS showing OTP was sent",
                "Bank SMS showing debit", "Caller's phone number",
                "Bank transaction screenshot",
            ],
            "Phishing": [
                "Screenshot of phishing email/SMS", "Phishing URL",
                "Screenshots of fake website", "Bank transaction records",
                "Email headers (forward full email)",
            ],
            "Job / Employment Fraud": [
                "Fake offer letter / job posting screenshot",
                "Payment receipts / transaction screenshots",
                "Conversation with recruiter (WhatsApp/email)",
                "Job portal link or ad screenshot",
                "Suspect's phone number and email",
            ],
            "Investment Fraud": [
                "Screenshots of investment platform / app",
                "Transaction records of all investments",
                "Conversation with agent (Telegram/WhatsApp)",
                "Advertised returns / scheme details",
                "Bank statements showing transfers",
            ],
            "E-commerce Fraud": [
                "Order confirmation screenshot", "Payment receipt",
                "Seller's contact details", "Product listing screenshot",
                "Delivery tracking info (or lack thereof)",
                "Conversation with seller",
            ],
            "Cyber Extortion": [
                "Screenshots of threats/demands",
                "Suspect's contact details",
                "Any payment receipts made to extortionist",
                "Original content being threatened with (if appropriate)",
                "Call recordings if available",
            ],
            "Account Compromise": [
                "Screenshot of unauthorized activity",
                "Account recovery details", "Any suspicious login notifications",
                "Platform's support ticket reference",
            ],
            "Identity Theft": [
                "Documents misused (e.g., Aadhaar, PAN)", "Loan/account details",
                "Letter from institution confirming fraudulent account",
                "Credit report showing unauthorized credit",
            ],
            "Malware / Ransomware": [
                "Screenshot of ransom note / malware message",
                "List of affected files/systems",
                "Any email/message that led to infection",
                "Device details",
            ],
        }
        return checklists.get(crime_category, [
            "All relevant screenshots",
            "Transaction records",
            "Suspect contact details",
            "Conversation logs",
            "Any documents received",
        ])

    def _build_context_note(self, ctx: Dict) -> str:
        parts = []
        if ctx.get("crime_category"):
            parts.append(f"Detected crime type: {ctx['crime_category']}")
        if ctx.get("financial_loss"):
            parts.append(f"Financial loss: ₹{ctx['financial_loss']}")
        if ctx.get("risk_level"):
            parts.append(f"Risk level: {ctx['risk_level']}")
        if ctx.get("missing_info"):
            parts.append(f"Still needed: {', '.join(ctx['missing_info'][:3])}")
        return ". ".join(parts)




# ─── Global Singleton ──────────────────────────────────────────────────────────

_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
