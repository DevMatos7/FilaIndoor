import { cn } from "../utils/cn";

export type StatusDotTone = "online" | "degraded" | "offline" | "disabled" | "neutral";

export type StatusDotProps = {
  tone?: StatusDotTone;
  label: string;
  className?: string;
  showLabel?: boolean;
};

const tones: Record<StatusDotTone, string> = {
  online: "bg-status-online",
  degraded: "bg-status-degraded",
  offline: "bg-status-offline",
  disabled: "bg-status-disabled",
  neutral: "bg-brand-300",
};

export function StatusDot({ tone = "neutral", label, className, showLabel = true }: StatusDotProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm text-ink", className)}>
      <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", tones[tone])} aria-hidden />
      {showLabel ? <span>{label}</span> : <span className="sr-only">{label}</span>}
    </span>
  );
}
