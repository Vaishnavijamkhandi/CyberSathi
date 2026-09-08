"""
Cybercrime Classifier — Multi-model training and inference.
Trains Naive Bayes, Logistic Regression, SVM, Random Forest on TF-IDF features.
Also integrates DistilBERT (Hugging Face) for comparison.
Saves trained models to disk for production use.
"""

import os
import re
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import warnings
warnings.filterwarnings("ignore")


# ─── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent.parent  # backend/
MODELS_DIR = BASE_DIR / "models"
DATASET_PATH = BASE_DIR / "ml_training" / "dataset" / "cybercrime_dataset.csv"
MODELS_DIR.mkdir(exist_ok=True)


# ─── Crime Categories ──────────────────────────────────────────────────────────

CRIME_CATEGORIES = [
    "UPI / Payment Fraud",
    "Banking Fraud",
    "OTP / Social Engineering",
    "Phishing",
    "Job / Employment Fraud",
    "Investment Fraud",
    "E-commerce Fraud",
    "Social Media Fraud",
    "Account Compromise",
    "Identity Theft",
    "Impersonation",
    "Cyber Extortion",
    "Malware / Ransomware",
    "Cryptocurrency Fraud",
    "Other / Unknown",
]

# Keyword-based indicators for XAI explanation
CATEGORY_INDICATORS = {
    "UPI / Payment Fraud": ["upi", "qr code", "gpay", "phonepe", "payment request", "scan", "transfer", "wrong transfer"],
    "Banking Fraud": ["bank account", "debit card", "credit card", "atm", "sim swap", "net banking", "ifsc"],
    "OTP / Social Engineering": ["otp", "one time password", "verification code", "share otp", "bank executive", "kyc", "remote access"],
    "Phishing": ["fake website", "clicked link", "login page", "entered credentials", "email link", "sms link", "phishing url", "spoofed site", "phishing"],
    "Job / Employment Fraud": ["job offer", "registration fee", "work from home", "data entry", "offer letter", "security deposit", "employment", "internship", "intern", "part time", "tasks", "task fraud", "linkedin job", "telegram task"],
    "Investment Fraud": ["investment", "returns", "trading", "profit", "withdraw", "scheme", "mutual fund", "stock market", "telegram group", "crypto investment"],
    "E-commerce Fraud": ["ordered", "purchased", "delivery", "product", "seller", "online shopping", "not delivered", "flipkart", "amazon", "olx", "courier"],
    "Social Media Fraud": ["whatsapp", "friend asked", "facebook", "instagram", "telegram", "social media", "dating", "matrimonial", "snapchat", "fake friend"],
    "Account Compromise": ["account hacked", "password changed", "lost access", "locked out", "unauthorized login", "hacker", "hacked", "account compromised", "hijacked", "account takeover", "compromised", "stolen account", "hacked my", "someone hacked"],
    "Identity Theft": ["aadhaar", "pan card", "identity misused", "loan in my name", "credit card opened", "kyc misused"],
    "Impersonation": ["fake profile", "my photos", "fake account", "my name", "impersonating", "duplicate profile"],
    "Cyber Extortion": ["threatening", "blackmail", "pay or", "video", "photos shared", "extortion", "demand money", "nude", "sextortion"],
    "Malware / Ransomware": ["virus", "malware", "ransomware", "files encrypted", "remote access app", "apk", "downloaded app", "hacked device", "trojan"],
    "Cryptocurrency Fraud": ["bitcoin", "crypto", "usdt", "cryptocurrency", "ethereum", "crypto wallet", "blockchain", "binance"],
    "Other / Unknown": [],
}


def _match_keyword(kw: str, text_lower: str) -> bool:
    """Match keyword using whole-word regex boundaries so 'link' doesn't match 'linkedin'."""
    pattern = r"(?:\b|_)" + re.escape(kw) + r"(?:\b|_)"
    return bool(re.search(pattern, text_lower))


# ─── Text Preprocessing ────────────────────────────────────────────────────────

