import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import { loadCache, saveCache } from "../services/edgeOffline";

type Ticket = { id: string; number: string; type?: string; status?: string };

type PlaylistItem = {
  id: string;
  name: string;
  type: string;
  url: string;
  mime_type?: string | null;
  duration_seconds: number;
};

type PlayerConfig = {
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
    current: Ticket | null;
    last_called: Ticket[];
    waiting_count: number;
  } | null;
};

type WsEvent = {
  event: string;
  event_id: string;
  timestamp: string;
  data: {
    ticket?: string;
    ticket_id?: string;
    department?: string;
    queue_id?: string;
    status?: string;
  };
};

const apiBase = import.meta.env.VITE_API_URL || "/api/v1";

function speak(template: string, number: string, department: string, lang: string) {
  if (!("speechSynthesis" in window)) return;
  const text = template
    .replace("{number}", number.split("").join(" "))
    .replace("{department}", department);
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = lang || "pt-BR";
  utter.rate = 0.95;
  window.speechSynthesis.speak(utter);
}

export default function Display() {
  const { queueId } = useParams();
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const forceAudio = params.get("audio");

  const [config, setConfig] = useState<PlayerConfig | null>(null);
  const [current, setCurrent] = useState<Ticket | null>(null);
  const [lastCalled, setLastCalled] = useState<Ticket[]>([]);
  const [overlay, setOverlay] = useState<{ number: string; department: string } | null>(null);
  const [wsState, setWsState] = useState<"connecting" | "online" | "offline">("connecting");
  const [error, setError] = useState<string | null>(null);
  const [slideIndex, setSlideIndex] = useState(0);

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

  const audioEnabled =
    forceAudio === "1" || forceAudio === "true" || !!config?.display.audio_enabled;

  useEffect(() => {
    aliveRef.current = true;
    intentionalCloseRef.current = false;

    function applyConfig(data: PlayerConfig) {
      configRef.current = data;
      setConfig(data);
      setCurrent(data.queue?.current || null);
      setLastCalled(data.queue?.last_called || []);
      setError(null);
    }

    async function fetchConfig(): Promise<PlayerConfig | null> {
      if (!token) {
        setError("Informe ?token= do display");
        return null;
      }
      const cacheId = `${queueId || "na"}:${token}`;
      try {
        const { data } = await axios.get<PlayerConfig>(`${apiBase}/player/config`, {
          headers: { "X-Display-Token": token },
          params: { token },
          timeout: 8000,
        });
        if (!aliveRef.current) return null;
        saveCache("player_config", cacheId, data);
        applyConfig(data);
        return data;
      } catch {
        const cached = loadCache<PlayerConfig>("player_config", cacheId, 60 * 60 * 1000);
        if (cached && aliveRef.current) {
          applyConfig(cached);
          setError("Modo cache local (edge offline)");
          return cached;
        }
        throw new Error("config unavailable");
      }
    }

    function showOverlay(number: string, department: string) {
      setOverlay({ number, department });
      if (overlayTimer.current) window.clearTimeout(overlayTimer.current);
      overlayTimer.current = window.setTimeout(() => setOverlay(null), 7000);

      const cfg = configRef.current;
      const force = forceAudioRef.current;
      const enabled = force === "1" || force === "true" || !!cfg?.display.audio_enabled;
      if (enabled && cfg) {
        speak(cfg.audio.template, number, department, cfg.audio.lang);
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

      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const url = `${proto}://${window.location.host}${cfg.ws_path}`;
      setWsState("connecting");
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (aliveRef.current) setWsState("online");
      };
      ws.onclose = () => {
        clearPing();
        if (!aliveRef.current || intentionalCloseRef.current) return;
        setWsState("offline");
        reconnectTimer.current = window.setTimeout(() => {
          const latest = configRef.current || cfg;
          connectWs(latest);
        }, 2500);
      };
      ws.onerror = () => {
        setWsState("offline");
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
            const department = evt.data.department || cfg.department || "Açougue";
            if (number) {
              const ticket: Ticket = {
                id: evt.data.ticket_id || number,
                number,
                status: evt.data.status,
              };
              setCurrent(ticket);
              setLastCalled((prev) => [ticket, ...prev.filter((t) => t.id !== ticket.id)].slice(0, 5));
              showOverlay(number, department);
            }
          }
          if (evt.event === "queue.updated") {
            void fetchConfig();
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

    async function sendHeartbeat(cfg: PlayerConfig) {
      if (!cfg.device?.id || !token) return;
      try {
        const estimate =
          typeof (navigator as Navigator & { storage?: { estimate?: () => Promise<{ quota?: number; usage?: number }> } })
            .storage?.estimate === "function"
            ? await (navigator as Navigator & { storage: { estimate: () => Promise<{ quota?: number; usage?: number }> } }).storage.estimate()
            : null;
        const freeMb =
          estimate?.quota != null && estimate?.usage != null
            ? Math.max(0, Math.round((estimate.quota - estimate.usage) / (1024 * 1024)))
            : undefined;
        await axios.post(
          `${apiBase}/devices/${cfg.device.id}/heartbeat`,
          {
            online: true,
            app_version: "1.0.0",
            free_storage_mb: freeMb,
            playlist_version: cfg.config_version ?? cfg.playlist?.length ?? 0,
          },
          { headers: { "X-Display-Token": token } },
        );
      } catch {
        // telemetria best-effort
      }
    }

    (async () => {
      try {
        const cfg = await fetchConfig();
        if (aliveRef.current && cfg) {
          connectWs(cfg);
          void sendHeartbeat(cfg);
          heartbeatTimer = window.setInterval(() => {
            const latest = configRef.current;
            if (latest) void sendHeartbeat(latest);
          }, 30000);
        }
      } catch {
        if (aliveRef.current) setError("Falha ao carregar config do player");
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

  const playlist = config?.playlist || [];
  const slide = playlist.length > 0 ? playlist[slideIndex % playlist.length] : null;

  useEffect(() => {
    if (playlist.length === 0) return;
    setSlideIndex(0);
  }, [playlist.length, config?.store_id]);

  useEffect(() => {
    if (!slide || playlist.length === 0) return;
    const ms = Math.max(3, slide.duration_seconds || 10) * 1000;
    const id = window.setTimeout(() => {
      setSlideIndex((i) => (i + 1) % playlist.length);
    }, ms);
    return () => window.clearTimeout(id);
  }, [slide, playlist.length]);

  const lastLine = lastCalled
    .filter((t) => t.id !== current?.id)
    .slice(0, 3)
    .map((t) => t.number)
    .join(" • ");

  return (
    <div className="relative flex min-h-screen flex-col bg-brand-900 text-white">
      <div className="absolute right-4 top-4 z-20 rounded-full bg-black/40 px-3 py-1 text-xs uppercase tracking-wide">
        {wsState === "online" ? "Ao vivo" : wsState === "connecting" ? "Conectando…" : "Reconectando…"}
        {audioEnabled ? " · Áudio" : " · Sem áudio"}
      </div>

      <section className="relative flex flex-[1.35] items-center justify-center overflow-hidden bg-gradient-to-br from-brand-700 via-brand-900 to-ink">
        {!slide && (
          <>
            <div
              className="pointer-events-none absolute inset-0 opacity-30"
              style={{
                backgroundImage:
                  "radial-gradient(circle at 20% 20%, #fff3 0, transparent 40%), radial-gradient(circle at 80% 60%, #1f6b4a55 0, transparent 45%)",
              }}
            />
            <div className="relative z-10 px-6 text-center">
              <p className="font-display text-4xl font-semibold tracking-tight sm:text-5xl">REAL</p>
              <p className="mt-3 text-lg text-brand-100 sm:text-xl">Ofertas e comunicação indoor</p>
              <p className="mt-2 text-sm text-white/60">Sem mídia na loja — cadastre em /media</p>
            </div>
          </>
        )}

        {slide?.type === "IMAGE" && (
          <img src={slide.url} alt={slide.name} className="absolute inset-0 h-full w-full object-cover" />
        )}
        {slide?.type === "VIDEO" && (
          <video
            key={slide.id}
            src={slide.url}
            className="absolute inset-0 h-full w-full object-cover"
            autoPlay
            muted
            playsInline
          />
        )}
        {slide?.type === "WEB" && (
          <iframe title={slide.name} src={slide.url} className="absolute inset-0 h-full w-full border-0 bg-white" />
        )}

        {overlay && (
          <div className="absolute inset-0 z-30 flex items-center justify-center bg-brand-900/92 p-6 backdrop-blur-sm">
            <div className="text-center">
              <p className="font-display text-8xl font-bold tracking-tight sm:text-9xl">{overlay.number}</p>
              <p className="mt-4 text-3xl uppercase tracking-[0.2em] text-brand-100">{overlay.department}</p>
              <p className="mt-6 text-2xl text-white/90">Dirija-se ao balcão</p>
            </div>
          </div>
        )}
      </section>

      <section className="flex flex-col justify-center border-t border-white/10 bg-ink px-6 py-8 sm:py-10">
        <p className="text-sm uppercase tracking-[0.25em] text-brand-100">
          {config?.department || config?.queue?.name || "Açougue"} · Senha atual
        </p>
        <p className="mt-2 font-display text-7xl font-bold tracking-tight sm:text-8xl">{current?.number || "—"}</p>
        <p className="mt-4 text-lg text-white/70">Últimas {lastLine || "—"}</p>
        {error && <p className="mt-3 text-sm text-amber-200">{error}</p>}
      </section>
    </div>
  );
}
