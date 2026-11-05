import api from "./api";

export type PeriodPreset = "today" | "yesterday" | "7d" | "30d" | "custom";

export type AnalyticsOverview = {
  period: {
    from: string;
    to: string;
    days: number;
    granularity: "hour" | "day";
    timezone_note: string;
    previous: { from: string; to: string };
  };
  filters: { store_id: string; queue_id: string | null; ticket_type: string | null };
  cohorts: Record<string, string>;
  metrics: {
    issued: number;
    completed: number;
    no_show: number;
    cancelled: number;
    completion_rate: number | null;
    completion_rate_note?: string;
    throughput_per_hour: number;
    wait: MetricStats;
    service: MetricStats;
    sla: {
      green: number;
      yellow: number;
      red: number;
      unknown: number;
      evaluable: number;
      within_target: number;
      within_target_rate: number | null;
      target_wait_seconds: number;
      warning_wait_seconds: number;
      definition: string;
    };
  };
  comparison: {
    previous: Record<string, number | null>;
    issued: Delta | null;
    completed: Delta | null;
    wait_avg: Delta | null;
    wait_p90: Delta | null;
    sla_rate: Delta | null;
    no_show: Delta | null;
    note: string;
  };
  series: {
    granularity: string;
    volume: Array<{ bucket: string; issued: number; completed: number }>;
    wait: Array<{
      bucket: string;
      avg_seconds: number | null;
      p90_seconds: number | null;
      sample_count: number;
    }>;
  };
  demand_hourly: Array<{ hour: number; issued: number }>;
  available_queues?: Array<{ id: string; name: string }>;
  queues: QueueRow[];
  by_type: Record<string, number>;
  terminals: {
    available: boolean;
    reason?: string;
    note?: string;
    items: Array<{
      terminal_id: string;
      completed: number;
      service_avg_seconds: number | null;
      service_sample_count: number;
    }>;
  };
  operators: {
    available: boolean;
    reason?: string;
    note?: string;
    items: Array<{ operator_id: string; completed: number }>;
  };
  devices_current: {
    available: boolean;
    label: string;
    note?: string;
    error?: boolean;
    total?: number;
    online?: number;
    degraded?: number;
    offline?: number;
    disabled?: number;
  };
  empty: boolean;
};

export type MetricStats = {
  avg_seconds: number | null;
  median_seconds: number | null;
  p90_seconds: number | null;
  max_seconds: number | null;
  sample_count: number;
};

export type Delta = { absolute: number; pct: number | null };

export type QueueRow = {
  queue_id: string;
  name: string;
  issued: number;
  completed: number;
  no_show: number;
  wait_avg_seconds: number | null;
  wait_p90_seconds: number | null;
  wait_sample_count: number;
  sla_within_rate: number | null;
  sla_evaluable: number;
  sla_green: number;
  sla_yellow: number;
  sla_red: number;
  sla_unknown: number;
};

export type QueueOption = { id: string; name: string; department_id?: string };

function toIsoDate(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function resolvePeriod(
  preset: PeriodPreset,
  customFrom?: string,
  customTo?: string,
): { from: string; to: string } {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (preset === "today") {
    const s = toIsoDate(today);
    return { from: s, to: s };
  }
  if (preset === "yesterday") {
    const y = new Date(today);
    y.setDate(y.getDate() - 1);
    const s = toIsoDate(y);
    return { from: s, to: s };
  }
  if (preset === "7d") {
    const from = new Date(today);
    from.setDate(from.getDate() - 6);
    return { from: toIsoDate(from), to: toIsoDate(today) };
  }
  if (preset === "30d") {
    const from = new Date(today);
    from.setDate(from.getDate() - 29);
    return { from: toIsoDate(from), to: toIsoDate(today) };
  }
  const from = customFrom || toIsoDate(today);
  const to = customTo || from;
  return { from, to: to < from ? from : to };
}

export async function fetchAnalyticsOverview(
  params: {
    store_id: string;
    from: string;
    to: string;
    queue_id?: string;
    ticket_type?: string;
  },
  signal?: AbortSignal,
): Promise<AnalyticsOverview> {
  const { data } = await api.get<AnalyticsOverview>("/analytics/overview", {
    params: {
      store_id: params.store_id,
      from: params.from,
      to: params.to,
      queue_id: params.queue_id || undefined,
      ticket_type: params.ticket_type || undefined,
    },
    signal,
  });
  return data;
}

export async function fetchQueuesForStore(
  storeId: string,
  signal?: AbortSignal,
): Promise<QueueOption[]> {
  const { data } = await api.get<Array<QueueOption & { department?: { store_id?: string }; store_id?: string }>>(
    "/queues",
    { signal },
  );
  // filtrar por loja quando o payload expuser store
  return (data || []).filter((q) => {
    const sid = (q as { store_id?: string }).store_id;
    if (sid) return sid === storeId;
    return true;
  });
}

export function formatSeconds(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  const s = Math.round(v);
  const m = Math.floor(s / 60);
  const r = s % 60;
  if (m <= 0) return `${r}s`;
  return `${m}:${String(r).padStart(2, "0")}`;
}

export function formatPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

export function formatDeltaPct(d: Delta | null | undefined, invertGood = false): string | null {
  if (!d || d.pct == null) return null;
  const pct = Math.round(d.pct * 1000) / 10;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct}%`;
}

export function deltaTone(d: Delta | null | undefined, invertGood = false): "up" | "down" | "flat" {
  if (!d || d.pct == null) return "flat";
  if (Math.abs(d.pct) < 0.005) return "flat";
  const up = d.pct > 0;
  if (invertGood) return up ? "down" : "up"; // wait up = bad
  return up ? "up" : "down";
}
