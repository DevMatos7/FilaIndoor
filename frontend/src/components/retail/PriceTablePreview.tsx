import { useMemo, useState } from "react";
import { Button } from "../../design-system";
import { PriceTableRenderer } from "../dynamic-content/PriceTableRenderer";
import type { PriceTableSnapshot } from "../dynamic-content/dynamicContentTypes";

export type SnapshotItem = {
  product_id: string;
  description: string;
  unit?: string | null;
  display_price?: number | null;
  regular_price?: number | null;
  is_promotion?: boolean;
  show_from_to?: boolean;
  formatted_display?: string | null;
  formatted_regular?: string | null;
  quantity_tiers?: { min_qty: number; amount: number; condition_text: string; formatted_amount?: string }[];
};

export type SnapshotPayload = PriceTableSnapshot & {
  pages: { number: number; items: SnapshotItem[] }[];
};

const VIEWPORTS = [
  { id: "1080p", label: "1920×1080", w: 1920, h: 1080 },
  { id: "4k", label: "3840×2160", w: 3840, h: 2160 },
  { id: "portrait", label: "1080×1920", w: 1080, h: 1920 },
] as const;

type Props = {
  snapshot: SnapshotPayload | null;
  adminMeta?: boolean;
};

/** Admin chrome around the shared PriceTableRenderer (same as TV). */
export function PriceTablePreview({ snapshot, adminMeta = true }: Props) {
  const [pageIdx, setPageIdx] = useState(0);
  const [vp, setVp] = useState<(typeof VIEWPORTS)[number]>(VIEWPORTS[0]);

  const scaleStyle = useMemo(() => {
    const maxW = 960;
    const s = Math.min(1, maxW / vp.w);
    return { width: vp.w, height: vp.h, transform: `scale(${s})`, transformOrigin: "top left" as const };
  }, [vp]);

  if (!snapshot) {
    return <div className="rounded-ds border border-dashed border-brand-200 p-8 text-ink/50">Sem preview</div>;
  }

  const outerH = Math.min(540, vp.h * Math.min(1, 960 / vp.w));
  const pageCount = snapshot.pages?.length || 1;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {VIEWPORTS.map((v) => (
          <Button key={v.id} size="sm" variant={vp.id === v.id ? "primary" : "secondary"} onClick={() => setVp(v)}>
            {v.label}
          </Button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={pageIdx <= 0}
            onClick={() => setPageIdx((p) => Math.max(0, p - 1))}
          >
            Anterior
          </Button>
          <span className="text-sm text-ink/70">
            {pageIdx + 1} / {pageCount}
          </span>
          <Button
            size="sm"
            variant="secondary"
            disabled={pageIdx >= pageCount - 1}
            onClick={() => setPageIdx((p) => Math.min(pageCount - 1, p + 1))}
          >
            Próxima
          </Button>
        </div>
      </div>

      {adminMeta && (
        <p className="text-xs text-ink/60">
          Fonte: {snapshot.source?.provider || "CISS"} · {snapshot.source?.freshness || snapshot.freshness} · status{" "}
          {snapshot.status}
          {(snapshot.pagination?.total_duration_seconds ?? snapshot.total_duration_seconds) != null
            ? ` · ciclo ${snapshot.pagination?.total_duration_seconds ?? snapshot.total_duration_seconds}s`
            : ""}
        </p>
      )}

      <div className="overflow-hidden rounded-ds border border-brand-200 bg-black/5" style={{ height: outerH }}>
        <div style={scaleStyle} className="relative shadow-lg">
          <PriceTableRenderer snapshot={snapshot} pageIndex={pageIdx} fill />
        </div>
      </div>
    </div>
  );
}
