import { ProductGridRenderer } from "./ProductGridRenderer";
import type { PriceTableSnapshot } from "./dynamicContentTypes";

type Props = {
  snapshot: PriceTableSnapshot | null;
  pageIndex?: number;
  fill?: boolean;
  className?: string;
};

/** Visual campaign board — same grid engine, promo emphasis. */
export function PromotionBoardRenderer(props: Props) {
  const snap = props.snapshot
    ? {
        ...props.snapshot,
        template: {
          ...props.snapshot.template,
          config: {
            ...(props.snapshot.template?.config || {}),
            emphasize_promo: true,
            show_promo_badge: true,
            show_regular_price: true,
          },
        },
      }
    : null;
  return (
    <div data-testid="promotion-board-renderer" className={props.fill ? "absolute inset-0" : "relative"}>
      <ProductGridRenderer {...props} snapshot={snap} />
    </div>
  );
}
