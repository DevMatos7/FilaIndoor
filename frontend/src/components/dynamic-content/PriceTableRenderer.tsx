import { PriceTablePageView } from "./PriceTablePage";
import {
  normalizePriceTableSnapshot,
  type PriceTableSnapshot,
} from "./dynamicContentTypes";

type Props = {
  snapshot: PriceTableSnapshot | null;
  /** 0-based page index controlled by parent (PlaybackClock / admin). */
  pageIndex?: number;
  className?: string;
  /** When true, fill parent (TV). When false, natural size inside scaled admin frame. */
  fill?: boolean;
};

/**
 * Shared PRICE_TABLE renderer — Admin Preview + Playlist Studio + Display Player.
 * Scale/container differ; visual rules do not.
 */
export function PriceTableRenderer({ snapshot, pageIndex = 0, className = "", fill = true }: Props) {
  const data = normalizePriceTableSnapshot(snapshot);
  if (!data || !data.pages?.length) {
    return (
      <div className={`flex h-full items-center justify-center bg-[#0f1720] text-white/50 ${className}`}>
        Sem tabela
      </div>
    );
  }

  const pages = data.pages;
  const idx = ((pageIndex % pages.length) + pages.length) % pages.length;
  const page = pages[idx];
  const columns = data.template?.config?.columns === 2 ? 2 : 1;
  const emphasize = Boolean(data.template?.config?.emphasize_promo);
  const showUnit = data.template?.config?.show_unit !== false;

  return (
    <div
      className={`bg-[#0f1720] text-white ${fill ? "absolute inset-0" : "relative"} ${className}`}
      data-testid="price-table-renderer"
      data-page-index={idx}
      data-page-count={pages.length}
      data-template={data.template?.slug || ""}
    >
      <div className="flex h-full flex-col p-[4%]">
        <header className="mb-[3%] border-b border-white/20 pb-[2%]">
          <h2 className="font-display text-[clamp(28px,3.2vw,64px)] font-semibold tracking-wide">
            {data.title || "Tabela de preços"}
          </h2>
        </header>
        <PriceTablePageView
          items={page?.items || []}
          columns={columns}
          emphasizePromo={emphasize}
          showUnit={showUnit}
        />
      </div>
    </div>
  );
}
