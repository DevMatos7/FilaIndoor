import { useState } from "react";

type Props = {
  url?: string | null;
  alt: string;
  fit?: "contain" | "cover";
  className?: string;
  /** TV / current page should eager-load to avoid flash. */
  eager?: boolean;
  /** Notify parent so layouts (e.g. Hero) can collapse empty image column. */
  onStatusChange?: (ok: boolean) => void;
};

/** Product image with silent fallback (no broken-icon flash). */
export function ProductImage({
  url,
  alt,
  fit = "contain",
  className = "",
  eager = true,
  onStatusChange,
}: Props) {
  const [failed, setFailed] = useState(false);
  if (!url || failed) {
    return (
      <div
        className={`flex items-center justify-center bg-[#0b1220] ${className}`}
        data-testid="product-image-fallback"
        aria-hidden
      />
    );
  }
  return (
    <img
      src={url}
      alt={alt}
      className={`${fit === "cover" ? "object-cover" : "object-contain"} ${className}`}
      data-testid="product-image"
      onLoad={() => onStatusChange?.(true)}
      onError={() => {
        setFailed(true);
        onStatusChange?.(false);
      }}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
    />
  );
}
