export type QuantityTier = {
  min_qty: number;
  amount: number;
  condition_text: string;
  formatted_amount?: string;
};

export type PriceTableItem = {
  product_id: string;
  description: string;
  unit?: string | null;
  display_price?: number | null;
  regular_price?: number | null;
  is_promotion?: boolean;
  show_from_to?: boolean;
  formatted_display?: string | null;
  formatted_regular?: string | null;
  quantity_tiers?: QuantityTier[];
  image?: { asset_id?: string; url?: string; name?: string } | null;
};

export type PriceTablePage = {
  number: number;
  items: PriceTableItem[];
};

/** Shared snapshot shape for admin preview + TV player. */
export type PriceTableSnapshot = {
  id?: string;
  type?: string;
  name?: string;
  title?: string;
  version?: string;
  generated_at?: string;
  freshness?: string;
  valid_until?: string;
  duration_mode?: string;
  page_duration_seconds?: number;
  total_duration_seconds?: number;
  page_count?: number;
  item_count?: number;
  status?: string;
  content_hash?: string;
  data_version?: string;
  template?: {
    id?: string;
    slug?: string;
    name?: string;
    config?: {
      columns?: number;
      rows?: number;
      emphasize_promo?: boolean;
      show_unit?: boolean;
      show_image?: boolean;
      show_regular_price?: boolean;
      show_promo_badge?: boolean;
      image_fit?: "contain" | "cover" | string;
      hero_layout?: string;
    };
  };
  pages: PriceTablePage[];
  source?: { freshness?: string; generated_at?: string; provider?: string; data_version?: string };
  content_type?: string;
  image_fit?: string;
  show_image?: boolean;
  pagination?: {
    page_count?: number;
    page_duration_seconds?: number;
    duration_mode?: string;
    total_duration_seconds?: number;
    items_per_page?: number;
    columns?: number;
    rows?: number;
  };
  warnings?: string[];
};

export function normalizePriceTableSnapshot(raw: PriceTableSnapshot | null | undefined): PriceTableSnapshot | null {
  if (!raw) return null;
  const pages = raw.pages || [];
  const pag = raw.pagination;
  return {
    ...raw,
    content_type: (raw.content_type || raw.type || "PRICE_TABLE").toUpperCase(),
    title: raw.title || raw.name || "Conteúdo dinâmico",
    freshness: raw.freshness || raw.source?.freshness,
    page_duration_seconds: raw.page_duration_seconds ?? pag?.page_duration_seconds ?? 8,
    total_duration_seconds: raw.total_duration_seconds ?? pag?.total_duration_seconds,
    duration_mode: raw.duration_mode ?? pag?.duration_mode ?? "FULL_CYCLE",
    page_count: raw.page_count ?? pag?.page_count ?? pages.length,
    image_fit: raw.image_fit || raw.template?.config?.image_fit || "contain",
    show_image: raw.show_image !== false,
    pages,
  };
}

export function contentTypeOf(raw: PriceTableSnapshot | null | undefined): string {
  return (raw?.content_type || raw?.type || "PRICE_TABLE").toUpperCase();
}
