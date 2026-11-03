import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { DisplayShell } from "../components/display/DisplayShell";
import { DisplayBoot } from "../components/display/DisplayBoot";
import { DisplayUnavailable } from "../components/display/DisplayUnavailable";
import { LayoutResolver } from "../components/display/LayoutResolver";
import { QueueCallOverlay } from "../components/display/QueueCallOverlay";
import type {
  CallOverlay,
  DisplayTicket,
  PlayerConfig,
  PlayerUiState,
  PlaylistItem,
  WsEvent,
} from "../components/display/types";
import {
  buildWsUrl,
  fetchPlayerConfig,
  sendDisplayHeartbeat,
  speakTicket,
} from "../services/displayPlayer";

/**
 * UX-6B — Display + Layout Engine
 *
 * DisplayShell
 *   ├── LayoutResolver → zones (MEDIA / QUEUE / TEXT / CLOCK / TICKER)
 *   └── QueueCallOverlay (global, acima das zones — UX-6C migrará para OverrideRenderer)
 *
 * Cache antigo sem `layout` → emergency media_queue_footer (UX-6A equivalente).
 */
export default function Display() {
  const { queueId } = useParams();
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const forceAudio = params.get("audio");

  const [uiState, setUiState] = useState<PlayerUiState>("boot");
  const [config, setConfig] = useState<PlayerConfig | null>(null);
  const [current, setCurrent] = useState<DisplayTicket | null>(null);
  const [lastCalled, setLastCalled] = useState<DisplayTicket[]>([]);
  const [overlay, setOverlay] = useState<CallOverlay | null>(null);
  const [slideIndex, setSlideIndex] = useState(0);
  const [skipIds, setSkipIds] = useState<Set<string>>(() => new Set());

  const seenEvents = useRef<Set<string>>(new Set());
  const overlayTimer = useRef<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number | null>(null);
  const pingTimer = useRef<number | null>(null);
  const aliveRef = useRef(true);
  const intentionalCloseRef = useRef(false);
  const configRef = useRef<PlayerConfig | null>(null);
  const forceAudioRef = useRef(forceAudio);
  forceAudioRef.current = forceAudio;

  useEffect(() => {
    aliveRef.current = true;
    intentionalCloseRef.current = false;

    function applyConfig(data: PlayerConfig) {
      configRef.current = data;
      setConfig(data);
      setCurrent(data.queue?.current || null);
      setLastCalled(data.queue?.last_called || []);
      const hasMedia = (data.playlist?.length || 0) > 0;
      setUiState(hasMedia ? "ready" : "fallback");
    }

    async function loadConfig(): Promise<PlayerConfig | null> {
      if (!token) {
        setUiState("unavailable");
        return null;
      }
      try {
        const { config: data, fromCache } = await fetchPlayerConfig(queueId, token);
        if (!aliveRef.current) return null;
        applyConfig(data);
        if (fromCache) {
          console.info("[display] using cached player config (edge/offline)");
        }
        return data;
      } catch {
        if (aliveRef.current) setUiState("unavailable");
        return null;
      }
    }

    function showOverlay(number: string, department: string, ticketType?: string) {
      setOverlay({ number, department, ticketType });
      if (overlayTimer.current) window.clearTimeout(overlayTimer.current);
      overlayTimer.current = window.setTimeout(() => setOverlay(null), 7000);

      const cfg = configRef.current;
      const force = forceAudioRef.current;
      const enabled = force === "1" || force === "true" || !!cfg?.display.audio_enabled;
      if (enabled && cfg) {
        speakTicket(cfg.audio.template, number, department, cfg.audio.lang);
      }
    }

    function clearPing() {
      if (pingTimer.current) {
        window.clearInterval(pingTimer.current);
        pingTimer.current = null;
      }
    }

    function connectWs(cfg: PlayerConfig) {
      if (!aliveRef.current) return;
      if (reconnectTimer.current) {
        window.clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      clearPing();
      if (wsRef.current) {
        intentionalCloseRef.current = true;
        wsRef.current.close();
        wsRef.current = null;
        intentionalCloseRef.current = false;
      }

      const ws = new WebSocket(buildWsUrl(cfg.ws_path));
      wsRef.current = ws;

      ws.onopen = () => {
        console.debug("[display] ws online");
      };
      ws.onclose = () => {
        clearPing();
        if (!aliveRef.current || intentionalCloseRef.current) return;
        console.debug("[display] ws offline — reconnecting");
        reconnectTimer.current = window.setTimeout(() => {
          const latest = configRef.current || cfg;
          connectWs(latest);
        }, 2500);
      };
      ws.onerror = () => {
        ws.close();
      };
      ws.onmessage = (msg) => {
        try {
          const evt = JSON.parse(msg.data) as WsEvent;
          if (seenEvents.current.has(evt.event_id)) return;
          seenEvents.current.add(evt.event_id);
          if (seenEvents.current.size > 500) {
            const first = seenEvents.current.values().next().value;
            if (first) seenEvents.current.delete(first);
          }

          if (evt.data.queue_id && queueId && evt.data.queue_id !== queueId) return;

          if (evt.event === "ticket.called" || evt.event === "ticket.recalled") {
            const number = evt.data.ticket || "";
            const department = evt.data.department || cfg.department || "Atendimento";
            if (number) {
              const ticket: DisplayTicket = {
                id: evt.data.ticket_id || number,
                number,
                type: evt.data.ticket_type,
                status: evt.data.status,
              };
              setCurrent(ticket);
              setLastCalled((prev) => [ticket, ...prev.filter((t) => t.id !== ticket.id)].slice(0, 5));
              showOverlay(number, department, evt.data.ticket_type);
            }
          }
          if (evt.event === "queue.updated") {
            void loadConfig();
          }
        } catch {
          // ignore malformed
        }
      };

      pingTimer.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, 20000);
    }

    let heartbeatTimer: number | null = null;

    (async () => {
      const cfg = await loadConfig();
      if (aliveRef.current && cfg) {
        connectWs(cfg);
        void sendDisplayHeartbeat(cfg, token);
        heartbeatTimer = window.setInterval(() => {
          const latest = configRef.current;
          if (latest) void sendDisplayHeartbeat(latest, token);
        }, 30000);
      }
    })();

    return () => {
      aliveRef.current = false;
      intentionalCloseRef.current = true;
      if (reconnectTimer.current) window.clearTimeout(reconnectTimer.current);
      if (heartbeatTimer) window.clearInterval(heartbeatTimer);
      clearPing();
      if (overlayTimer.current) window.clearTimeout(overlayTimer.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [token, queueId]);

  const playlist = useMemo(() => {
    const raw = config?.playlist || [];
    return raw.filter((p) => !skipIds.has(p.id));
  }, [config?.playlist, skipIds]);

  const slide = playlist.length > 0 ? playlist[slideIndex % playlist.length] : null;

  useEffect(() => {
    setSlideIndex(0);
    setSkipIds(new Set());
  }, [config?.store_id, config?.config_version, config?.playlist?.length]);

  useEffect(() => {
    if (!slide || playlist.length === 0) return;
    const ms = Math.max(3, slide.duration_seconds || 10) * 1000;
    const id = window.setTimeout(() => {
      setSlideIndex((i) => (i + 1) % playlist.length);
    }, ms);
    return () => window.clearTimeout(id);
  }, [slide, playlist.length]);

  function handleMediaFailed(item: PlaylistItem) {
    setSkipIds((prev) => {
      const next = new Set(prev);
      next.add(item.id);
      return next;
    });
    setSlideIndex((i) => i + 1);
  }

  const department = config?.department || config?.queue?.name || "Atendimento";

  // All-media failed → branded fallback, still show footer if we have config
  const effectiveState: PlayerUiState =
    uiState === "ready" && playlist.length === 0 ? "fallback" : uiState;

  if (effectiveState === "boot") {
    return (
      <DisplayShell>
        <DisplayBoot />
      </DisplayShell>
    );
  }

  if (effectiveState === "unavailable") {
    return (
      <DisplayShell>
        <DisplayUnavailable />
      </DisplayShell>
    );
  }

  return (
    <DisplayShell>
      <div className="relative h-full w-full overflow-hidden">
        <LayoutResolver
          layout={config?.layout}
          mediaItem={slide}
          onMediaFailed={handleMediaFailed}
          department={department}
          current={current}
          lastCalled={lastCalled}
        />
        {/* Overlay global — acima de todas as zones (não acoplado ao LayoutResolver) */}
        <QueueCallOverlay call={overlay} />
      </div>
    </DisplayShell>
  );
}
