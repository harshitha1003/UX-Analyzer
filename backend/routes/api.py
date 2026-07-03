import csv
import io
from collections import Counter, defaultdict

from flask import Blueprint, jsonify, request, Response

from database.db import DATABASE_PATH, get_db, row_to_dict, rows_to_dicts
from services.preprocessing import preprocess_text
from services.sentiment import analyze_sentiment, sentiment_engine_status
from services.ux_issue_detector import detect_ux_issues
from services.recommendation_engine import generate_recommendations
from services.reporting import rows_to_csv

api = Blueprint("api", __name__)


def log_activity(action, metadata=""):
    with get_db() as conn:
        conn.execute("INSERT INTO user_activity (action, metadata) VALUES (?, ?)", (action, metadata))


def persist_analysis(text, source="manual"):
    if not text or not text.strip():
        raise ValueError("Feedback text is required.")

    print("STEP 1: Starting preprocessing", flush=True)
    processed = preprocess_text(text)

    print("STEP 2: Starting sentiment", flush=True)
    sentiment = analyze_sentiment(text)

    print("STEP 3: Detecting issues", flush=True)
    issues = detect_ux_issues(text, processed["processed_text"])

    print("STEP 4: Generating recommendations", flush=True)
    recommendations = generate_recommendations(text, issues, sentiment)

    print("STEP 5: Writing to database", flush=True)
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO feedback (source, text, cleaned_text) VALUES (?, ?, ?)",
            (source, text.strip(), processed["cleaned_text"]),
        )
        feedback_id = cursor.lastrowid

        conn.execute(
            "INSERT INTO sentiment_results (feedback_id, sentiment, confidence) VALUES (?, ?, ?)",
            (feedback_id, sentiment["sentiment"], sentiment["confidence"]),
        )

        for issue in issues:
            conn.execute(
                "INSERT INTO ux_issues (feedback_id, category, score, evidence) VALUES (?, ?, ?, ?)",
                (feedback_id, issue["category"], issue["score"], issue["evidence"]),
            )

        for rec in recommendations:
            conn.execute(
                "INSERT INTO recommendations (feedback_id, category, recommendation, priority) VALUES (?, ?, ?, ?)",
                (feedback_id, rec["category"], rec["recommendation"], rec["priority"]),
            )

    print("STEP 6: Done", flush=True)

    return {
        "feedback_id": feedback_id,
        "text": text.strip(),
        "preprocessing": processed,
        "sentiment": sentiment,
        "issues": issues,
        "recommendations": recommendations,
    }


@api.errorhandler(Exception)
def handle_error(error):
    status = 400 if isinstance(error, ValueError) else 500
    return jsonify({"error": str(error)}), status


