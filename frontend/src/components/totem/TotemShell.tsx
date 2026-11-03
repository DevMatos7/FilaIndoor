import { CSSProperties, ReactNode } from "react";
import { DEFAULT_TOTEM_BRAND, TotemBrand } from "./types";

type Props = {
  children: ReactNode;
  brand?: Partial<TotemBrand>;
  className?: string;
};

/** Full-viewport kiosk frame — CSS vars prepared for future brand config. */
export function TotemShell({ children, brand, className }: Props) {
  const b = { ...DEFAULT_TOTEM_BRAND, ...brand };
  const style = {
    "--totem-brand": b.primary,
    "--totem-surface": b.surface,
    background: `linear-gradient(180deg, ${b.primary} 0%, #103a28 48%, #0c2b1e 100%)`,
  } as CSSProperties;
  return (
    <div
      className={`totem-root flex min-h-[100dvh] flex-col font-sans text-brand-950 ${className || ""}`}
      style={style}
      data-totem-brand={b.wordmark}
    >
      {children}
    </div>
  );
}
