import json
import os

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"

_last_error = None


ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["sentiment", "issues", "recommendations", "summary"],
    "properties": {
        "summary": {
            "type": "string",
            "description": "One concise sentence summarizing the user's main experience.",
        },
        "sentiment": {
            "type": "object",
            "additionalProperties": False,
            "required": ["sentiment", "confidence"],
            "properties": {
                "sentiment": {"type": "string", "enum": ["Positive", "Negative", "Neutral"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "issues": {
            "type": "array",
            "minItems": 0,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["category", "score", "evidence"],
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Specific UX/product category, not limited to a fixed list.",
                    },
                    "score": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence": {
                        "type": "string",
                        "description": "Short phrase from or paraphrase of the feedback supporting the issue.",
                    },
                },
            },
        },
        "recommendations": {
            "type": "array",
            "minItems": 1,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["category", "recommendation", "priority"],
                "properties": {
                    "category": {"type": "string"},
                    "recommendation": {
                        "type": "string",
                        "description": "Specific, actionable product or UX improvement.",
                    },
                    "priority": {"type": "string", "enum": ["High", "Medium", "Low"]},
                },
            },
        },
    },
}


def _env_enabled(name, default=True):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _model_name():
    return os.environ.get("AI_UX_OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL


def _analysis_prompt(text, processed_text):
    return f"""
Analyze this user feedback for a UX/product team.

Return practical, non-generic output:
- Sentiment should reflect the user's overall emotion and confidence.
- Issues should be specific and can use any category that fits the feedback.
- Recommendations should directly address the issue, include product/design/engineering action, and avoid canned advice.
- If feedback is vague or positive, still provide a useful next step.

Original feedback:
{text.strip()}

Normalized text:
{processed_text or ""}
""".strip()


def _coerce_score(value, default=0.7):
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except (TypeError, ValueError):
        return default


def _normalize_priority(value):
    priority = str(value or "Medium").title()
    return priority if priority in {"High", "Medium", "Low"} else "Medium"


def _normalize_result(data):
    sentiment_data = data.get("sentiment") or {}
    sentiment = str(sentiment_data.get("sentiment") or "Neutral").title()
    if sentiment not in {"Positive", "Negative", "Neutral"}:
        sentiment = "Neutral"

    issues = []
    for item in data.get("issues") or []:
        category = str(item.get("category") or "General").strip()[:80]
        evidence = str(item.get("evidence") or "AI-inferred signal").strip()[:240]
        issues.append({
            "category": category or "General",
            "score": _coerce_score(item.get("score")),
            "evidence": evidence or "AI-inferred signal",
            "source": "openai",
            "model": _model_name(),
        })

    recommendations = []
    for item in data.get("recommendations") or []:
        recommendation = str(item.get("recommendation") or "").strip()
        if not recommendation:
            continue
        recommendations.append({
            "category": str(item.get("category") or "General").strip()[:80] or "General",
            "recommendation": recommendation[:500],
            "priority": _normalize_priority(item.get("priority")),
            "source": "openai",
            "model": _model_name(),
        })

    if not recommendations:
        recommendations.append({
            "category": "General",
            "recommendation": "Review this feedback with the product team and identify the smallest change that would reduce user friction.",
            "priority": "Low",
            "source": "openai",
            "model": _model_name(),
        })

    return {
        "summary": str(data.get("summary") or "").strip(),
        "sentiment": {
            "sentiment": sentiment,
            "confidence": _coerce_score(sentiment_data.get("confidence"), default=0.75),
            "source": "openai",
            "model": _model_name(),
        },
        "issues": issues,
        "recommendations": recommendations,
        "analysis_engine": {
            "source": "openai",
            "model": _model_name(),
        },
    }


def analyze_feedback_with_openai(text, processed_text=""):
    global _last_error
    if not _env_enabled("AI_UX_USE_OPENAI_ANALYSIS", default=True):
        _last_error = "OpenAI analysis is disabled."
        return None
    if not os.environ.get("OPENAI_API_KEY"):
        _last_error = "OPENAI_API_KEY is not configured."
        return None

    try:
        from openai import OpenAI

        client = OpenAI(timeout=float(os.environ.get("AI_UX_OPENAI_TIMEOUT", "20")))
        response = client.responses.create(
            model=_model_name(),
            instructions=(
                "You are a senior UX research and product analyst. "
                "Extract structured insight from feedback and generate concrete, useful recommendations."
            ),
            input=_analysis_prompt(text, processed_text),
            max_output_tokens=900,
            temperature=0.2,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "ux_feedback_analysis",
                    "schema": ANALYSIS_SCHEMA,
                    "strict": True,
                }
            },
        )
        data = json.loads(response.output_text)
        _last_error = None
        return _normalize_result(data)
    except Exception as exc:
        _last_error = f"{exc.__class__.__name__}: {exc}"
        return None


def openai_analysis_status():
    enabled = _env_enabled("AI_UX_USE_OPENAI_ANALYSIS", default=True)
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    message = None
    if not enabled:
        message = "OpenAI analysis is disabled."
    elif not has_key:
        message = "OPENAI_API_KEY is not configured."
    elif _last_error:
        message = _last_error
    return {
        "source": "openai",
        "model": _model_name(),
        "enabled": enabled,
        "available": enabled and has_key,
        "message": message,
    }
