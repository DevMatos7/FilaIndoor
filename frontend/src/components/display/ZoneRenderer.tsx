import { CSSProperties, ReactNode } from "react";
import { ContentRenderer } from "./ContentRenderer";
import { QueueZone } from "./QueueZone";
import { TextZone } from "./TextZone";
import { ClockZone } from "./ClockZone";
import { TickerZone } from "./TickerZone";
import type { LayoutZone } from "./layoutTypes";
import type { DisplayTicket, PlaylistItem } from "./types";

type Props = {
  zone: LayoutZone;
  /** First MEDIA zone only receives the shared content sequence. */
  isPrimaryMedia?: boolean;
  mediaItem: PlaylistItem | null;
  onMediaFailed?: (item: PlaylistItem) => void;
  department: string;
  current: DisplayTicket | null;
  lastCalled: DisplayTicket[];
  paused?: boolean;
  displayToken?: string;
};

export function ZoneRenderer({
  zone,
  isPrimaryMedia,
  mediaItem,
  onMediaFailed,
  department,
  current,
  lastCalled,
  paused = false,
  displayToken = "",
}: Props) {
  const style: CSSProperties = {
    position: "absolute",
    left: `${zone.x}%`,
    top: `${zone.y}%`,
    width: `${zone.width}%`,
    height: `${zone.height}%`,
    zIndex: zone.z_index ?? 0,
    overflow: "hidden",
  };

  let content: ReactNode = null;
  switch (zone.type) {
    case "MEDIA":
      content = isPrimaryMedia ? (
        <div className="relative h-full w-full">
          <ContentRenderer
            item={mediaItem}
            paused={paused}
            displayToken={displayToken}
            onMediaFailed={onMediaFailed}
          />
        </div>
      ) : null;
      if (!isPrimaryMedia) {
        console.warn("[display] extra MEDIA zone ignored", zone.id);
      }
      break;
    case "QUEUE":
      content = (
        <QueueZone
          department={department}
          current={current}
          lastCalled={lastCalled}
          config={zone.config}
        />
      );
      break;
    case "TEXT":
      content = <TextZone config={zone.config} />;
      break;
    case "CLOCK":
      content = <ClockZone config={zone.config} />;
      break;
    case "TICKER":
      content = <TickerZone config={zone.config} />;
      break;
    default:
      console.warn("[display] unknown zone type", zone.type, zone.id);
      return null;
  }

  if (!content) return null;

  return (
    <div style={style} data-zone-type={zone.type} data-zone-id={zone.id}>
      {content}
    </div>
  );
}
