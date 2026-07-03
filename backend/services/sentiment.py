import math
import os
import re

_classifier = None
_classifier_error = None

DEFAULT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"
MODEL_ALIASES = {
    "distillbert-base-uncased-finetuned-sst-2-emglish": DEFAULT_MODEL,
    "distilbert-base-uncased-finetuned-sst-2-emglish": DEFAULT_MODEL,
    "distillbert-base-uncased-finetuned-sst-2-english": DEFAULT_MODEL,
}

POSITIVE_TERMS = {
    "love", "great", "fast", "easy", "smooth", "helpful", "excellent", "clear",
    "intuitive", "good", "amazing", "perfect", "useful", "reliable"
}
NEGATIVE_TERMS = {
    "bad", "slow", "confusing", "crash", "broken", "bug", "hard", "difficult",
    "annoying", "hate", "terrible", "poor", "inaccessible", "lag", "freeze",
    "unusable", "frustrating", "error"
}


def _env_enabled(name, default=True):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _sentiment_model_name():
    configured = os.environ.get("AI_UX_SENTIMENT_MODEL", DEFAULT_MODEL).strip()
    normalized = configured.lower()
    return MODEL_ALIASES.get(normalized, configured or DEFAULT_MODEL)


def _load_classifier():
    global _classifier, _classifier_error
    if _classifier is not None:
        return _classifier
    if not _env_enabled("AI_UX_USE_TRANSFORMER_SENTIMENT", default=False):
        _classifier = False
        return _classifier
    try:
        from transformers import pipeline

        _classifier = pipeline(
            "sentiment-analysis",
            model=_sentiment_model_name(),
            truncation=True,
        )
        _classifier_error = None
    except Exception:
        _classifier_error = "Transformer sentiment model is unavailable; using lexical fallback."
        _classifier = False
    return _classifier


def _fallback_sentiment(text):
    words = set(re.findall(r"[a-z']+", (text or "").lower()))
    positive = len(words & POSITIVE_TERMS)
    negative = len(words & NEGATIVE_TERMS)
    if positive == negative:
        return {
            "sentiment": "Neutral",
            "confidence": 0.62,
            "source": "fallback",
            "model": "lexical-rules",
        }
    sentiment = "Positive" if positive > negative else "Negative"
    gap = abs(positive - negative)
    confidence = min(0.93, 0.62 + math.log1p(gap) / 3)
    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 2),
        "source": "fallback",
        "model": "lexical-rules",
    }


def analyze_sentiment(text):
    classifier = _load_classifier()
    if not classifier:
        return _fallback_sentiment(text)

    try:
        result = classifier(text[:512])[0]
        label = result.get("label", "").upper()
        sentiment = "Positive" if label == "POSITIVE" else "Negative" if label == "NEGATIVE" else "Neutral"
        return {
            "sentiment": sentiment,
            "confidence": round(float(result.get("score", 0.0)), 2),
            "source": "transformer",
            "model": _sentiment_model_name(),
        }
    except Exception:
        return _fallback_sentiment(text)


def sentiment_engine_status():
    if _classifier:
        return {
            "source": "transformer",
            "model": _sentiment_model_name(),
            "available": True,
        }
    transformer_enabled = _env_enabled("AI_UX_USE_TRANSFORMER_SENTIMENT", default=False)
    return {
        "source": "fallback",
        "model": "lexical-rules",
        "configured_model": _sentiment_model_name(),
        "available": True,
        "transformer_enabled": transformer_enabled,
        "message": _classifier_error or (
            "Transformer sentiment is enabled but has not been loaded yet."
            if transformer_enabled else
            "Transformer sentiment is disabled; lexical fallback is active."
        ),
    }
