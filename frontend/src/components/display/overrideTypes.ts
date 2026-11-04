/** Screen Override Engine types (UX-6C). */

export type OverrideType = "EMERGENCY" | "QUEUE_CALL" | "MANUAL" | "CAMPAIGN";

export type TargetScope = "STORE" | "QUEUE" | "DISPLAY" | "CHANNEL";

export type ScreenOverride = {
  id: string;
  store_id: string;
  override_type: OverrideType | string;
  priority: number;
  target_scope: TargetScope | string;
  target_id?: string | null;
  payload: Record<string, unknown>;
  starts_at: string;
  expires_at: string;
  cancelled_at?: string | null;
  dedupe_key?: string | null;
  source_type?: string | null;
  source_id?: string | null;
  created_at?: string;
};

/** Z-index convention — overrides above all layout zones. */
export const DISPLAY_LAYER_Z = {
  layout: 0,
  override: 40,
} as const;

export const OVERRIDE_PRIORITY: Record<string, number> = {
  EMERGENCY: 400,
  QUEUE_CALL: 300,
  MANUAL: 200,
  CAMPAIGN: 100,
};

export const LEGACY_QUEUE_CALL_MS = 7000;

export function parseOverrideTime(iso: string | undefined | null): number {
  if (!iso) return 0;
  const t = Date.parse(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  return Number.isFinite(t) ? t : 0;
}

export function isOverrideActive(o: ScreenOverride, now = Date.now()): boolean {
  if (o.cancelled_at) return false;
  const start = parseOverrideTime(o.starts_at);
  const end = parseOverrideTime(o.expires_at);
  return start <= now && now < end;
}
