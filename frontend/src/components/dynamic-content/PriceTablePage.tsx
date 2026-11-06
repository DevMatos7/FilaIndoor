import { PriceDisplay } from "./PriceDisplay";
import { QuantityPrice } from "./QuantityPrice";
import type { PriceTableItem } from "./dynamicContentTypes";

type Props = {
  items: PriceTableItem[];
  columns?: number;
  emphasizePromo?: boolean;
  showUnit?: boolean;
};

export function PriceTablePageView({ items, columns = 1, emphasizePromo, showUnit = true }: Props) {
  return (
    <div
      className={
        columns === 2
          ? "grid flex-1 grid-cols-2 gap-x-[4%] gap-y-[1.5%] content-start"
          : "flex flex-1 flex-col gap-[1.2%]"
      }
      data-testid="price-table-page"
    >
      {items.map((item) => (
        <div
          key={item.product_id}
          className={`flex items-baseline justify-between gap-4 border-b border-white/10 pb-[0.8%] ${
            emphasizePromo && item.is_promotion ? "bg-amber-500/15 px-2" : ""
          }`}
          data-testid="price-table-row"
          data-product-id={item.product_id}
        >
          <div className="min-w-0 flex-1">
            <div
              className="line-clamp-2 font-display text-[clamp(18px,1.8vw,36px)] font-medium leading-tight"
              data-testid="product-description"
            >
              {item.description}
              {showUnit && item.unit ? ` · ${item.unit}` : ""}
            </div>
            {item.quantity_tiers && item.quantity_tiers.length > 0 && (
              <QuantityPrice tiers={item.quantity_tiers} />
            )}
          </div>
          <PriceDisplay item={item} emphasizePromo={emphasizePromo} />
        </div>
      ))}
    </div>
  );
}
