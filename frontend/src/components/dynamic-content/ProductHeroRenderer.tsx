import { useEffect, useState } from "react";
import { formatBrl } from "../../utils/formatPrice";
import { ProductImage } from "./ProductImage";
import { QuantityPrice } from "./QuantityPrice";
import type { VisualProductItem } from "./ProductCard";
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

export function ProductHeroRenderer({ snapshot, pageIndex = 0, fill = true, className = "" }: Props) {
  const data = normalizePriceTableSnapshot(snapshot);
  const pages = data?.pages || [];
  const idx = pages.length ? ((pageIndex % pages.length) + pages.length) % pages.length : 0;
  const item = (pages[idx]?.items?.[0] || null) as VisualProductItem | null;
  const imageUrl = item?.image?.url || null;
  const [imageOk, setImageOk] = useState(Boolean(imageUrl));

  useEffect(() => {
    setImageOk(Boolean(imageUrl));
  }, [imageUrl, item?.product_id]);

  if (!data?.pages?.length) {
    return (
      <div className={`flex h-full items-center justify-center bg-[#0f1720] text-white/50 ${className}`}>
        Sem destaque
      </div>
    );
  }
  if (!item) {
    return (
      <div className={`flex h-full items-center justify-center bg-[#0f1720] text-white/50 ${className}`}>
        Sem produto
      </div>
    );
  }
  const promo = Boolean(data.template?.config?.emphasize_promo || item.is_promotion);
  const fit = (data.image_fit || data.template?.config?.image_fit || "contain") as "contain" | "cover";
  const showImageColumn = Boolean(imageUrl) && imageOk;

  return (
    <div
      className={`bg-[#0f1720] text-white ${fill ? "absolute inset-0" : "relative"} ${className}`}
      data-testid="product-hero-renderer"
      data-page-index={idx}
      data-product-id={item.product_id}
    >
      <div className={`grid h-full ${showImageColumn ? "grid-cols-[1.15fr_1fr]" : "grid-cols-1"}`}>
        {Boolean(imageUrl) && (
          <div className={`relative bg-[#0b1220] ${showImageColumn ? "" : "hidden"}`}>
            <ProductImage
              url={imageUrl}
              alt={item.description}
              fit={fit}
              className="absolute inset-0 h-full w-full p-[5%]"
              onStatusChange={setImageOk}
            />
          </div>
        )}
        <div className="flex flex-col justify-center gap-[3%] p-[6%]">
          {promo && item.is_promotion && (
            <div className="text-[clamp(14px,1.4vw,28px)] font-semibold uppercase tracking-[0.2em] text-amber-300">
              Oferta
            </div>
          )}
          <h2
            className="font-display text-[clamp(28px,3.4vw,72px)] font-semibold leading-tight"
            data-testid="product-description"
          >
            {item.description}
          </h2>
          {item.quantity_tiers && item.quantity_tiers.length > 0 && (
            <QuantityPrice tiers={item.quantity_tiers} />
          )}
          <div>
            {item.show_from_to && item.formatted_regular && (
              <div className="text-[clamp(16px,1.6vw,32px)] text-white/50 line-through">
                DE {item.formatted_regular}
              </div>
            )}
            <div
              className={`font-display text-[clamp(36px,4.5vw,96px)] font-semibold tabular-nums ${
                item.is_promotion ? "text-amber-300" : "text-white"
              }`}
              data-testid="price-display"
              data-price-value={String(item.display_price ?? "")}
              data-price-product={item.product_id}
            >
              {item.show_from_to ? "POR " : ""}
              {item.formatted_display || formatBrl(item.display_price)}
            </div>
            {item.unit && (
              <div className="mt-1 text-[clamp(16px,1.6vw,32px)] text-white/70">
                /{item.unit.toLowerCase()}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
