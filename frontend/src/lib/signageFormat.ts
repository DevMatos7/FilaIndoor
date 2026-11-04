/** Shared duration helpers — aligned with player resolve_for_store. */

export function formatClockDuration(sec: number | null | undefined): string {
  const s = Math.max(0, Math.floor(Number(sec) || 0));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

/**
 * Effective seconds for a playlist item.
 * Player: item.duration_seconds || asset.duration_seconds || 10
 */
export function effectiveItemDuration(item: {
  duration_seconds?: number | null;
  asset?: { duration_seconds?: number | null } | null;
}): number {
  return Math.max(1, Number(item.duration_seconds) || Number(item.asset?.duration_seconds) || 10);
}

export function hostOf(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}
