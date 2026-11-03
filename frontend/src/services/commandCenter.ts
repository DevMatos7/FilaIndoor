import api from "./api";

export type LiveState = "live" | "updating" | "stale" | "partial" | "error";

export type AlertSeverity = "INFO" | "WARNING" | "CRITICAL";

export type CommandCenterAlert = {
  id: string;
  severity: AlertSeverity;
  title: string;
  description: string;
  href?: string;
};

export type QueueCard = {
  id: string;
  name: string;
  department_name?: string | null;
  status: string;
  waiting_count: number;
  priority_waiting: number;
  current_number?: string | null;
  current_status?: string | null;
  estimated_wait_seconds?: number | null;
  sla_level: "OK" | "WARNING" | "CRITICAL" | string;
};

export type DeviceCategory = {
  total: number;
  online: number;
  degraded: number;
  offline: number;
  disabled: number;
  level: string;
  items: Array<{ id: string; name: string; status: string; device_type: string }>;
};

export type ContentItem = {
  channel_id?: string | null;
  channel_name?: string | null;
  playlist_name?: string | null;
  schedule_name?: string | null;
  source?: string | null;
  screen_count: number;
  screens?: Array<{ id: string; name: string }>;
};

export type CommandCenterView = {
  storeId: string;
  storeName: string;
  generatedAt: string;
  fetchedAt: number;
  metrics: {
    waiting: number;
    serving: number;
    issued: number;
    completed: number;
    no_show: number;
    waitAvg: number | null;
    waitP90: number | null;
    activeTerminals: number;
    sla: {
      green: number;
      yellow: number;
      red: number;
      unknown: number;
      target_wait_seconds: number;
      warning_wait_seconds: number;
    };
  };
  queues: QueueCard[];
  devices: {
    categories: Record<string, DeviceCategory>;
    terminals: { total: number; active: number };
  };
  edge: { status: string; pending: number; failed: number };
  content: { available: boolean; message?: string | null; items: ContentItem[] };
  alerts: CommandCenterAlert[];
  hourly: Array<{ hour: number; issued: number; completed: number }>;
  sections: {
    metrics: "ok" | "error";
    queues: "ok" | "error";
    devices: "ok" | "error";
    content: "ok" | "error";
  };
};

type ApiOverview = {
  store_id: string;
  store_name: string;
  generated_at: string;
  metrics: {
    issued: number;
    completed: number;
    waiting: number;
    serving: number;
    no_show: number;
    active_terminals?: number;
    wait: { avg_seconds: number | null; p90_seconds: number | null };
    sla: CommandCenterView["metrics"]["sla"];
  };
  queues: QueueCard[];
  devices: CommandCenterView["devices"];
  edge: CommandCenterView["edge"];
  content: CommandCenterView["content"];
  alerts: CommandCenterAlert[];
  hourly: CommandCenterView["hourly"];
  sections?: CommandCenterView["sections"];
};

export function normalizeOverview(raw: ApiOverview, fetchedAt = Date.now()): CommandCenterView {
  const sections = raw.sections || {
    metrics: "ok" as const,
    queues: "ok" as const,
    devices: "ok" as const,
    content: "ok" as const,
  };
  return {
    storeId: raw.store_id,
    storeName: raw.store_name,
    generatedAt: raw.generated_at,
    fetchedAt,
    metrics: {
      waiting: raw.metrics?.waiting ?? 0,
      serving: raw.metrics?.serving ?? 0,
      issued: raw.metrics?.issued ?? 0,
      completed: raw.metrics?.completed ?? 0,
      no_show: raw.metrics?.no_show ?? 0,
      waitAvg: raw.metrics?.wait?.avg_seconds ?? null,
      waitP90: raw.metrics?.wait?.p90_seconds ?? null,
      activeTerminals: raw.metrics?.active_terminals ?? 0,
      sla: raw.metrics?.sla ?? {
        green: 0,
        yellow: 0,
        red: 0,
        unknown: 0,
        target_wait_seconds: 600,
        warning_wait_seconds: 900,
      },
    },
    queues: raw.queues || [],
    devices: raw.devices || {
      categories: {},
      terminals: { total: 0, active: 0 },
    },
    edge: raw.edge || { status: "ONLINE", pending: 0, failed: 0 },
    content: raw.content || { available: false, message: "Conteúdo atual indisponível", items: [] },
    alerts: raw.alerts || [],
    hourly: raw.hourly || [],
    sections,
  };
}

export function hasPartialFailure(view: CommandCenterView): boolean {
  return Object.values(view.sections).some((s) => s === "error");
}

export async function fetchCommandCenter(
  storeId: string,
  signal?: AbortSignal,
): Promise<CommandCenterView> {
  const { data } = await api.get<ApiOverview>("/operations/overview", {
    params: { store_id: storeId },
    signal,
  });
  return normalizeOverview(data);
}

export function fmtSec(v: number | null | undefined): string {
  if (v == null) return "—";
  const m = Math.floor(v / 60);
  const s = Math.round(v % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function relativeAge(fetchedAt: number, now = Date.now()): string {
  const sec = Math.max(0, Math.round((now - fetchedAt) / 1000));
  if (sec < 5) return "agora";
  if (sec < 60) return `há ${sec} s`;
  const m = Math.floor(sec / 60);
  return `há ${m} min`;
}

/** Intervalo considerado "ao vivo" (segundos). */
export const LIVE_TTL_MS = 45_000;
export const REFRESH_MS = 30_000;
