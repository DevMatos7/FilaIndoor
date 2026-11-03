export type DisplayTicket = {
  id: string;
  number: string;
  type?: string;
  status?: string;
};

export type PlaylistItem = {
  id: string;
  name: string;
  type: string;
  url: string;
  mime_type?: string | null;
  duration_seconds: number;
};

export type PlayerConfig = {
  store_id: string;
  queue_id: string;
  department: string;
  ws_path: string;
  config_version?: number;
  device?: {
    id: string;
    device_uuid: string;
    status: string;
    config_version: number;
  };
  display: {
    id: string;
    name: string;
    audio_enabled: boolean;
    audio_template: string;
  };
  audio: { enabled: boolean; template: string; lang: string };
  playlist?: PlaylistItem[];
  queue: {
    name: string;
    current: DisplayTicket | null;
    last_called: DisplayTicket[];
    waiting_count: number;
  } | null;
};

export type WsEvent = {
  event: string;
  event_id: string;
  timestamp: string;
  data: {
    ticket?: string;
    ticket_id?: string;
    ticket_type?: string;
    department?: string;
    queue_id?: string;
    status?: string;
  };
};

/** Public player presentation states (overlay is orthogonal). */
export type PlayerUiState = "boot" | "ready" | "fallback" | "unavailable";

export type CallOverlay = {
  number: string;
  department: string;
  ticketType?: string;
};

export function isPriorityType(type?: string | null) {
  return type === "PRIORITY" || type === "PRIORITY_PLUS";
}
