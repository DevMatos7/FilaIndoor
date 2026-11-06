/** Shared duration helpers — aligned with player resolve_for_store. */

export function formatClockDuration(sec: number | null | undefined): string {
  const s = Math.max(0, Math.floor(Number(sec) || 0));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

/**
 * Effective seconds for a playlist item.
 * MEDIA: item.duration_seconds || asset.duration_seconds || 10
 * DYNAMIC SOURCE: effective_duration_seconds from content snapshot
 */
export function effectiveItemDuration(item: {
  item_type?: string | null;
  duration_seconds?: number | null;
  duration_source?: string | null;
  effective_duration_seconds?: number | null;
  asset?: { duration_seconds?: number | null } | null;
  dynamic_content?: { total_duration_seconds?: number | null } | null;
}): number {
  const itype = (item.item_type || "MEDIA").toUpperCase();
  if (itype === "DYNAMIC") {
    const source = (item.duration_source || "SOURCE").toUpperCase();
    if (source === "OVERRIDE") {
      return Math.max(1, Number(item.duration_seconds) || 10);
    }
    return Math.max(
      1,
      Number(item.effective_duration_seconds) ||
        Number(item.dynamic_content?.total_duration_seconds) ||
        Number(item.duration_seconds) ||
        10,
    );
  }
  return Math.max(1, Number(item.duration_seconds) || Number(item.asset?.duration_seconds) || 10);
}

export function hostOf(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}
