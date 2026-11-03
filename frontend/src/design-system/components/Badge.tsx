import { HTMLAttributes, ReactNode } from "react";
import { cn } from "../utils/cn";

export type BadgeTone = "neutral" | "brand" | "success" | "warning" | "danger" | "info";

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
  icon?: ReactNode;
};

const tones: Record<BadgeTone, string> = {
  neutral: "bg-status-offline-bg text-status-offline",
  brand: "bg-brand-50 text-brand-800",
  success: "bg-semantic-success-bg text-semantic-success",
  warning: "bg-semantic-warning-bg text-semantic-warning",
  danger: "bg-semantic-danger-bg text-semantic-danger",
  info: "bg-semantic-info-bg text-semantic-info",
};

export function Badge({ className, tone = "neutral", icon, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
      {...props}
    >
      {icon}
      {children}
    </span>
  );
}
