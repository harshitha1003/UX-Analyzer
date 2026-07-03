import { useState } from "react";
import { AlertCircle, CheckCircle2, Lightbulb } from "lucide-react";
import LoadingButton from "../components/LoadingButton.jsx";
import { analyzeFeedback, getApiErrorMessage } from "../services/api.js";

export default function AnalyzeFeedback() {
  const [text, setText] = useState("The app takes too long to load and the navigation is confusing.");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleAnalyze(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await analyzeFeedback(text);
      setResult(data);
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to analyze feedback."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft dark:border-slate-800 dark:bg-slate-900">
        <h1 className="text-2xl font-bold">Analyze Feedback</h1>
        <form className="mt-5 space-y-4" onSubmit={handleAnalyze}>
          <label className="block">
            <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">Feedback text</span>
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={10}
              className="focus-ring mt-2 w-full resize-none rounded-lg border border-slate-300 bg-white p-3 text-sm leading-6 dark:border-slate-700 dark:bg-slate-950"
              placeholder="Paste app reviews, survey responses, or support comments..."
            />
          </label>
          {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:bg-rose-950 dark:text-rose-200">{error}</p>}
          <LoadingButton loading={loading} type="submit" disabled={!text.trim()}>
            Analyze
          </LoadingButton>
        </form>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-xl font-bold">Analysis Result</h2>
        {!result ? (
          <p className="mt-4 text-slate-600 dark:text-slate-300">Run an analysis to see sentiment, UX issues, and recommendations.</p>
        ) : (
          <div className="mt-5 space-y-5">
            <div className="rounded-lg bg-slate-100 p-4 dark:bg-slate-800">
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Sentiment</p>
              <p className="mt-1 text-2xl font-bold">
                {result.sentiment.sentiment} <span className="text-base text-slate-500">({result.sentiment.confidence})</span>
              </p>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                {result.sentiment.source === "transformer" ? "AI model" : "Fallback"}: {result.sentiment.model}
              </p>
            </div>

            <div>
              <h3 className="mb-3 flex items-center gap-2 font-bold"><AlertCircle size={18} /> Detected UX Issues</h3>
              <div className="space-y-2">
                {result.issues.length ? result.issues.map((issue) => (
                  <div key={issue.category} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-semibold">{issue.category}</span>
                      <span className="text-sm text-slate-500">{issue.score}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Evidence: {issue.evidence}</p>
                  </div>
                )) : <p className="text-sm text-slate-500">No specific UX issue detected.</p>}
              </div>
            </div>

            <div>
              <h3 className="mb-3 flex items-center gap-2 font-bold"><Lightbulb size={18} /> Recommendations</h3>
              <div className="space-y-2">
                {result.recommendations.map((rec) => (
                  <div key={`${rec.category}-${rec.recommendation}`} className="rounded-lg bg-emerald-50 p-3 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100">
                    <p className="font-semibold">{rec.category} · {rec.priority}</p>
                    <p className="mt-1 text-sm">{rec.recommendation}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2 text-sm text-slate-500">
              <CheckCircle2 size={16} /> Saved to SQLite.
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
