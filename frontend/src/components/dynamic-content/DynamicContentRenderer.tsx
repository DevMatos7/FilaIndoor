import { useEffect, useState } from "react";
import { pageIndexFromElapsed, usePlaybackClock } from "../display/PlaybackClock";
import { fetchPlayerDynamicContent } from "../../services/dynamicContentPlayer";
import { DynamicContentFallback } from "./DynamicContentFallback";
import { PriceTableRenderer } from "./PriceTableRenderer";
import {
  normalizePriceTableSnapshot,
  type PriceTableSnapshot,
} from "./dynamicContentTypes";

type PlayerProps = {
  mode: "player";
  contentId: string;
  token: string;
  itemKey: string;
  paused: boolean;
  onFailed?: () => void;
  /** Optional preloaded snapshot (studio). */
  snapshot?: never;
  pageIndex?: never;
};

type PreviewProps = {
  mode: "preview";
  snapshot: PriceTableSnapshot | null;
  pageIndex?: number;
  paused?: boolean;
  contentId?: never;
  token?: never;
  itemKey?: never;
  onFailed?: never;
};

type Props = PlayerProps | PreviewProps;

/**
 * Routes DYNAMIC content to the shared PriceTableRenderer.
 * Player mode: fetch + ETag cache + page timer via PlaybackClock.
 * Preview mode: controlled snapshot/page (admin / studio).
 */
export function DynamicContentRenderer(props: Props) {
  if (props.mode === "preview") {
    return (
      <PriceTableRenderer
        snapshot={props.snapshot}
        pageIndex={props.pageIndex ?? 0}
        fill
      />
    );
  }

  return <PlayerDynamicContent {...props} />;
}

function PlayerDynamicContent({
  contentId,
  token,
  itemKey,
  paused,
  onFailed,
}: PlayerProps) {
  const [snapshot, setSnapshot] = useState<PriceTableSnapshot | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    setFailed(false);
    setSnapshot(null);
    (async () => {
      const result = await fetchPlayerDynamicContent(contentId, token);
      if (!alive) return;
      if (!result.ok) {
        setFailed(true);
        onFailed?.();
        return;
      }
      setSnapshot(normalizePriceTableSnapshot(result.payload));
    })();
    return () => {
      alive = false;
    };
  }, [contentId, token, itemKey, onFailed]);

  const data = normalizePriceTableSnapshot(snapshot);
  const pageDur = data?.page_duration_seconds ?? 8;
  const pageCount = Math.max(1, data?.page_count ?? data?.pages?.length ?? 1);
  const mode = data?.duration_mode || "FULL_CYCLE";

  const clock = usePlaybackClock({
    resetKey: itemKey,
    paused: paused || !data,
    enabled: !!data && !failed,
  });

  const pageIndex = data
    ? pageIndexFromElapsed(clock.activeElapsedMs, pageDur, pageCount, mode)
    : 0;

  if (failed) return <DynamicContentFallback />;
  if (!data) {
    return <div className="absolute inset-0 bg-brand-950" data-testid="dynamic-loading" />;
  }

  return (
    <PriceTableRenderer snapshot={data} pageIndex={pageIndex} fill />
  );
}