@api.post("/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    result = persist_analysis(payload.get("text", ""), payload.get("source", "manual"))
    log_activity("analyze", f"feedback_id={result['feedback_id']}")
    return jsonify(result), 201


@api.post("/upload")
def upload():
    file = request.files.get("file")
    if not file:
        raise ValueError("CSV file is required.")
    stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
    reader = csv.DictReader(stream)
    rows = list(reader)
    if not rows:
        raise ValueError("CSV contains no rows.")
    text_key = "text" if "text" in rows[0] else "feedback" if "feedback" in rows[0] else None
    if not text_key:
        raise ValueError("CSV must include a text or feedback column.")
    results = [persist_analysis(row[text_key], row.get("source", "csv")) for row in rows if row.get(text_key)]
    log_activity("upload", f"rows={len(results)}")
    return jsonify({"count": len(results), "results": results}), 201


@api.get("/dashboard")
def dashboard():
    with get_db() as conn:
        total_feedback = conn.execute("SELECT COUNT(*) AS count FROM feedback").fetchone()["count"]
        feedback = rows_to_dicts(conn.execute("SELECT * FROM feedback ORDER BY created_at DESC LIMIT 100"))
        sentiments = rows_to_dicts(conn.execute("SELECT sentiment, confidence, created_at FROM sentiment_results"))
        issues = rows_to_dicts(conn.execute("SELECT category, score, created_at FROM ux_issues"))
        recs = rows_to_dicts(conn.execute("SELECT category, recommendation, priority, created_at FROM recommendations ORDER BY created_at DESC LIMIT 50"))

    sentiment_counts = Counter(item["sentiment"] for item in sentiments)
    issue_counts = Counter(item["category"] for item in issues)
    trend_bucket = defaultdict(lambda: {"Positive": 0, "Negative": 0, "Neutral": 0})
    for item in sentiments:
        day = item["created_at"][:10]
        trend_bucket[day][item["sentiment"]] += 1

    total = len(sentiments)
    statistics = {
        "total_feedback": total_feedback,
        "positive_percent": round((sentiment_counts["Positive"] / total) * 100, 1) if total else 0,
        "negative_percent": round((sentiment_counts["Negative"] / total) * 100, 1) if total else 0,
        "neutral_percent": round((sentiment_counts["Neutral"] / total) * 100, 1) if total else 0,
    }

    return jsonify(
        {
            "statistics": statistics,
            "sentiment_counts": dict(sentiment_counts),
            "issue_counts": dict(issue_counts),
            "trend": [{"date": day, **counts} for day, counts in sorted(trend_bucket.items())],
            "feedback": feedback,
            "recommendations": recs,
            "heatmap": [
                {"area": "Navigation", "value": issue_counts["Navigation"]},
                {"area": "UI", "value": issue_counts["UI Design"]},
                {"area": "Performance", "value": issue_counts["Performance"]},
                {"area": "Accessibility", "value": issue_counts["Accessibility"]},
                {"area": "Bugs", "value": issue_counts["Bugs"]},
                {"area": "Usability", "value": issue_counts["Usability"]},
            ],
        }
    )


@api.get("/issues")
def issues():
    with get_db() as conn:
        rows = rows_to_dicts(
            conn.execute(
                """
                SELECT ux_issues.*, feedback.text
                FROM ux_issues
                JOIN feedback ON feedback.id = ux_issues.feedback_id
                ORDER BY ux_issues.created_at DESC
                """
            )
        )
    return jsonify(rows)


@api.get("/recommendations")
def recommendations():
    with get_db() as conn:
        rows = rows_to_dicts(
            conn.execute(
                """
                SELECT recommendations.*, feedback.text
                FROM recommendations
                JOIN feedback ON feedback.id = recommendations.feedback_id
                ORDER BY recommendations.created_at DESC
                """
            )
        )
    return jsonify(rows)


@api.get("/statistics")
def statistics():
    return dashboard()


@api.get("/export")
def export_csv():
    with get_db() as conn:
        rows = rows_to_dicts(
            conn.execute(
                """
                SELECT feedback.id, feedback.source, feedback.text, sentiment_results.sentiment,
                    sentiment_results.confidence, GROUP_CONCAT(ux_issues.category, ', ') AS issues
                FROM feedback
                LEFT JOIN sentiment_results ON sentiment_results.feedback_id = feedback.id
                LEFT JOIN ux_issues ON ux_issues.feedback_id = feedback.id
                GROUP BY feedback.id
                ORDER BY feedback.created_at DESC
                """
            )
        )
    return Response(
        rows_to_csv(rows),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=ux-feedback-results.csv"},
    )


@api.get("/health")
def health():
    with get_db() as conn:
        conn.execute("SELECT 1")
        feedback_count = conn.execute("SELECT COUNT(*) AS count FROM feedback").fetchone()["count"]
    return jsonify({
        "status": "ok",
        "database": "ok",
        "feedback_count": feedback_count,
        "db_path": DATABASE_PATH,
        "sentiment_engine": sentiment_engine_status(),
    })


@api.delete("/dashboard/clear")
def clear_dashboard():
    with get_db() as conn:
        conn.execute("DELETE FROM recommendations")
        conn.execute("DELETE FROM ux_issues")
        conn.execute("DELETE FROM sentiment_results")
        conn.execute("DELETE FROM feedback")
        conn.execute("DELETE FROM user_activity")

        # Reset auto increment (ignore if sqlite_sequence doesn't exist)
        try:
            conn.execute("DELETE FROM sqlite_sequence")
        except Exception:
            pass

        conn.commit()

    return jsonify({
        "success": True,
        "message": "Dashboard cleared successfully."
    }), 200
