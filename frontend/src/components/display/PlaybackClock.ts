import { useCallback, useEffect, useRef, useState } from "react";

export type PlaybackClockState = "RUNNING" | "PAUSED";

/**
 * Logical playback clock — advances only while RUNNING.
 * Override layers pause this clock so page/item timers resume correctly.
 */
export function usePlaybackClock(opts: {
  /** Reset key — change when playlist item changes. */
  resetKey: string | number | null | undefined;
  paused: boolean;
  enabled?: boolean;
}) {
  const { resetKey, paused, enabled = true } = opts;
  const [elapsedMs, setElapsedMs] = useState(0);
  const accumRef = useRef(0);
  const segmentStartRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);

  const tick = useCallback(() => {
    const extra =
      segmentStartRef.current != null ? performance.now() - segmentStartRef.current : 0;
    setElapsedMs(accumRef.current + extra);
    rafRef.current = window.requestAnimationFrame(tick);
  }, []);

  useEffect(() => {
    accumRef.current = 0;
    segmentStartRef.current = null;
    setElapsedMs(0);
  }, [resetKey]);

  useEffect(() => {
    if (rafRef.current != null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (!enabled) return;

    if (paused) {
      if (segmentStartRef.current != null) {
        accumRef.current += performance.now() - segmentStartRef.current;
        segmentStartRef.current = null;
        setElapsedMs(accumRef.current);
      }
      return;
    }

    segmentStartRef.current = performance.now();
    rafRef.current = window.requestAnimationFrame(tick);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    };
  }, [paused, enabled, resetKey, tick]);

  const state: PlaybackClockState = !enabled ? "PAUSED" : paused ? "PAUSED" : "RUNNING";

  return {
    elapsedMs,
    activeElapsedMs: elapsedMs,
    state,
  };
}

/** Page index for PRICE_TABLE given active elapsed. */
export function pageIndexFromElapsed(
  activeElapsedMs: number,
  pageDurationSeconds: number,
  pageCount: number,
  durationMode: string,
): number {
  const pageDur = Math.max(1, pageDurationSeconds) * 1000;
  const count = Math.max(1, pageCount);
  if ((durationMode || "FULL_CYCLE").toUpperCase() === "FIXED") {
    return Math.floor(activeElapsedMs / pageDur) % count;
  }
  // FULL_CYCLE — clamp to last page until item advances
  return Math.min(count - 1, Math.floor(activeElapsedMs / pageDur));
}
