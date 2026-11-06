import { useEffect, useState } from "react";
import { pageIndexFromElapsed, usePlaybackClock } from "../display/PlaybackClock";
import { fetchPlayerDynamicContent } from "../../services/dynamicContentPlayer";
import { DynamicContentFallback } from "./DynamicContentFallback";
import { PriceTableRenderer } from "./PriceTableRenderer";
import { ProductGridRenderer } from "./ProductGridRenderer";
import { ProductHeroRenderer } from "./ProductHeroRenderer";
import { PromotionBoardRenderer } from "./PromotionBoardRenderer";
import {
  contentTypeOf,
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

function renderByType(snapshot: PriceTableSnapshot | null, pageIndex: number, fill: boolean) {
  const type = contentTypeOf(snapshot);
  switch (type) {
    case "PRODUCT_GRID":
      return <ProductGridRenderer snapshot={snapshot} pageIndex={pageIndex} fill={fill} />;
    case "PRODUCT_HERO":
      return <ProductHeroRenderer snapshot={snapshot} pageIndex={pageIndex} fill={fill} />;
    case "PROMOTION_BOARD":
      return <PromotionBoardRenderer snapshot={snapshot} pageIndex={pageIndex} fill={fill} />;
    case "PRICE_TABLE":
      return <PriceTableRenderer snapshot={snapshot} pageIndex={pageIndex} fill={fill} />;
    default:
      console.warn("[display] dynamic_content_skipped unknown type", type);
      return <DynamicContentFallback />;
  }
}

/**
 * Shared dynamic router — Admin Preview + Studio + TV.
 */
export function DynamicContentRenderer(props: Props) {
  if (props.mode === "preview") {
    return renderByType(props.snapshot, props.pageIndex ?? 0, true);
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
      const normalized = normalizePriceTableSnapshot(result.payload);
      if (!normalized || !normalized.pages?.length || (normalized.item_count ?? 0) === 0) {
        console.warn("[display] dynamic_content_skipped empty", contentId);
        setFailed(true);
        onFailed?.();
        return;
      }
      // Preload next page images lightly
      const pages = normalized.pages || [];
      const next = pages[1];
      next?.items?.forEach((it) => {
        const url = (it as { image?: { url?: string } }).image?.url;
        if (url) {
          const img = new Image();
          img.src = url;
        }
      });
      setSnapshot(normalized);
    })();
    return () => {
      alive = false;
    };
    // onFailed is intentionally omitted — parent often passes an inline callback
    // and including it re-triggers fetch forever (loading flash / black frame).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentId, token, itemKey]);

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

  return renderByType(data, pageIndex, true);
}
