import { KeyboardEvent, ReactNode, useState } from "react";
import { Globe, Image as ImageIcon, Video } from "lucide-react";
import { cn } from "../utils/cn";
import { Badge } from "../components/Badge";
import { Skeleton } from "../components/Skeleton";

export type MediaCardType = "IMAGE" | "VIDEO" | "WEB" | string;

export type MediaCardProps = {
  name: string;
  mediaType: MediaCardType;
  previewUrl?: string | null;
  durationSeconds?: number | null;
  width?: number | null;
  height?: number | null;
  createdAtLabel?: string | null;
  highlighted?: boolean;
  /** Picker selection state (keyboard + aria). */
  selected?: boolean;
  onOpen?: () => void;
  menu?: ReactNode;
  className?: string;
};

function typeLabel(t: string) {
  if (t === "IMAGE") return "Imagem";
  if (t === "VIDEO") return "Vídeo";
  if (t === "WEB") return "Web";
  return t;
}

function fmtDuration(sec?: number | null) {
  if (sec == null) return null;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function TypeIcon({ type }: { type: string }) {
  if (type === "VIDEO") return <Video className="h-10 w-10 text-brand-400" aria-hidden />;
  if (type === "WEB") return <Globe className="h-10 w-10 text-brand-400" aria-hidden />;
  return <ImageIcon className="h-10 w-10 text-brand-400" aria-hidden />;
}

export function MediaCard({
  name,
  mediaType,
  previewUrl,
  durationSeconds,
  width,
  height,
  createdAtLabel,
  highlighted,
  selected,
  onOpen,
  menu,
  className,
}: MediaCardProps) {
  const [imgFailed, setImgFailed] = useState(false);
  const type = (mediaType || "").toUpperCase();
  const duration = type === "VIDEO" ? fmtDuration(durationSeconds) : null;
  const dims = width && height ? `${width} × ${height}` : null;
  const isSelected = !!selected;

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (!onOpen) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onOpen();
    }
  }

  return (
    <div
      role={onOpen ? "button" : undefined}
      tabIndex={onOpen ? 0 : undefined}
      aria-pressed={onOpen ? isSelected : undefined}
      onClick={onOpen}
      onKeyDown={onKeyDown}
      className={cn(
        "group flex flex-col overflow-hidden rounded-ds border border-brand-100 bg-surface text-left transition",
        "hover:border-brand-300 hover:shadow-ds focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600",
        (highlighted || isSelected) && "ring-2 ring-brand-500 ring-offset-2",
        isSelected && "border-brand-600",
        onOpen && "cursor-pointer",
        className,
      )}
    >
      <div className="relative aspect-video bg-brand-50">
        {type === "IMAGE" && previewUrl && !imgFailed ? (
          <img
            src={previewUrl}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : type === "VIDEO" && previewUrl && !imgFailed ? (
          <video
            src={previewUrl}
            preload="metadata"
            muted
            playsInline
            className="h-full w-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 px-3">
            <TypeIcon type={type} />
            {type === "WEB" && previewUrl && (
              <p className="line-clamp-2 break-all text-center text-xs text-ink/55">
                {safeHost(previewUrl)}
              </p>
            )}
          </div>
        )}
        <div className="absolute left-2 top-2">
          <Badge tone={type === "VIDEO" ? "info" : type === "WEB" ? "brand" : "neutral"}>
            {typeLabel(type)}
          </Badge>
        </div>
        {menu && (
          <div
            className="absolute right-1 top-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
          >
            {menu}
          </div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-3">
        <p className="line-clamp-2 font-sans text-sm font-semibold text-brand-900">{name}</p>
        <p className="text-xs text-ink/60">
          {[duration, dims, createdAtLabel].filter(Boolean).join(" · ") || typeLabel(type)}
        </p>
      </div>
    </div>
  );
}

function safeHost(url: string) {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

export function MediaCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-ds border border-brand-100 bg-surface",
        className,
      )}
      aria-hidden
    >
      <Skeleton.Line className="aspect-video h-auto w-full rounded-none" />
      <div className="space-y-2 p-3">
        <Skeleton.Text className="h-4 w-3/4" />
        <Skeleton.Text className="h-3 w-1/2" />
      </div>
    </div>
  );
}
