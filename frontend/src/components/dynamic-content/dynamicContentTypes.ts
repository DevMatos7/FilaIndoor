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
      emphasize_promo?: boolean;
      show_unit?: boolean;
    };
  };
  pages: PriceTablePage[];
  source?: { freshness?: string; generated_at?: string; provider?: string; data_version?: string };
  pagination?: {
    page_count?: number;
    page_duration_seconds?: number;
    duration_mode?: string;
    total_duration_seconds?: number;
    items_per_page?: number;
  };
  warnings?: string[];
};

export function normalizePriceTableSnapshot(raw: PriceTableSnapshot | null | undefined): PriceTableSnapshot | null {
  if (!raw) return null;
  const pages = raw.pages || [];
  const pag = raw.pagination;
  return {
    ...raw,
    title: raw.title || raw.name || "Tabela de preços",
    freshness: raw.freshness || raw.source?.freshness,
    page_duration_seconds: raw.page_duration_seconds ?? pag?.page_duration_seconds ?? 8,
    total_duration_seconds: raw.total_duration_seconds ?? pag?.total_duration_seconds,
    duration_mode: raw.duration_mode ?? pag?.duration_mode ?? "FULL_CYCLE",
    page_count: raw.page_count ?? pag?.page_count ?? pages.length,
    pages,
  };
}
