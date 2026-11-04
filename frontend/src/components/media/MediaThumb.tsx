import { useState } from "react";
import { Globe, Image as ImageIcon, Video } from "lucide-react";
import { cn } from "../../design-system";
import { hostOf } from "../../lib/signageFormat";

type Props = {
  mediaType: string;
  url?: string | null;
  name?: string;
  className?: string;
};

/** Compact visual shared by Media Library / Playlist timeline (no iframe/autoplay). */
export function MediaThumb({ mediaType, url, name, className }: Props) {
  const [failed, setFailed] = useState(false);
  const type = (mediaType || "").toUpperCase();

  if (type === "IMAGE" && url && !failed) {
    return (
      <img
        src={url}
        alt=""
        loading="lazy"
        className={cn("h-full w-full object-cover", className)}
        onError={() => setFailed(true)}
      />
    );
  }
  if (type === "VIDEO" && url && !failed) {
    return (
      <video
        src={url}
        preload="metadata"
        muted
        playsInline
        className={cn("h-full w-full object-cover", className)}
        onError={() => setFailed(true)}
      />
    );
  }
  return (
    <div
      className={cn(
        "flex h-full w-full flex-col items-center justify-center gap-1 bg-brand-50 px-1 text-center",
        className,
      )}
    >
      {type === "WEB" ? (
        <Globe className="h-5 w-5 text-brand-400" aria-hidden />
      ) : type === "VIDEO" ? (
        <Video className="h-5 w-5 text-brand-400" aria-hidden />
      ) : (
        <ImageIcon className="h-5 w-5 text-brand-400" aria-hidden />
      )}
      {type === "WEB" && url && (
        <span className="line-clamp-2 break-all text-[10px] text-ink/50">{hostOf(url)}</span>
      )}
      {name && type !== "WEB" && failed && (
        <span className="line-clamp-1 text-[10px] text-ink/45">{name}</span>
      )}
    </div>
  );
}
