import re


ISSUE_PATTERNS = {
    "Checkout & Payment": [
        "checkout", "payment", "pay", "card", "billing", "invoice", "coupon",
        "refund", "subscription", "order total", "purchase"
    ],
    "Form Recovery": [
        "form", "field", "input", "refill", "retype", "lost data", "validation",
        "submit", "save draft", "dropdown"
    ],
    "Error Messaging": [
        "error", "message", "without saying", "unclear", "failed", "fail",
        "why", "warning", "alert", "blank", "nothing happens"
    ],
    "Account & Authentication": [
        "login", "log in", "sign in", "signup", "password", "otp", "verification",
        "account", "session", "logout", "locked"
    ],
    "Search & Discovery": [
        "search", "filter", "sort", "find", "results", "recommendation",
        "discover", "browse", "category"
    ],
    "Navigation & Information Architecture": [
        "navigate", "navigation", "menu", "back", "flow", "journey", "tab",
        "breadcrumb", "page", "screen", "order history"
    ],
    "Upload & Import": [
        "upload", "csv", "import", "file", "attachment", "download", "export",
        "row", "spreadsheet"
    ],
    "Performance & Reliability": [
        "slow", "lag", "load", "loading", "freeze", "crash", "timeout", "delay",
        "hang", "stuck", "keeps spinning"
    ],
    "Mobile & Responsive Layout": [
        "mobile", "phone", "tablet", "responsive", "small screen", "touch",
        "scroll", "viewport", "keyboard covers"
    ],
    "Accessibility": [
        "accessibility", "contrast", "screen reader", "keyboard", "voice",
        "small text", "blind", "caption", "aria", "focus"
    ],
    "Visual Hierarchy & Controls": [
        "button", "color", "layout", "font", "clutter", "visual", "icon",
        "spacing", "hidden", "hard to see"
    ],
    "Data Accuracy & Trust": [
        "wrong", "incorrect", "missing", "duplicate", "outdated", "sync",
        "status", "tracking", "history", "not updated"
    ],
    "Onboarding & Guidance": [
        "onboarding", "tutorial", "guide", "help", "tooltip", "instructions",
        "learn", "confused", "first time", "how to"
    ],
}


GENERIC_FRICTION = [
    "hard", "difficult", "frustrating", "annoying", "confusing", "complicated",
    "unusable", "bad experience", "hate"
]


def _sentences(text):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text or "") if part.strip()]


def _evidence_for(text, terms):
    lowered = (text or "").lower()
    sentences = _sentences(text)
    matched_terms = [term for term in terms if term in lowered]
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if any(term in sentence_lower for term in matched_terms):
            return sentence[:180]
    return ", ".join(matched_terms[:5]) or "inferred from feedback wording"


def _score(matches, has_generic_friction):
    base = 0.55 + (0.08 * len(matches))
    if has_generic_friction:
        base += 0.08
    return round(min(0.96, base), 2)


def detect_ux_issues(text, processed_text=""):
    haystack = f"{text or ''} {processed_text or ''}".lower()
    has_generic_friction = any(term in haystack for term in GENERIC_FRICTION)
    matches = []

    for category, terms in ISSUE_PATTERNS.items():
        matched_terms = [term for term in terms if term in haystack]
        if not matched_terms:
            continue
        matches.append({
            "category": category,
            "score": _score(matched_terms, has_generic_friction),
            "evidence": _evidence_for(text, matched_terms),
            "signals": matched_terms[:6],
            "source": "dynamic-local",
        })

    if not matches and has_generic_friction:
        matches.append({
            "category": "General Usability Friction",
            "score": 0.66,
            "evidence": _evidence_for(text, GENERIC_FRICTION),
            "signals": [term for term in GENERIC_FRICTION if term in haystack][:6],
            "source": "dynamic-local",
        })

    if not matches and (text or "").strip():
        matches.append({
            "category": "Qualitative Feedback Review",
            "score": 0.5,
            "evidence": (text or "").strip()[:180],
            "signals": [],
            "source": "dynamic-local",
        })

    return sorted(matches, key=lambda item: item["score"], reverse=True)[:6]
