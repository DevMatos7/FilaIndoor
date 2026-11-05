import { useMemo, useState } from "react";
import { Button } from "../../design-system";
import { formatBrl } from "../../utils/formatPrice";

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

export type SnapshotPayload = {
  title?: string;
  template?: { slug?: string; config?: { columns?: number; emphasize_promo?: boolean } };
  pages: { number: number; items: SnapshotItem[] }[];
  source?: { freshness?: string; generated_at?: string; provider?: string };
  pagination?: { page_count?: number; total_duration_seconds?: number };
  warnings?: string[];
  status?: string;
  item_count?: number;
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

export function PriceTablePreview({ snapshot, adminMeta = true }: Props) {
  const [pageIdx, setPageIdx] = useState(0);
  const [vp, setVp] = useState<(typeof VIEWPORTS)[number]>(VIEWPORTS[0]);

  const page = snapshot?.pages?.[pageIdx] || snapshot?.pages?.[0];
  const columns = snapshot?.template?.config?.columns === 2 ? 2 : 1;
  const emphasize = Boolean(snapshot?.template?.config?.emphasize_promo);

  const scaleStyle = useMemo(() => {
    // container scales to fit ~960px wide in admin
    const maxW = 960;
    const s = Math.min(1, maxW / vp.w);
    return { width: vp.w, height: vp.h, transform: `scale(${s})`, transformOrigin: "top left" as const };
  }, [vp]);

  if (!snapshot) {
    return <div className="rounded-ds border border-dashed border-brand-200 p-8 text-ink/50">Sem preview</div>;
  }

  const outerH = Math.min(540, vp.h * Math.min(1, 960 / vp.w));

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
            {(page?.number || pageIdx + 1)} / {snapshot.pages?.length || 1}
          </span>
          <Button
            size="sm"
            variant="secondary"
            disabled={pageIdx >= (snapshot.pages?.length || 1) - 1}
            onClick={() => setPageIdx((p) => Math.min((snapshot.pages?.length || 1) - 1, p + 1))}
          >
            Próxima
          </Button>
        </div>
      </div>

      {adminMeta && (
        <p className="text-xs text-ink/60">
          Fonte: {snapshot.source?.provider || "CISS"} · {snapshot.source?.freshness} · status {snapshot.status}
          {snapshot.pagination?.total_duration_seconds != null
            ? ` · ciclo ${snapshot.pagination.total_duration_seconds}s`
            : ""}
        </p>
      )}

      <div className="overflow-hidden rounded-ds border border-brand-200 bg-black/5" style={{ height: outerH }}>
        <div style={scaleStyle} className="bg-[#0f1720] text-white shadow-lg">
          <div className="flex h-full flex-col p-[4%]">
            <header className="mb-[3%] border-b border-white/20 pb-[2%]">
              <h2 className="font-display text-[clamp(28px,3.2vw,64px)] font-semibold tracking-wide">
                {snapshot.title || "Tabela de preços"}
              </h2>
            </header>
            <div
              className={
                columns === 2
                  ? "grid flex-1 grid-cols-2 gap-x-[4%] gap-y-[1.5%] content-start"
                  : "flex flex-1 flex-col gap-[1.2%]"
              }
            >
              {(page?.items || []).map((item) => (
                <div
                  key={item.product_id}
                  className={`flex items-baseline justify-between gap-4 border-b border-white/10 pb-[0.8%] ${
                    emphasize && item.is_promotion ? "bg-amber-500/15 px-2" : ""
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-display text-[clamp(18px,1.8vw,36px)] font-medium leading-tight">
                      {item.description}
                      {item.unit ? ` ${item.unit}` : ""}
                    </div>
                    {item.quantity_tiers && item.quantity_tiers.length > 0 && (
                      <div className="mt-1 space-y-0.5 text-[clamp(12px,1.1vw,20px)] text-white/75">
                        {item.quantity_tiers.map((t) => (
                          <div key={`${t.min_qty}-${t.amount}`}>
                            {t.condition_text}: {t.formatted_amount || formatBrl(t.amount)}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    {item.show_from_to && item.formatted_regular && (
                      <div className="text-[clamp(12px,1.1vw,22px)] text-white/50 line-through">
                        DE {item.formatted_regular}
                      </div>
                    )}
                    <div
                      className={`font-display text-[clamp(22px,2.4vw,48px)] font-semibold tabular-nums ${
                        item.is_promotion ? "text-amber-300" : "text-white"
                      }`}
                    >
                      {item.show_from_to ? "POR " : ""}
                      {item.formatted_display || formatBrl(item.display_price)}
                    </div>
                    {item.is_promotion && (
                      <div className="text-[clamp(11px,1vw,18px)] uppercase tracking-wider text-amber-200/90">
                        Promoção
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
