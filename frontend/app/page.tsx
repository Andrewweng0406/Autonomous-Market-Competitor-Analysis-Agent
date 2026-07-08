"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AnalysisDepth,
  SubjectType,
  TaskStatusResponse,
  startAnalysis,
  subscribeToStream,
  pollStatus,
} from "@/lib/api";

const STATUS_LABEL: Record<TaskStatusResponse["status"], string> = {
  pending: "Queued",
  in_progress: "Researching",
  completed: "Complete",
  failed: "Failed",
};

const STATUS_COLOR: Record<TaskStatusResponse["status"], string> = {
  pending: "bg-slate-200 text-slate-700",
  in_progress: "bg-amber-100 text-amber-800",
  completed: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-800",
};

export default function HomePage() {
  const [subject, setSubject] = useState("");
  const [subjectType, setSubjectType] = useState<SubjectType>("idea");
  const [depth, setDepth] = useState<AnalysisDepth>("standard");
  const [additionalContext, setAdditionalContext] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatusResponse | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
      abortRef.current?.abort();
    };
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!subject.trim() || submitting) return;

    eventSourceRef.current?.close();
    abortRef.current?.abort();

    setSubmitting(true);
    setSubmitError(null);
    setTaskStatus(null);

    try {
      const { task_id } = await startAnalysis({
        subject: subject.trim(),
        subject_type: subjectType,
        depth,
        additional_context: additionalContext.trim() || null,
      });

      // Prefer live SSE updates; the stream degrades gracefully because the
      // UI only depends on `taskStatus`, which the polling fallback also sets.
      const source = subscribeToStream(
        task_id,
        (status) => setTaskStatus(status),
        () => {
          // SSE dropped (e.g. proxy buffering) — fall back to polling.
          source.close();
          const controller = new AbortController();
          abortRef.current = controller;
          void pollStatus(task_id, setTaskStatus, { signal: controller.signal });
        }
      );
      eventSourceRef.current = source;
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  const report = taskStatus?.result;
  const isRunning =
    taskStatus?.status === "pending" || taskStatus?.status === "in_progress";

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Autonomous Market &amp; Competitor Analysis Agent
        </h1>
        <p className="mt-2 text-slate-600">
          Describe a business idea, product, or company. The agent will research
          the live web, then return a structured SWOT and competitor analysis.
        </p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Business idea, product, or company
          </label>
          <textarea
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            required
            rows={3}
            placeholder="e.g. A subscription box that delivers artisanal coffee from small-batch roasters"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Subject type
            </label>
            <select
              value={subjectType}
              onChange={(e) => setSubjectType(e.target.value as SubjectType)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="idea">Business idea</option>
              <option value="product">Product concept</option>
              <option value="company">Existing company</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Analysis depth
            </label>
            <select
              value={depth}
              onChange={(e) => setDepth(e.target.value as AnalysisDepth)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="quick">Quick</option>
              <option value="standard">Standard</option>
              <option value="deep">Deep</option>
            </select>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Additional context <span className="text-slate-400">(optional)</span>
          </label>
          <textarea
            value={additionalContext}
            onChange={(e) => setAdditionalContext(e.target.value)}
            rows={2}
            placeholder="Target market, geography, budget constraints, etc."
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || isRunning}
          className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting || isRunning ? "Running analysis..." : "Analyze"}
        </button>

        {submitError && (
          <p className="text-sm text-red-600">{submitError}</p>
        )}
      </form>

      {taskStatus && (
        <section className="mt-8 space-y-6">
          <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3">
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_COLOR[taskStatus.status]}`}
            >
              {STATUS_LABEL[taskStatus.status]}
            </span>
            <span className="text-sm text-slate-600">
              {taskStatus.progress ?? "Waiting for the agent to start..."}
            </span>
            {isRunning && (
              <span className="ml-auto h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900" />
            )}
          </div>

          {taskStatus.status === "failed" && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <p className="font-semibold">Analysis failed</p>
              <p className="mt-1">{taskStatus.error}</p>
            </div>
          )}

          {report && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-slate-900">
                  Report: {report.subject}
                </h2>
                <button
                  onClick={() => setShowRawJson((v) => !v)}
                  className="text-xs font-medium text-slate-500 underline hover:text-slate-700"
                >
                  {showRawJson ? "Show formatted report" : "Show raw JSON"}
                </button>
              </div>

              {showRawJson ? (
                <pre className="overflow-x-auto rounded-lg border border-slate-200 bg-slate-900 p-4 text-xs text-slate-100">
                  {JSON.stringify(report, null, 2)}
                </pre>
              ) : (
                <article className="prose prose-slate max-w-none rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {report.markdown_report}
                  </ReactMarkdown>
                </article>
              )}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
