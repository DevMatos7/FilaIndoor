export type TotemUiState =
  | "boot"
  | "idle"
  | "processing"
  | "success"
  | "printer_error"
  | "server_error"
  | "offline"
  | "closed"
  | "unavailable";

export type QueueStatus = {
  name: string;
  department_name?: string;
  store_id?: string | null;
  waiting_count: number;
  estimated_wait_seconds: number;
  status: string;
};

export type IssueResponse = {
  ticket: {
    id: string;
    number: string;
    type: string;
    people_ahead?: number;
    estimated_wait_seconds?: number;
  };
  print: {
    ok: boolean;
    message?: string;
    provider?: string;
  };
  department_name?: string;
};

/** Brand hooks for future logo/color/message without new config store. */
export type TotemBrand = {
  wordmark: string;
  primary: string;
  surface: string;
  message?: string;
};

export const DEFAULT_TOTEM_BRAND: TotemBrand = {
  wordmark: "REAL",
  primary: "#154a34",
  surface: "#f3f6f4",
};

export function formatWaitMinutes(seconds: number | null | undefined): string | null {
  if (seconds == null || seconds <= 0) return null;
  const mins = Math.round(seconds / 60);
  if (mins < 1) return "menos de 1 minuto";
  if (mins === 1) return "1 minuto";
  return `${mins} minutos`;
}