def preprocess_text(text: str) -> str:
    """Lowercase, remove special chars, normalize whitespace."""
    text = text.lower()
    text = re.sub(r"₹[\d,]+(?:\.\d+)?", " AMOUNT ", text)
    text = re.sub(r"\+?91?\d{10}", " PHONENUMBER ", text)
    text = re.sub(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", " EMAILADDRESS ", text)
    text = re.sub(r"https?://\S+|www\.\S+", " URL ", text)
    text = re.sub(r"\d{6,}", " LONGDIGIT ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ─── Model Building ────────────────────────────────────────────────────────────

def build_pipelines() -> Dict[str, Pipeline]:
    """Build sklearn pipelines for each model."""
    tfidf = lambda: TfidfVectorizer(
        preprocessor=preprocess_text,
        ngram_range=(1, 2),
        max_features=15000,
        min_df=1,
        sublinear_tf=True,
    )
    return {
        "Naive Bayes": Pipeline([("tfidf", tfidf()), ("clf", MultinomialNB(alpha=0.5))]),
        "Logistic Regression": Pipeline([("tfidf", tfidf()), ("clf", LogisticRegression(max_iter=1000, C=1.0, random_state=42))]),
        "SVM (Linear)": Pipeline([("tfidf", tfidf()), ("clf", LinearSVC(max_iter=2000, C=1.0, random_state=42))]),
        "Random Forest": Pipeline([("tfidf", tfidf()), ("clf", RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1))]),
    }


# ─── Training ──────────────────────────────────────────────────────────────────

def train_all_models(df: pd.DataFrame) -> Tuple[Dict, Dict, LabelEncoder]:
    """Train all models and return fitted pipelines + evaluation results."""
    X = df["complaint_text"].astype(str).tolist()
    y = df["crime_category"].astype(str).tolist()

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    pipelines = build_pipelines()
    results = {}
    fitted_models = {}

    for name, pipeline in pipelines.items():
        print(f"Training {name}...")
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(
            y_test, y_pred,
            target_names=le.classes_,
            output_dict=True,
            zero_division=0,
        )
        results[name] = {
            "accuracy": round(acc * 100, 2),
            "precision": round(report["macro avg"]["precision"] * 100, 2),
            "recall": round(report["macro avg"]["recall"] * 100, 2),
            "f1_score": round(report["macro avg"]["f1-score"] * 100, 2),
            "per_class": {
                cls: {
                    "precision": round(report[cls]["precision"] * 100, 2),
                    "recall": round(report[cls]["recall"] * 100, 2),
                    "f1": round(report[cls]["f1-score"] * 100, 2),
                }
                for cls in le.classes_ if cls in report
            },
        }
        fitted_models[name] = pipeline
        print(f"  -> Accuracy: {acc:.2%}")

    return fitted_models, results, le


def save_models(models: Dict, le: LabelEncoder, results: Dict):
    """Save all models, label encoder, and results to disk."""
    for name, model in models.items():
        safe_name = name.replace(" ", "_").replace("(", "").replace(")", "").lower()
        joblib.dump(model, MODELS_DIR / f"{safe_name}.pkl")
        print(f"Saved: {safe_name}.pkl")

    joblib.dump(le, MODELS_DIR / "label_encoder.pkl")
    joblib.dump(results, MODELS_DIR / "benchmark_results.pkl")
    print("Saved: label_encoder.pkl, benchmark_results.pkl")


# ─── Inference ─────────────────────────────────────────────────────────────────

class CrimeClassifier:
    """
    Production classifier that loads the best saved model and provides predictions.
    Falls back to keyword-based classification if models are not trained yet.
    """

    def __init__(self, preferred_model: str = "logistic_regression"):
        self.model: Optional[Pipeline] = None
        self.le: Optional[LabelEncoder] = None
        self.model_name = preferred_model
        self._load()

    def _load(self):
        """Load model from disk if available."""
        try:
            model_path = MODELS_DIR / f"{self.model_name}.pkl"
            le_path = MODELS_DIR / "label_encoder.pkl"
            if model_path.exists() and le_path.exists():
                self.model = joblib.load(model_path)
                self.le = joblib.load(le_path)
                print(f"[OK] Loaded classifier: {self.model_name}")
            else:
                print(f"Model not found at {model_path}. Using keyword fallback.")
        except Exception as e:
            print(f"Failed to load model: {e}. Using keyword fallback.")

    def _keyword_fallback(self, text: str) -> Tuple[str, float, List[str]]:
        """Keyword-based fallback classifier with word boundary matching."""
        text_lower = text.lower()
        scores = {}
        matched_indicators = {}
        for category, keywords in CATEGORY_INDICATORS.items():
            matches = [kw for kw in keywords if _match_keyword(kw, text_lower)]
            scores[category] = len(matches)
            matched_indicators[category] = matches

        best_cat = max(scores, key=scores.get)
        best_score = scores[best_cat]

        if best_score == 0:
            best_cat = "Other / Unknown"
            confidence = 0.3
        else:
            confidence = min(0.55 + (best_score * 0.15), 0.95)

        indicators = matched_indicators.get(best_cat, [])
        return best_cat, round(confidence, 2), indicators[:5]

    def predict(self, text: str) -> Dict:
        """
        Classify a cybercrime complaint text with robust hybrid ML + high-precision rule guards.
        """
        indicators = self._get_indicators(text)
        kw_cat, kw_conf, kw_indicators = self._keyword_fallback(text)

        ml_category = None
        ml_confidence = 0.0
        alternatives = []

        if self.model is not None and self.le is not None:
            try:
                processed = preprocess_text(text)
                clf = self.model.named_steps["clf"]
                tfidf_vec = self.model.named_steps["tfidf"]
                X = tfidf_vec.transform([processed])

                if hasattr(clf, "predict_proba"):
                    proba = clf.predict_proba(X)[0]
                    top_idx = np.argmax(proba)
                    ml_confidence = float(proba[top_idx])
                    ml_category = str(self.le.inverse_transform([top_idx])[0])

                    top3_idx = np.argsort(proba)[::-1][:3]
                    alternatives = [
                        {"category": str(self.le.inverse_transform([i])[0]), "confidence": round(float(proba[i]), 3)}
                        for i in top3_idx
                    ]
                else:
                    pred = clf.predict(X)[0]
                    ml_category = str(self.le.inverse_transform([pred])[0])
                    ml_confidence = 0.80
                    alternatives = [{"category": ml_category, "confidence": ml_confidence}]
            except Exception as e:
                print(f"Model prediction failed: {e}, using fallback")

        # Hybrid Decision Logic:
        # If keyword fallback matched strong specific indicators (e.g. 'hacked', 'linkedin', 'upi', 'otp'),
        # and ML is either unavailable, has low confidence (< 0.35), or ML has 0 indicators in the text while keyword has matches:
        text_lower = text.lower()
        ml_has_indicators = any(
            _match_keyword(kw, text_lower)
            for kw in CATEGORY_INDICATORS.get(ml_category or "", [])
        )

        use_keyword = False
        if kw_indicators:
            if not ml_category:
                use_keyword = True
            elif ml_confidence < 0.35:
                # ML is uncertain / guessing among diffused classes
                use_keyword = True
            elif not ml_has_indicators and len(kw_indicators) >= 1:
                # ML predicted category has zero matching indicators, but kw_cat has direct matches
                use_keyword = True

        if use_keyword and kw_cat != "Other / Unknown":
            category = kw_cat
            confidence = kw_conf
            chosen_indicators = kw_indicators
            method = "Rules/Keywords (High Confidence)"
            if not any(a.get("category") == category for a in alternatives):
                alternatives.insert(0, {"category": category, "confidence": confidence})
        elif ml_category:
            category = ml_category
            confidence = round(ml_confidence, 3)
            chosen_indicators = indicators
            method = f"ML ({self.model_name})"
        else:
            category = kw_cat
            confidence = kw_conf
            chosen_indicators = kw_indicators or indicators
            method = "keyword_fallback"

        return {
            "category": category,
            "confidence": confidence,
            "indicators": chosen_indicators,
            "alternatives": alternatives or [{"category": category, "confidence": confidence}],
            "method": method,
        }

    def _get_indicators(self, text: str) -> List[str]:
        """Extract present indicators from text for XAI explanation using word boundary matching."""
        text_lower = text.lower()
        found = []
        for category, keywords in CATEGORY_INDICATORS.items():
            for kw in keywords:
                if _match_keyword(kw, text_lower) and kw not in found:
                    found.append(kw)
        return found[:8]  # Return top 8


# ─── Global Singleton ──────────────────────────────────────────────────────────

_classifier_instance: Optional[CrimeClassifier] = None


def get_classifier() -> CrimeClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = CrimeClassifier()
    return _classifier_instance


def get_benchmark_results() -> Optional[Dict]:
    """Load saved benchmark results from disk."""
    results_path = MODELS_DIR / "benchmark_results.pkl"
    if results_path.exists():
        return joblib.load(results_path)
    return None


if __name__ == "__main__":
    # Quick test
    clf = get_classifier()
    test = "Someone called from my bank asking OTP. I gave it and ₹45000 was debited."
    result = clf.predict(test)
    print(f"Category: {result['category']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Indicators: {result['indicators']}")
