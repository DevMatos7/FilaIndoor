export type ZoneType = "MEDIA" | "QUEUE" | "TEXT" | "CLOCK" | "TICKER" | string;

export type LayoutZone = {
  id: string;
  name: string;
  type: ZoneType;
  x: number;
  y: number;
  width: number;
  height: number;
  z_index: number;
  config?: Record<string, unknown>;
};

export type ResolvedLayout = {
  id: string;
  store_id?: string | null;
  name: string;
  slug: string;
  orientation: string;
  aspect_ratio: string;
  background?: { type?: string; value?: string } | null;
  config?: Record<string, unknown> | null;
  zones: LayoutZone[];
  resolved_from?: string;
  legacy_layout?: string;
};

/** Emergency fallback identical to UX-6A media + footer (cache antigo / layout inválido). */
export const EMERGENCY_LAYOUT: ResolvedLayout = {
  id: "emergency-media-queue-footer",
  name: "Mídia + fila inferior",
  slug: "media_queue_footer",
  orientation: "LANDSCAPE",
  aspect_ratio: "16:9",
  background: { type: "color", value: "#071a12" },
  config: { safe_area: 3 },
  resolved_from: "frontend_emergency",
  zones: [
    {
      id: "emergency-media",
      name: "Mídia",
      type: "MEDIA",
      x: 0,
      y: 0,
      width: 100,
      height: 82,
      z_index: 0,
      config: {},
    },
    {
      id: "emergency-queue",
      name: "Fila",
      type: "QUEUE",
      x: 0,
      y: 82,
      width: 100,
      height: 18,
      z_index: 1,
      config: { variant: "footer", show_last_called: true, show_label: true },
    },
  ],
};

export function isValidLayout(layout: ResolvedLayout | null | undefined): layout is ResolvedLayout {
  return !!layout && Array.isArray(layout.zones) && layout.zones.length > 0;
}
