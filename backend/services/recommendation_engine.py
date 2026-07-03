RECOMMENDATIONS = {
    "Navigation": [
        "Audit the reported journey, reduce unnecessary path choices, and rename confusing navigation labels using user language.",
        "Add stronger wayfinding cues such as visible back paths, current-page state, breadcrumbs, or clearer search entry points.",
    ],
    "Performance": [
        "Measure the affected flow with real-device performance traces, then optimize slow API calls, heavy assets, and blocking UI states.",
        "Add skeleton or progress states where waits are unavoidable so users understand the app is still working.",
    ],
    "UI Design": [
        "Tighten the visual hierarchy around the affected controls, make primary actions more prominent, and standardize spacing and labels.",
        "Run a quick design review for contrast, density, alignment, and affordance issues in the mentioned screen.",
    ],
    "Accessibility": [
        "Test the affected experience with keyboard and screen-reader flows, then fix labels, focus order, contrast, and text sizing.",
        "Add accessibility checks to the release process for this area so similar regressions are caught earlier.",
    ],
    "Bugs": [
        "Create a reproducible defect ticket from this feedback, add a regression test, and improve the recovery message for users.",
        "Instrument the affected action with error logging so the team can identify frequency, device patterns, and failed states.",
    ],
    "Usability": [
        "Map the user's task step by step, remove avoidable decisions, and add inline guidance where users hesitate.",
        "Validate the revised flow with a small usability test focused on completion rate and time to success.",
    ],
}


def priority_for(sentiment, score):
    if sentiment == "Negative" and score >= 0.75:
        return "High"
    if sentiment == "Negative" or score >= 0.7:
        return "Medium"
    return "Low"


def generate_recommendations(text, issues, sentiment_result):
    if not issues:
        return [
            {
                "category": "General",
                "recommendation": "Cluster this feedback with similar comments, identify the user's goal, and review whether a small UX improvement could reduce future friction.",
                "priority": "Low",
                "source": "local-fallback",
                "model": "adaptive-rules",
            }
        ]
    sentiment = sentiment_result.get("sentiment", "Neutral")
    recommendations = []
    for issue in issues:
        category = issue["category"]
        templates = RECOMMENDATIONS.get(category, RECOMMENDATIONS["Usability"])
        template = templates[0] if sentiment == "Negative" or issue["score"] >= 0.7 else templates[-1]
        evidence = issue.get("evidence")
        if evidence:
            recommendation = f"{template} Evidence to inspect: {evidence}."
        else:
            recommendation = template
        recommendations.append({
            "category": category,
            "recommendation": recommendation,
            "priority": priority_for(sentiment, issue["score"]),
            "source": "local-fallback",
            "model": "adaptive-rules",
        })
    return recommendations
