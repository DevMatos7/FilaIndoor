import axios from "axios";
import { loadCache, saveCache } from "./edgeOffline";
import type { PlayerConfig } from "../components/display/types";

const apiBase = import.meta.env.VITE_API_URL || "/api/v1";

export function speakTicket(
  template: string,
  number: string,
  department: string,
  lang: string,
) {
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

export function cacheIdFor(queueId: string | undefined, token: string) {
  return `${queueId || "na"}:${token}`;
}

export async function fetchPlayerConfig(
  queueId: string | undefined,
  token: string,
): Promise<{ config: PlayerConfig; fromCache: boolean }> {
  const cacheId = cacheIdFor(queueId, token);
  try {
    const { data } = await axios.get<PlayerConfig>(`${apiBase}/player/config`, {
      headers: { "X-Display-Token": token },
      params: { token },
      timeout: 8000,
    });
    saveCache("player_config", cacheId, data);
    return { config: data, fromCache: false };
  } catch {
    const cached = loadCache<PlayerConfig>("player_config", cacheId, 60 * 60 * 1000);
    if (cached) return { config: cached, fromCache: true };
    throw new Error("config unavailable");
  }
}

export async function sendDisplayHeartbeat(cfg: PlayerConfig, token: string) {
  if (!cfg.device?.id || !token) return;
  try {
    const estimate =
      typeof (
        navigator as Navigator & {
          storage?: { estimate?: () => Promise<{ quota?: number; usage?: number }> };
        }
      ).storage?.estimate === "function"
        ? await (
            navigator as Navigator & {
              storage: { estimate: () => Promise<{ quota?: number; usage?: number }> };
            }
          ).storage.estimate()
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
    // telemetria best-effort — invisível ao público
  }
}

export function buildWsUrl(wsPath: string) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}${wsPath}`;
}
