import type { Ticket } from "../../services/api";

export type Terminal = {
  id: string;
  name: string;
  code: string;
  department_id: string;
  active?: boolean;
};

export type OperatorPanel = {
  name: string;
  status?: string;
  department_id?: string;
  department_display_name?: string;
  waiting_count: number;
  priority_waiting: number;
  serving: Ticket | null;
  elapsed_seconds: number | null;
  terminal_id?: string | null;
};

export type OperatorPhase = "login" | "select-terminal" | "operating";

export type ActionKind = "next" | "recall" | "no_show" | "complete" | null;

export function formatElapsed(total: number | null | undefined) {
  const s = Math.max(0, Math.floor(total || 0));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

export function isPriority(type?: string | null) {
  return type === "PRIORITY" || type === "PRIORITY_PLUS";
}

export function terminalLabel(t: Terminal) {
  return t.name?.trim() || t.code;
}

export const TERMINAL_STORAGE_KEY = "operator_terminal";
