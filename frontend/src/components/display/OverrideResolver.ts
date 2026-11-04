import {
  isOverrideActive,
  parseOverrideTime,
  type ScreenOverride,
} from "./overrideTypes";

/**
 * Pure selection — independent from LayoutResolver.
 * Rule: priority DESC, starts_at DESC, created_at DESC.
 */
export function resolveCurrentOverride(
  candidates: ScreenOverride[],
  now = Date.now(),
): ScreenOverride | null {
  const active = candidates.filter((o) => isOverrideActive(o, now));
  if (active.length === 0) return null;
  active.sort((a, b) => {
    if (b.priority !== a.priority) return b.priority - a.priority;
    const sb = parseOverrideTime(b.starts_at) - parseOverrideTime(a.starts_at);
    if (sb !== 0) return sb;
    return parseOverrideTime(b.created_at) - parseOverrideTime(a.created_at);
  });
  return active[0];
}

export function nextExpiryMs(candidates: ScreenOverride[], now = Date.now()): number | null {
  const ends = candidates
    .filter((o) => isOverrideActive(o, now))
    .map((o) => parseOverrideTime(o.expires_at) - now)
    .filter((ms) => ms > 0);
  if (ends.length === 0) return null;
  return Math.min(...ends);
}
