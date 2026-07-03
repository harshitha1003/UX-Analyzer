# AI-Powered UX Feedback Analyzer API

Base URL: `http://localhost:5000`

## POST /analyze

Analyze one feedback comment.

Request:

```json
{
  "text": "The navigation is confusing.",
  "source": "manual"
}
```

Response:

```json
{
  "feedback_id": 1,
  "sentiment": {
    "sentiment": "Negative",
    "confidence": 0.92,
    "source": "openai",
    "model": "gpt-4.1-mini"
  },
  "issues": [
    {
      "category": "Checkout Flow",
      "score": 0.86,
      "evidence": "payment failed without explaining why"
    }
  ],
  "recommendations": [
    {
      "category": "Checkout Flow",
      "recommendation": "Show a specific payment error, keep the user's form data intact, and offer a retry path with alternate payment options.",
      "priority": "High"
    }
  ],
  "analysis_engine": {
    "source": "openai",
    "model": "gpt-4.1-mini"
  }
}
```

## POST /upload

Upload a CSV file with a `text` or `feedback` column.

Form field: `file`

Response:

```json
{
  "count": 8,
  "results": []
}
```

## GET /dashboard

Returns overview card statistics, chart datasets, recent feedback, recommendations, and heatmap data.

## GET /issues

Returns detected UX issues joined with feedback text.

## GET /recommendations

Returns generated UX recommendations joined with feedback text.

## GET /statistics

Alias for dashboard statistics payload.

## GET /export

Downloads analyzed results as `ux-feedback-results.csv`.

## GET /health

Returns service health, OpenAI analysis availability, and local sentiment engine status.
