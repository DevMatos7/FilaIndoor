import { formatBrl } from "../../utils/formatPrice";
import type { QuantityTier } from "./dynamicContentTypes";

type Props = {
  tiers: QuantityTier[];
};

/** Quantity conditions stay visually next to the price block. */
export function QuantityPrice({ tiers }: Props) {
  if (!tiers.length) return null;
  return (
    <div className="mt-1 space-y-0.5 text-[clamp(12px,1.1vw,20px)] text-white/75" data-testid="quantity-tiers">
      {tiers.map((t) => (
        <div key={`${t.min_qty}-${t.amount}`} className="flex flex-wrap items-baseline gap-x-2">
          <span className="uppercase tracking-wide">{t.condition_text}</span>
          <span className="tabular-nums font-semibold text-white">
            {t.formatted_amount || formatBrl(t.amount)}
          </span>
        </div>
      ))}
    </div>
  );
}
