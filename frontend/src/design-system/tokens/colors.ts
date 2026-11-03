/** Tokens de cor — espelham `tailwind.config.js` (fonte de verdade no Tailwind). */

export const brand = {
  50: "#f0f7f4",
  100: "#dceee6",
  200: "#b8d9cb",
  300: "#8fc0a8",
  400: "#5a9a7a",
  500: "#1f6b4a",
  600: "#1a5a3e",
  700: "#154a34",
  800: "#103a28",
  900: "#0c2b1e",
  950: "#071a12",
} as const;

export const surface = {
  DEFAULT: "#ffffff",
  muted: "#f3f6f4",
  elevated: "#ffffff",
} as const;

export const text = {
  primary: "#14201a",
  secondary: "rgb(20 32 26 / 0.72)",
  muted: "rgb(20 32 26 / 0.55)",
} as const;

export const border = {
  DEFAULT: "#dceee6",
  strong: "#8fc0a8",
} as const;

export const semantic = {
  success: { fg: "#15803d", bg: "#f0fdf4", border: "#bbf7d0" },
  warning: { fg: "#b45309", bg: "#fffbeb", border: "#fde68a" },
  danger: { fg: "#b91c1c", bg: "#fef2f2", border: "#fecaca" },
  info: { fg: "#1d4ed8", bg: "#eff6ff", border: "#bfdbfe" },
} as const;

export const deviceStatus = {
  ONLINE: { label: "Online", fg: "text-status-online", bg: "bg-status-online-bg" },
  DEGRADED: { label: "Degradado", fg: "text-status-degraded", bg: "bg-status-degraded-bg" },
  OFFLINE: { label: "Offline", fg: "text-status-offline", bg: "bg-status-offline-bg" },
  DISABLED: { label: "Desabilitado", fg: "text-status-disabled", bg: "bg-status-disabled-bg" },
} as const;

export const queueStatus = {
  OPEN: { label: "Aberta", fg: "text-status-online", bg: "bg-status-online-bg" },
  PAUSED: { label: "Pausada", fg: "text-status-degraded", bg: "bg-status-degraded-bg" },
  CLOSED: { label: "Fechada", fg: "text-status-offline", bg: "bg-status-offline-bg" },
} as const;

export const ticketType = {
  NORMAL: { label: "Normal", className: "bg-brand-50 text-brand-800" },
  PRIORITY: { label: "Prioritária", className: "bg-semantic-warning-bg text-semantic-warning" },
  PRIORITY_PLUS: { label: "Prioridade+", className: "bg-semantic-danger-bg text-semantic-danger" },
} as const;

export const slaLevel = {
  OK: { label: "OK", fg: "text-sla-ok", bg: "bg-sla-ok-bg" },
  WARNING: { label: "Atenção", fg: "text-sla-warning", bg: "bg-sla-warning-bg" },
  CRITICAL: { label: "Crítico", fg: "text-sla-critical", bg: "bg-sla-critical-bg" },
} as const;
