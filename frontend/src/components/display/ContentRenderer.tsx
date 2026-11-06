import { MediaPlayer } from "./MediaPlayer";
import type { PlaylistItem } from "./types";
import { DynamicContentRenderer } from "../dynamic-content/DynamicContentRenderer";

type Props = {
  item: PlaylistItem | null;
  paused?: boolean;
  displayToken?: string;
  onMediaFailed?: (item: PlaylistItem) => void;
};

/**
 * Zone content sequence unit:
 * ContentRenderer → MediaPlayer | DynamicContentRenderer
 */
export function ContentRenderer({ item, paused = false, displayToken = "", onMediaFailed }: Props) {
  if (!item) {
    return <MediaPlayer item={null} onMediaFailed={onMediaFailed} />;
  }

  if (item.item_type === "DYNAMIC" || item.type === "DYNAMIC" || item.type === "PRICE_TABLE") {
    const contentId = item.dynamic_content?.id || item.id;
    return (
      <DynamicContentRenderer
        mode="player"
        contentId={contentId}
        token={displayToken}
        itemKey={item.item_id || item.id}
        paused={paused}
        onFailed={() => onMediaFailed?.(item)}
      />
    );
  }

  return <MediaPlayer item={item} paused={paused} onMediaFailed={onMediaFailed} />;
}
