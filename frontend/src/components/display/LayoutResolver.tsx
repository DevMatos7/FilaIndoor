import { CSSProperties, useMemo } from "react";
import { ZoneRenderer } from "./ZoneRenderer";
import { EMERGENCY_LAYOUT, isValidLayout, type ResolvedLayout } from "./layoutTypes";
import type { DisplayTicket, PlaylistItem } from "./types";

type Props = {
  layout?: ResolvedLayout | null;
  mediaItem: PlaylistItem | null;
  onMediaFailed?: (item: PlaylistItem) => void;
  department: string;
  current: DisplayTicket | null;
  lastCalled: DisplayTicket[];
};

/**
 * Renders data-driven layout zones. Invalid/missing layout → UX-6A emergency footer layout.
 * Overrides are intentionally NOT owned here — OverrideRenderer is a sibling layer.
 */
export function LayoutResolver({
  layout,
  mediaItem,
  onMediaFailed,
  department,
  current,
  lastCalled,
}: Props) {
  const resolved = useMemo(() => {
    if (isValidLayout(layout)) return layout;
    console.warn("[display] invalid/missing layout — using emergency media_queue_footer");
    return EMERGENCY_LAYOUT;
  }, [layout]);

  const primaryMediaId = useMemo(() => {
    const mediaZones = resolved.zones.filter((z) => z.type === "MEDIA");
    return mediaZones[0]?.id ?? null;
  }, [resolved.zones]);

  const bg =
    resolved.background?.type === "color" && resolved.background.value
      ? resolved.background.value
      : "#071a12";

  const containerStyle: CSSProperties = {
    position: "relative",
    width: "100%",
    height: "100%",
    overflow: "hidden",
    background: bg,
  };

  return (
    <div className="layout-resolver h-full w-full" style={containerStyle} data-layout-slug={resolved.slug}>
      {resolved.zones.map((zone) => (
        <ZoneRenderer
          key={zone.id}
          zone={zone}
          isPrimaryMedia={zone.type === "MEDIA" && zone.id === primaryMediaId}
          mediaItem={mediaItem}
          onMediaFailed={onMediaFailed}
          department={department}
          current={current}
          lastCalled={lastCalled}
        />
      ))}
    </div>
  );
}
