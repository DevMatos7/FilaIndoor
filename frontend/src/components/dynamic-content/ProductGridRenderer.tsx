import { ProductCard, type VisualProductItem } from "./ProductCard";
import {
  normalizePriceTableSnapshot,
  type PriceTableSnapshot,
} from "./dynamicContentTypes";

type Props = {
  snapshot: PriceTableSnapshot | null;
  pageIndex?: number;
  fill?: boolean;
  className?: string;
};

export function ProductGridRenderer({ snapshot, pageIndex = 0, fill = true, className = "" }: Props) {
  const data = normalizePriceTableSnapshot(snapshot);
  if (!data?.pages?.length) {
    return (
      <div className={`flex h-full items-center justify-center bg-[#0f1720] text-white/50 ${className}`}>
        Sem grade
      </div>
    );
  }
  const pages = data.pages;
  const idx = ((pageIndex % pages.length) + pages.length) % pages.length;
  const page = pages[idx];
  const cols = Number(data.template?.config?.columns || data.pagination?.columns || 2);
  const showImage = data.show_image !== false && data.template?.config?.show_image !== false;
  const showUnit = data.template?.config?.show_unit !== false;
  const showRegular = data.template?.config?.show_regular_price !== false;
  const emphasize = Boolean(data.template?.config?.emphasize_promo);
  const fit = (data.image_fit || data.template?.config?.image_fit || "contain") as "contain" | "cover";

  return (
    <div
      className={`bg-[#0f1720] text-white ${fill ? "absolute inset-0" : "relative"} ${className}`}
      data-testid="product-grid-renderer"
      data-page-index={idx}
      data-template={data.template?.slug || ""}
    >
      <div className="flex h-full flex-col p-[3%]">
        <header className="mb-[2%] border-b border-white/15 pb-[1.5%]">
          <h2 className="font-display text-[clamp(24px,2.8vw,56px)] font-semibold tracking-wide">
            {data.title || "Grade de produtos"}
          </h2>
        </header>
        <div
          className="grid flex-1 gap-[2%] content-stretch"
          style={{ gridTemplateColumns: `repeat(${Math.max(1, cols)}, minmax(0, 1fr))` }}
        >
          {(page?.items || []).map((item) => (
            <ProductCard
              key={item.product_id}
              item={item as VisualProductItem}
              showImage={showImage}
              showUnit={showUnit}
              showRegular={showRegular}
              emphasizePromo={emphasize}
              imageFit={fit}
              compact={cols >= 4}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
