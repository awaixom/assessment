const base =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") ||
  (import.meta.env.DEV ? "" : "http://localhost:8000");

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type RemittanceFilter = "REMITTED" | "UNREMITTED";

export type WorkLogSummary = {
  id: number;
  external_id: string;
  task_id: number;
  task_title: string;
  user_id: number;
  freelancer_name: string;
  freelancer_email: string;
  total_hours: string;
  amount_cents: number;
  remitted_amount_cents: number;
  unremitted_amount_cents: number;
  remittance_status: RemittanceFilter;
};

export type TimeEntry = {
  id: number;
  occurred_on: string;
  hours: string;
  memo: string | null;
  status: string;
  amount_cents: number;
  settled_remittance_id: number | null;
};

export type WorkLogDetail = WorkLogSummary & { time_entries: TimeEntry[] };

export function fetchWorklogs(params: {
  remittance_status?: RemittanceFilter;
  user_id?: number;
  period_start?: string;
  period_end?: string;
}) {
  const q = new URLSearchParams();
  if (params.remittance_status) q.set("remittance_status", params.remittance_status);
  if (params.user_id != null) q.set("user_id", String(params.user_id));
  if (params.period_start && params.period_end) {
    q.set("period_start", params.period_start);
    q.set("period_end", params.period_end);
  }
  const qs = q.toString();
  return api<WorkLogSummary[]>(`/worklogs${qs ? `?${qs}` : ""}`);
}

export function fetchWorklog(id: number) {
  return api<WorkLogDetail>(`/worklogs/${id}`);
}

export function patchTimeEntry(id: number, status: "approved" | "excluded") {
  return api<{ ok: boolean }>(`/worklogs/time-entries/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export type GenerateRemittancesBody = {
  period_start: string;
  period_end: string;
  exclude_worklog_ids: number[];
  exclude_user_ids: number[];
};

export type GenerateRemittancesResponse = {
  period_start: string;
  period_end: string;
  remittances: {
    remittance_id: number;
    user_id: number;
    freelancer_name: string;
    total_cents: number;
    status: string;
    failure_reason: string | null;
    settled_entry_ids: number[];
    applied_adjustment_ids: number[];
  }[];
};

export function generateRemittances(body: GenerateRemittancesBody) {
  return api<GenerateRemittancesResponse>("/generate-remittances", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export type SettlementPreviewResponse = {
  period_start: string;
  period_end: string;
  batches: {
    user_id: number;
    freelancer_name: string;
    time_entry_ids: number[];
    adjustment_ids: number[];
    entry_total_cents: number;
    adjustment_total_cents: number;
    total_cents: number;
  }[];
  grand_total_cents: number;
};

export function previewSettlement(body: GenerateRemittancesBody) {
  return api<SettlementPreviewResponse>("/preview-settlement", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
