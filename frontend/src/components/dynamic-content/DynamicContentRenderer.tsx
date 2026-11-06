import { useEffect, useRef, useState } from "react";
import { pageIndexFromElapsed, usePlaybackClock } from "../display/PlaybackClock";
import {
  clearDynamicContentCache,
  fetchPlayerDynamicContent,
} from "../../services/dynamicContentPlayer";
import { subscribeDynamicInvalidation } from "../../services/dynamicInvalidationBus";
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
  const safePages = Math.max(1, snapshot?.page_count ?? snapshot?.pages?.length ?? 1);
  const safeIndex = ((pageIndex % safePages) + safePages) % safePages;
  switch (type) {
    case "PRODUCT_GRID":
      return <ProductGridRenderer snapshot={snapshot} pageIndex={safeIndex} fill={fill} />;
    case "PRODUCT_HERO":
      return <ProductHeroRenderer snapshot={snapshot} pageIndex={safeIndex} fill={fill} />;
    case "PROMOTION_BOARD":
      return <PromotionBoardRenderer snapshot={snapshot} pageIndex={safeIndex} fill={fill} />;
    case "PRICE_TABLE":
      return <PriceTableRenderer snapshot={snapshot} pageIndex={safeIndex} fill={fill} />;
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
  const pendingRef = useRef<PriceTableSnapshot | null>(null);
  const pageIndexRef = useRef(0);
  const urgentSkipRef = useRef(false);

  useEffect(() => {
    let alive = true;
    setFailed(false);
    setSnapshot(null);
    pendingRef.current = null;
    urgentSkipRef.current = false;
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentId, token, itemKey]);

  // WS invalidation → prefetch; apply on page boundary (or urgent skip if STALE)
  useEffect(() => {
    return subscribeDynamicInvalidation(async (payload) => {
      if (payload.dynamic_content_id !== contentId) return;
      const reason = (payload.reason || "").toUpperCase();
      console.info("[display] dynamic.prefetched?", contentId, reason);
      clearDynamicContentCache(contentId);
      const result = await fetchPlayerDynamicContent(contentId, token);
      if (!result.ok) {
        if (result.reason === "stale" || result.reason === "forbidden") {
          console.warn("[display] dynamic.stale.skipped", contentId);
          urgentSkipRef.current = true;
          setFailed(true);
          onFailed?.();
        }
        return;
      }
      const normalized = normalizePriceTableSnapshot(result.payload);
      if (!normalized || !normalized.pages?.length || (normalized.item_count ?? 0) === 0) {
        urgentSkipRef.current = true;
        setFailed(true);
        onFailed?.();
        return;
      }
      // Safe boundary: hold pending until page index changes (unless paused/override)
      pendingRef.current = normalized;
      console.info("[display] dynamic.prefetched", contentId);
      if (paused) {
        // During QUEUE_CALL: apply when resume (next render with pending)
        return;
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentId, token, paused]);

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

  // Apply pending snapshot on page boundary or when returning from pause
  useEffect(() => {
    const pending = pendingRef.current;
    if (!pending || failed) return;
    if (paused) return;
    if (pageIndex !== pageIndexRef.current || !snapshot) {
      const nextCount = Math.max(1, pending.page_count ?? pending.pages?.length ?? 1);
      // shrink-safe: pageIndex clamped in renderByType
      void nextCount;
      setSnapshot(pending);
      pendingRef.current = null;
      console.info("[display] dynamic.applied_boundary", contentId);
    }
    pageIndexRef.current = pageIndex;
  }, [pageIndex, paused, failed, snapshot, contentId]);

  // valid_until hard expiry while on screen
  useEffect(() => {
    if (!data?.valid_until || failed) return;
    const until = Date.parse(data.valid_until);
    if (Number.isNaN(until)) return;
    const ms = until - Date.now();
    if (ms <= 0) {
      clearDynamicContentCache(contentId);
      void (async () => {
        const result = await fetchPlayerDynamicContent(contentId, token);
        if (!result.ok) {
          setFailed(true);
          onFailed?.();
          return;
        }
        const normalized = normalizePriceTableSnapshot(result.payload);
        if (!normalized?.pages?.length) {
          setFailed(true);
          onFailed?.();
          return;
        }
        pendingRef.current = normalized;
      })();
      return;
    }
    const t = window.setTimeout(() => {
      clearDynamicContentCache(contentId);
      void fetchPlayerDynamicContent(contentId, token).then((result) => {
        if (!result.ok) {
          setFailed(true);
          onFailed?.();
          return;
        }
        const normalized = normalizePriceTableSnapshot(result.payload);
        if (normalized?.pages?.length) pendingRef.current = normalized;
      });
    }, ms);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.valid_until, contentId, token, failed]);

  if (failed || urgentSkipRef.current) return <DynamicContentFallback />;
  if (!data) {
    return <div className="absolute inset-0 bg-brand-950" data-testid="dynamic-loading" />;
  }

  return renderByType(data, pageIndex, true);
}
