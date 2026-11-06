import type { PriceTableSnapshot } from "../components/dynamic-content/dynamicContentTypes";
import { cacheKey } from "./edgeOffline";

const apiBase = () => import.meta.env.VITE_API_URL || "/api/v1";

type CachedDynamic = {
  payload: PriceTableSnapshot;
  etag: string;
  generated_at?: string;
  valid_until?: string;
  saved_at: number;
};

function readDynamicCache(id: string): CachedDynamic | null {
  try {
    const raw = localStorage.getItem(cacheKey("dynamic_content", id));
    if (!raw) return null;
    return JSON.parse(raw) as CachedDynamic;
  } catch {
    return null;
  }
}

function writeDynamicCache(id: string, entry: CachedDynamic) {
  try {
    localStorage.setItem(cacheKey("dynamic_content", id), JSON.stringify(entry));
  } catch {
    /* quota */
  }
}

function isCacheValid(entry: CachedDynamic | null): entry is CachedDynamic {
  if (!entry?.payload || !entry.valid_until) return false;
  const until = Date.parse(entry.valid_until);
  if (Number.isNaN(until)) return false;
  return Date.now() <= until;
}

export type DynamicFetchResult =
  | { ok: true; payload: PriceTableSnapshot; etag: string; fromCache: boolean }
  | { ok: false; reason: "stale" | "network" | "forbidden" | "not_modified_empty" };

/**
 * Player dynamic fetch — ETag / 304 / valid_until cache.
 * Never returns expired cache as OK.
 */
export async function fetchPlayerDynamicContent(
  contentId: string,
  token: string,
): Promise<DynamicFetchResult> {
  const cached = readDynamicCache(contentId);
  const headers: Record<string, string> = {
    "X-Display-Token": token,
  };
  if (cached?.etag) {
    headers["If-None-Match"] = cached.etag;
  }

  try {
    console.info("[display] dynamic_content_fetch", contentId);
    const res = await fetch(`${apiBase()}/player/dynamic-content/${contentId}?token=${encodeURIComponent(token)}`, {
      headers,
      cache: "no-store",
    });

    if (res.status === 304) {
      if (isCacheValid(cached)) {
        console.info("[display] dynamic_content_cache_hit", contentId);
        return { ok: true, payload: cached.payload, etag: cached.etag, fromCache: true };
      }
      console.warn("[display] dynamic_content_stale", contentId);
      return { ok: false, reason: "stale" };
    }

    if (res.status === 403 || res.status === 404 || res.status === 422) {
      console.warn("[display] dynamic_content_skipped", contentId, res.status);
      return { ok: false, reason: "forbidden" };
    }

    if (!res.ok) {
      if (isCacheValid(cached)) {
        console.info("[display] dynamic_content_cache_hit", contentId);
        return { ok: true, payload: cached.payload, etag: cached.etag, fromCache: true };
      }
      console.warn("[display] dynamic_content_skipped", contentId, "network", res.status);
      return { ok: false, reason: "network" };
    }

    const payload = (await res.json()) as PriceTableSnapshot;
    const etag = (res.headers.get("ETag") || `"${payload.content_hash || payload.version || ""}"`).trim();
    const freshness = payload.freshness || payload.source?.freshness;
    if (freshness === "STALE" || freshness === "FAILED") {
      console.warn("[display] dynamic_content_stale", contentId);
      return { ok: false, reason: "stale" };
    }

    writeDynamicCache(contentId, {
      payload,
      etag,
      generated_at: payload.generated_at || payload.source?.generated_at,
      valid_until: payload.valid_until,
      saved_at: Date.now(),
    });
    console.info("[display] dynamic_content_cache_miss", contentId);
    return { ok: true, payload, etag, fromCache: false };
  } catch {
    if (isCacheValid(cached)) {
      console.info("[display] dynamic_content_cache_hit", contentId);
      return { ok: true, payload: cached.payload, etag: cached.etag, fromCache: true };
    }
    console.warn("[display] dynamic_content_skipped", contentId, "network");
    return { ok: false, reason: "network" };
  }
}
