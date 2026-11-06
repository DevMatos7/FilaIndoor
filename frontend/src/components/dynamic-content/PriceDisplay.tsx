import { formatBrl } from "../../utils/formatPrice";
import type { PriceTableItem } from "./dynamicContentTypes";

type Props = {
  item: PriceTableItem;
  emphasizePromo?: boolean;
};

/** Dominant price column — shared by admin + TV. */
export function PriceDisplay({ item, emphasizePromo }: Props) {
  return (
    <div className="shrink-0 text-right" data-price-product={item.product_id}>
      {item.show_from_to && item.formatted_regular && (
        <div className="text-[clamp(12px,1.1vw,22px)] text-white/50 line-through">
          DE {item.formatted_regular}
        </div>
      )}
      <div
        className={`font-display text-[clamp(22px,2.4vw,48px)] font-semibold tabular-nums ${
          emphasizePromo && item.is_promotion ? "text-amber-300" : "text-white"
        }`}
        data-testid="price-display"
        data-price-value={String(item.display_price ?? "")}
      >
        {item.show_from_to ? "POR " : ""}
        {item.formatted_display || formatBrl(item.display_price)}
      </div>
      {item.is_promotion && (
        <div className="text-[clamp(11px,1vw,18px)] uppercase tracking-wider text-amber-200/90">Promoção</div>
      )}
    </div>
  );
}
