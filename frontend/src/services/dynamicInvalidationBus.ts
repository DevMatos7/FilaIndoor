type Handler = (payload: { dynamic_content_id: string; reason?: string; version?: string }) => void;

const handlers = new Set<Handler>();
const dirtyIds = new Set<string>();

export function markDynamicDirty(contentId: string) {
  dirtyIds.add(contentId);
}

export function clearDynamicDirty(contentId: string) {
  dirtyIds.delete(contentId);
}

export function isDynamicDirty(contentId: string) {
  return dirtyIds.has(contentId);
}

export function subscribeDynamicInvalidation(handler: Handler): () => void {
  handlers.add(handler);
  return () => {
    handlers.delete(handler);
  };
}

export function publishDynamicInvalidation(payload: {
  dynamic_content_id: string;
  reason?: string;
  version?: string;
}) {
  if (payload.dynamic_content_id) {
    markDynamicDirty(payload.dynamic_content_id);
  }
  handlers.forEach((h) => h(payload));
}
