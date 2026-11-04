import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { nextExpiryMs, resolveCurrentOverride } from "./OverrideResolver";
import {
  isOverrideActive,
  LEGACY_QUEUE_CALL_MS,
  OVERRIDE_PRIORITY,
  parseOverrideTime,
  type ScreenOverride,
} from "./overrideTypes";

export type PlayerMatchContext = {
  storeId?: string | null;
  queueId?: string | null;
  displayId?: string | null;
  channelId?: string | null;
};

function matchesTarget(o: ScreenOverride, ctx: PlayerMatchContext): boolean {
  const scope = (o.target_scope || "").toUpperCase();
  if (o.store_id && ctx.storeId && o.store_id !== ctx.storeId) return false;
  if (scope === "STORE") return true;
  if (scope === "QUEUE") return !!ctx.queueId && o.target_id === ctx.queueId;
  if (scope === "DISPLAY") return !!ctx.displayId && o.target_id === ctx.displayId;
  if (scope === "CHANNEL") return !!ctx.channelId && o.target_id === ctx.channelId;
  return false;
}

function upsert(list: ScreenOverride[], next: ScreenOverride): ScreenOverride[] {
  const filtered = list.filter((o) => o.id !== next.id && !(next.dedupe_key && o.dedupe_key === next.dedupe_key));
  return [...filtered, next];
}

function legacyQueueCallFromEvent(data: {
  ticket?: string;
  ticket_id?: string;
  ticket_type?: string;
  department?: string;
  queue_id?: string;
  event_id?: string;
}): ScreenOverride {
  const now = Date.now();
  const id = `legacy:${data.event_id || data.ticket_id || data.ticket}:${now}`;
  return {
    id,
    store_id: "",
    override_type: "QUEUE_CALL",
    priority: OVERRIDE_PRIORITY.QUEUE_CALL,
    target_scope: "QUEUE",
    target_id: data.queue_id || null,
    payload: {
      ticket_id: data.ticket_id,
      ticket_number: data.ticket,
      queue_id: data.queue_id,
      department_name: data.department || "Atendimento",
      ticket_type: data.ticket_type,
      instruction: "Dirija-se ao balcão",
      legacy: true,
    },
    starts_at: new Date(now).toISOString(),
    expires_at: new Date(now + LEGACY_QUEUE_CALL_MS).toISOString(),
    dedupe_key: id,
    source_type: "LEGACY_WS",
  };
}

export function useOverrideManager(ctx: PlayerMatchContext) {
  const [overrides, setOverrides] = useState<ScreenOverride[]>([]);
  const spokenRef = useRef<Set<string>>(new Set());
  const timerRef = useRef<number | null>(null);
  const ctxRef = useRef(ctx);
  ctxRef.current = ctx;

  useEffect(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const ms = nextExpiryMs(overrides);
    if (ms == null) return;
    timerRef.current = window.setTimeout(() => {
      setOverrides((prev) => prev.filter((o) => isOverrideActive(o)));
    }, Math.max(50, ms + 20));
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [overrides]);

  const seedFromConfig = useCallback((active: ScreenOverride[] | undefined | null) => {
    const list = (active || []).filter((o) => isOverrideActive(o) && matchesTarget(o, ctxRef.current));
    setOverrides(list);
  }, []);

  const ingestOverride = useCallback((raw: ScreenOverride) => {
    if (!matchesTarget(raw, ctxRef.current)) return;
    if (!isOverrideActive(raw)) return;
    setOverrides((prev) => upsert(prev, raw).filter((o) => isOverrideActive(o)));
  }, []);

  const cancelOverride = useCallback((overrideId: string) => {
    setOverrides((prev) => prev.filter((o) => o.id !== overrideId));
  }, []);

  const handleWsEvent = useCallback(
    (event: string, data: Record<string, unknown>, eventId?: string) => {
      if (event === "screen.override.started" && data.override) {
        ingestOverride(data.override as ScreenOverride);
        return;
      }
      if (event === "screen.override.cancelled") {
        const id = (data.override_id as string) || (data.override as ScreenOverride | undefined)?.id;
        if (id) cancelOverride(id);
        return;
      }
      if (event === "ticket.called" || event === "ticket.recalled") {
        const embedded = data.override as ScreenOverride | undefined;
        if (embedded) {
          ingestOverride(embedded);
          return;
        }
        ingestOverride(
          legacyQueueCallFromEvent({
            ticket: data.ticket as string | undefined,
            ticket_id: data.ticket_id as string | undefined,
            ticket_type: data.ticket_type as string | undefined,
            department: data.department as string | undefined,
            queue_id: data.queue_id as string | undefined,
            event_id: eventId,
          }),
        );
      }
    },
    [cancelOverride, ingestOverride],
  );

  const current = useMemo(() => resolveCurrentOverride(overrides), [overrides]);

  const markSpoken = useCallback((overrideId: string) => {
    spokenRef.current.add(overrideId);
    if (spokenRef.current.size > 200) {
      const first = spokenRef.current.values().next().value;
      if (first) spokenRef.current.delete(first);
    }
  }, []);

  const wasSpoken = useCallback((overrideId: string) => spokenRef.current.has(overrideId), []);

  const remainingMs = current
    ? Math.max(0, parseOverrideTime(current.expires_at) - Date.now())
    : 0;

  return {
    current,
    overrides,
    remainingMs,
    seedFromConfig,
    handleWsEvent,
    markSpoken,
    wasSpoken,
  };
}
