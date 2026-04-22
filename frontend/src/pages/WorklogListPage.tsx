import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  RemittanceFilter,
  WorkLogSummary,
  fetchWorklogs,
  generateRemittances,
} from "../api";
import { formatUsd } from "../util";

const defaultPeriod = () => ({
  start: "2025-11-01",
  end: "2025-11-30",
});

export default function WorklogListPage() {
  const [period, setPeriod] = useState(defaultPeriod);
  const [status, setStatus] = useState<RemittanceFilter | "">("");
  const [userId, setUserId] = useState("");
  const [rows, setRows] = useState<WorkLogSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [excludeWl, setExcludeWl] = useState<Record<number, boolean>>({});
  const [excludeUser, setExcludeUser] = useState<Record<number, boolean>>({});

  const [reviewOpen, setReviewOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [resultMsg, setResultMsg] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr(null);
      try {
        const data = await fetchWorklogs({
          remittance_status: status || undefined,
          user_id: userId ? Number(userId) : undefined,
          period_start: period.start,
          period_end: period.end,
        });
        if (!cancelled) setRows(data);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [period.start, period.end, status, userId]);

  const uniqueUsers = useMemo(() => {
    const m = new Map<number, string>();
    for (const r of rows) m.set(r.user_id, r.freelancer_name);
    return Array.from(m.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [rows]);

  const eligibleRows = useMemo(
    () =>
      rows.filter(
        (r) =>
          !excludeWl[r.id] &&
          !excludeUser[r.user_id] &&
          r.remittance_status === "UNREMITTED" &&
          r.unremitted_amount_cents > 0
      ),
    [rows, excludeWl, excludeUser]
  );

  const previewTotal = useMemo(
    () => eligibleRows.reduce((s, r) => s + r.unremitted_amount_cents, 0),
    [eligibleRows]
  );

  async function runSettlement() {
    setSubmitting(true);
    setResultMsg(null);
    try {
      const exclude_worklog_ids = Object.entries(excludeWl)
        .filter(([, v]) => v)
        .map(([k]) => Number(k));
      const exclude_user_ids = Object.entries(excludeUser)
        .filter(([, v]) => v)
        .map(([k]) => Number(k));
      const res = await generateRemittances({
        period_start: period.start,
        period_end: period.end,
        exclude_worklog_ids,
        exclude_user_ids,
      });
      const ok = res.remittances.filter((r) => r.status === "completed").length;
      const failed = res.remittances.filter((r) => r.status === "failed").length;
      setResultMsg(
        `Created ${res.remittances.length} remittance(s): ${ok} completed, ${failed} failed.`
      );
      setReviewOpen(false);
      const data = await fetchWorklogs({
        remittance_status: status || undefined,
        user_id: userId ? Number(userId) : undefined,
        period_start: period.start,
        period_end: period.end,
      });
      setRows(data);
    } catch (e) {
      setResultMsg(e instanceof Error ? e.message : "Settlement failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <section className="panel">
        <h2>Filters</h2>
        <div className="grid-filters">
          <label className="field">
            Period start
            <input
              type="date"
              value={period.start}
              onChange={(e) => setPeriod((p) => ({ ...p, start: e.target.value }))}
            />
          </label>
          <label className="field">
            Period end
            <input
              type="date"
              value={period.end}
              onChange={(e) => setPeriod((p) => ({ ...p, end: e.target.value }))}
            />
          </label>
          <label className="field">
            Remittance status
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as RemittanceFilter | "")}
            >
              <option value="">All</option>
              <option value="UNREMITTED">UNREMITTED</option>
              <option value="REMITTED">REMITTED</option>
            </select>
          </label>
          <label className="field">
            Freelancer id (optional)
            <input
              placeholder="e.g. 1"
              value={userId}
              onChange={(e) => setUserId(e.target.value.replace(/\D/g, ""))}
            />
          </label>
        </div>
        <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
          Amounts in the table are scoped to the selected period. Unremitted totals include only
          approved segments not yet paid on a completed remittance.
        </p>
      </section>

      <section className="panel">
        <h2>Exclude from next batch</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Checked worklogs and freelancers are omitted from{" "}
          <span className="mono">POST /generate-remittances</span> for this browser session.
        </p>
        <div className="stack" style={{ marginTop: "0.75rem" }}>
          {uniqueUsers.map(([uid, name]) => (
            <label key={uid} className="checkbox-line">
              <input
                type="checkbox"
                checked={!!excludeUser[uid]}
                onChange={(e) =>
                  setExcludeUser((s) => ({ ...s, [uid]: e.target.checked }))
                }
              />
              Exclude all worklogs for <strong>{name}</strong>{" "}
              <span className="muted mono">(user {uid})</span>
            </label>
          ))}
        </div>
      </section>

      <section className="panel">
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "0.75rem",
          }}
        >
          <h2 style={{ margin: 0 }}>Worklogs</h2>
          <div className="row-actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setReviewOpen(true)}
              disabled={eligibleRows.length === 0}
            >
              Review payment batch
            </button>
          </div>
        </div>
        {resultMsg && <p className="error" style={{ color: "var(--accent)" }}>{resultMsg}</p>}
        {err && <p className="error">{err}</p>}
        {loading ? (
          <p className="muted">Loading…</p>
        ) : (
          <div className="table-wrap" style={{ marginTop: "1rem" }}>
            <table>
              <thead>
                <tr>
                  <th />
                  <th>Task</th>
                  <th>Freelancer</th>
                  <th>Hours</th>
                  <th>Period total</th>
                  <th>Unremitted</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <input
                        type="checkbox"
                        title="Exclude this worklog from settlement"
                        checked={!!excludeWl[r.id]}
                        disabled={!!excludeUser[r.user_id]}
                        onChange={(e) =>
                          setExcludeWl((s) => ({ ...s, [r.id]: e.target.checked }))
                        }
                      />
                    </td>
                    <td>{r.task_title}</td>
                    <td>
                      {r.freelancer_name}{" "}
                      <span className="muted mono" style={{ fontSize: "0.8em" }}>
                        #{r.user_id}
                      </span>
                    </td>
                    <td className="mono">{Number(r.total_hours).toFixed(2)}</td>
                    <td className="mono">{formatUsd(r.amount_cents)}</td>
                    <td className="mono">{formatUsd(r.unremitted_amount_cents)}</td>
                    <td>
                      <span
                        className={
                          r.remittance_status === "REMITTED" ? "pill pill-ok" : "pill pill-warn"
                        }
                      >
                        {r.remittance_status}
                      </span>
                    </td>
                    <td>
                      <Link to={`/worklogs/${r.id}`}>Details</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {reviewOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(5, 10, 14, 0.72)",
            zIndex: 19,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
          }}
          role="presentation"
          onClick={() => !submitting && setReviewOpen(false)}
        >
        <div
          className="panel"
          style={{
            position: "relative",
            maxWidth: "640px",
            maxHeight: "min(90vh, 720px)",
            overflow: "auto",
            zIndex: 20,
            width: "100%",
          }}
          role="dialog"
          aria-modal="true"
          onClick={(e) => e.stopPropagation()}
        >
          <h2>Confirm settlement</h2>
          <p className="muted">
            Period <span className="mono">{period.start}</span> →{" "}
            <span className="mono">{period.end}</span>. Retroactive adjustments pending for a user
            are applied on the next successful remittance (see backend seed for an example).
          </p>
          <div className="review-grid" style={{ marginTop: "1rem" }}>
            <div className="stat">
              <div className="label">Worklogs in batch</div>
              <div className="value">{eligibleRows.length}</div>
            </div>
            <div className="stat">
              <div className="label">Unremitted total (period, filtered)</div>
              <div className="value">{formatUsd(previewTotal)}</div>
            </div>
          </div>
          <div className="table-wrap" style={{ marginTop: "1rem" }}>
            <table>
              <thead>
                <tr>
                  <th>Freelancer</th>
                  <th>Task</th>
                  <th>Unremitted</th>
                </tr>
              </thead>
              <tbody>
                {eligibleRows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.freelancer_name}</td>
                    <td>{r.task_title}</td>
                    <td className="mono">{formatUsd(r.unremitted_amount_cents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row-actions" style={{ marginTop: "1.25rem" }}>
            <button
              type="button"
              className="btn btn-primary"
              disabled={submitting}
              onClick={() => void runSettlement()}
            >
              {submitting ? "Running…" : "Confirm & generate remittances"}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={submitting}
              onClick={() => setReviewOpen(false)}
            >
              Cancel
            </button>
          </div>
        </div>
        </div>
      )}
    </>
  );
}
