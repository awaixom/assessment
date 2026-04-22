import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { WorkLogDetail, fetchWorklog, patchTimeEntry } from "../api";
import { formatUsd } from "../util";

export default function WorklogDetailPage() {
  const { id } = useParams();
  const wid = Number(id);
  const [row, setRow] = useState<WorkLogDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchWorklog(wid);
        if (!cancelled) setRow(data);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : "Not found");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [wid]);

  async function toggleEntry(entryId: number, next: "approved" | "excluded") {
    setBusyId(entryId);
    setErr(null);
    try {
      await patchTimeEntry(entryId, next);
      const data = await fetchWorklog(wid);
      setRow(data);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusyId(null);
    }
  }

  if (err && !row) return <p className="error">{err}</p>;
  if (!row) return <p className="muted">Loading…</p>;

  return (
    <section className="panel">
      <div className="row-actions" style={{ marginBottom: "1rem" }}>
        <Link to="/">← Back to worklogs</Link>
      </div>
      <h2 style={{ marginTop: 0 }}>{row.task_title}</h2>
      <p className="muted">
        {row.freelancer_name} · <span className="mono">{row.freelancer_email}</span>
      </p>
      <div className="review-grid" style={{ marginTop: "1rem" }}>
        <div className="stat">
          <div className="label">Total hours (approved)</div>
          <div className="value">{Number(row.total_hours).toFixed(2)}</div>
        </div>
        <div className="stat">
          <div className="label">Billable total</div>
          <div className="value">{formatUsd(row.amount_cents)}</div>
        </div>
        <div className="stat">
          <div className="label">Remitted</div>
          <div className="value">{formatUsd(row.remitted_amount_cents)}</div>
        </div>
        <div className="stat">
          <div className="label">Unremitted</div>
          <div className="value">{formatUsd(row.unremitted_amount_cents)}</div>
        </div>
      </div>
      {err && <p className="error">{err}</p>}
      <h3 style={{ marginTop: "1.5rem" }}>Time entries</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Hours</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Settlement</th>
              <th>Memo</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {row.time_entries.map((te) => (
              <tr key={te.id}>
                <td className="mono">{te.occurred_on}</td>
                <td className="mono">{Number(te.hours).toFixed(2)}</td>
                <td className="mono">{formatUsd(te.amount_cents)}</td>
                <td>{te.status}</td>
                <td className="mono">
                  {te.settled_remittance_id != null
                    ? `#${te.settled_remittance_id}`
                    : "—"}
                </td>
                <td>{te.memo || "—"}</td>
                <td>
                  {te.status === "approved" ? (
                    <button
                      type="button"
                      className="btn btn-ghost"
                      style={{ padding: "0.35rem 0.6rem", fontSize: "0.8rem" }}
                      disabled={busyId === te.id || te.settled_remittance_id != null}
                      onClick={() => void toggleEntry(te.id, "excluded")}
                    >
                      Exclude
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-ghost"
                      style={{ padding: "0.35rem 0.6rem", fontSize: "0.8rem" }}
                      disabled={busyId === te.id}
                      onClick={() => void toggleEntry(te.id, "approved")}
                    >
                      Approve
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
