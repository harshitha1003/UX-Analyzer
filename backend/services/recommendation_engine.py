PLAYBOOKS = {
    "Checkout & Payment": {
        "action": "Redesign the payment failure path so users see the exact failed step, a plain-language reason, and a retry option without losing checkout progress.",
        "validation": "Track payment retry success rate, checkout abandonment, and support tickets tagged payment failure.",
    },
    "Form Recovery": {
        "action": "Persist form state locally or server-side, show field-level validation before submit, and restore entered values after errors or navigation.",
        "validation": "Test failed-submit, refresh, back-button, and session-timeout cases with partially completed forms.",
    },
    "Error Messaging": {
        "action": "Replace vague failure states with actionable messages that explain what happened, what the user can do next, and when to contact support.",
        "validation": "Review the top error states and confirm each one has a user-facing recovery path.",
    },
    "Account & Authentication": {
        "action": "Simplify the authentication flow by clarifying the required credential step, preserving user progress, and adding recovery options for password or OTP failures.",
        "validation": "Measure login completion, OTP resend usage, and failed-session loops.",
    },
    "Search & Discovery": {
        "action": "Tune search and filtering around the user's vocabulary, add empty-state guidance, and expose the most relevant filters earlier in the flow.",
        "validation": "Compare zero-result rate, search refinement rate, and task completion before and after the change.",
    },
    "Navigation & Information Architecture": {
        "action": "Map the reported journey, rename confusing destinations, and add visible orientation cues such as current location, back paths, or breadcrumbs.",
        "validation": "Run a task test where users must find the mentioned destination without assistance.",
    },
    "Upload & Import": {
        "action": "Make the import flow tolerant of imperfect files by validating rows before submission, showing row-level errors, and offering a corrected-file preview.",
        "validation": "Test empty rows, missing columns, large files, duplicate rows, and malformed CSV values.",
    },
    "Performance & Reliability": {
        "action": "Instrument the affected flow, identify the slowest client and API spans, and add resilient loading, retry, or timeout states.",
        "validation": "Track p95 load time, crash/error rate, and user retries for the reported flow.",
    },
    "Mobile & Responsive Layout": {
        "action": "Audit the screen at common mobile breakpoints, then fix tap targets, scroll behavior, sticky actions, and keyboard overlap.",
        "validation": "Retest on small phones, tablets, and landscape orientation before release.",
    },
    "Accessibility": {
        "action": "Fix keyboard navigation, focus order, labels, contrast, and screen-reader announcements for the affected interaction.",
        "validation": "Run automated accessibility checks and one manual keyboard-only pass through the flow.",
    },
    "Visual Hierarchy & Controls": {
        "action": "Increase the prominence of the primary action, reduce competing visual noise, and make control states unmistakable.",
        "validation": "Use a quick first-click or five-second test to confirm users notice the intended action.",
    },
    "Data Accuracy & Trust": {
        "action": "Audit the data source, sync timing, and display logic for the reported information, then expose status or freshness where users need trust.",
        "validation": "Add regression checks for stale, missing, duplicate, and incorrect data states.",
    },
    "Onboarding & Guidance": {
        "action": "Add contextual guidance at the moment of confusion, using short inline copy, examples, or progressive hints instead of a separate tutorial.",
        "validation": "Measure first-time task completion and help-link usage after the guidance is added.",
    },
    "General Usability Friction": {
        "action": "Review the exact task behind this feedback, remove avoidable steps, and clarify the next action at each decision point.",
        "validation": "Run a small usability test and compare completion rate, time on task, and user confidence.",
    },
    "Qualitative Feedback Review": {
        "action": "Cluster this comment with similar feedback, identify the user goal, and convert the repeated pattern into a testable product hypothesis.",
        "validation": "Look for frequency across support tickets, reviews, analytics, and session recordings.",
    },
}


def priority_for(sentiment, score):
    if sentiment == "Negative" and score >= 0.75:
        return "High"
    if sentiment == "Negative" or score >= 0.7:
        return "Medium"
    return "Low"


def _issue_context(issue):
    evidence = (issue.get("evidence") or "").strip()
    signals = issue.get("signals") or []
    parts = []
    if evidence:
        parts.append(f"Use this evidence as the acceptance target: \"{evidence}\"")
    if signals:
        parts.append(f"Signals detected: {', '.join(signals[:4])}")
    return " ".join(parts)


def _playbook_for(category):
    if category in PLAYBOOKS:
        return PLAYBOOKS[category]
    return {
        "action": f"Investigate the reported {category.lower()} issue with product, design, and engineering, then ship the smallest measurable fix.",
        "validation": "Define one success metric and verify the fix against similar feedback after release.",
    }


def generate_recommendations(text, issues, sentiment_result):
    if not issues:
        issues = [{
            "category": "Qualitative Feedback Review",
            "score": 0.5,
            "evidence": (text or "").strip()[:180],
            "signals": [],
        }]

    sentiment = sentiment_result.get("sentiment", "Neutral")
    recommendations = []
    seen = set()

    for issue in issues:
        category = issue.get("category", "Qualitative Feedback Review")
        if category in seen:
            continue
        seen.add(category)

        playbook = _playbook_for(category)
        context = _issue_context(issue)
        recommendation = f"{playbook['action']} {context} Validate by: {playbook['validation']}"

        recommendations.append({
            "category": category,
            "recommendation": recommendation.strip(),
            "priority": priority_for(sentiment, issue.get("score", 0.5)),
            "source": "dynamic-local",
            "model": "issue-playbook-v2",
        })

    return recommendations[:6]
