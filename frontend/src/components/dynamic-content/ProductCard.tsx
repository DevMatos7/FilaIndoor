import { formatBrl } from "../../utils/formatPrice";
import { ProductImage } from "./ProductImage";
import { QuantityPrice } from "./QuantityPrice";
import type { PriceTableItem } from "./dynamicContentTypes";

export type VisualProductItem = PriceTableItem & {
  image?: { asset_id?: string; url?: string; name?: string } | null;
};

type Props = {
  item: VisualProductItem;
  showImage?: boolean;
  showUnit?: boolean;
  showRegular?: boolean;
  emphasizePromo?: boolean;
  imageFit?: "contain" | "cover";
  compact?: boolean;
};

export function ProductCard({
  item,
  showImage = true,
  showUnit = true,
  showRegular = true,
  emphasizePromo,
  imageFit = "contain",
  compact,
}: Props) {
  return (
    <div
      className={`flex h-full flex-col overflow-hidden border border-white/10 bg-white/[0.03] ${
        emphasizePromo && item.is_promotion ? "ring-1 ring-amber-400/40" : ""
      }`}
      data-testid="product-card"
      data-product-id={item.product_id}
    >
      {showImage && (
        <div
          className={`relative min-h-0 flex-[1.1] ${compact ? "max-h-[55%]" : "max-h-[58%]"} bg-[#0b1220]`}
        >
          <ProductImage
            url={item.image?.url}
            alt={item.description}
            fit={imageFit}
            className="absolute inset-0 h-full w-full p-[6%]"
          />
        </div>
      )}
      <div className="flex min-h-0 flex-[0.9] flex-col justify-between gap-1 overflow-hidden p-[6%]">
        <div
          className="line-clamp-2 font-display text-[clamp(14px,1.4vw,28px)] font-medium leading-tight"
          data-testid="product-description"
        >
          {item.description}
        </div>
        {item.quantity_tiers && item.quantity_tiers.length > 0 && (
          <QuantityPrice tiers={item.quantity_tiers} />
        )}
        <div className="mt-auto text-right">
          {showRegular && item.show_from_to && item.formatted_regular && (
            <div className="text-[clamp(11px,1vw,18px)] text-white/50 line-through">
              DE {item.formatted_regular}
            </div>
          )}
          <div
            className={`font-display text-[clamp(18px,2vw,40px)] font-semibold tabular-nums ${
              item.is_promotion ? "text-amber-300" : "text-white"
            }`}
            data-testid="price-display"
            data-price-value={String(item.display_price ?? "")}
            data-price-product={item.product_id}
          >
            {item.show_from_to ? "POR " : ""}
            {item.formatted_display || formatBrl(item.display_price)}
            {showUnit && item.unit ? (
              <span className="ml-1 text-[clamp(12px,1.1vw,20px)] font-normal text-white/70">
                /{item.unit.toLowerCase()}
              </span>
            ) : null}
          </div>
          {emphasizePromo && item.is_promotion && (
            <div className="text-[clamp(10px,0.9vw,16px)] uppercase tracking-wider text-amber-200/90">
              Oferta
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
