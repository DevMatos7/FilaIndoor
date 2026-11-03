import { CheckCircle2, AlertTriangle, OctagonAlert } from "lucide-react";
import { slaLevel } from "../tokens/colors";
import { Badge } from "../components/Badge";
import { cn } from "../utils/cn";

export type SlaCode = keyof typeof slaLevel;

const icons = {
  OK: CheckCircle2,
  WARNING: AlertTriangle,
  CRITICAL: OctagonAlert,
} as const;

export function SlaIndicator({ level, className }: { level: string; className?: string }) {
  const key = (level in slaLevel ? level : "OK") as SlaCode;
  const meta = slaLevel[key];
  const Icon = icons[key];

  return (
    <Badge
      className={cn(meta.bg, meta.fg, className)}
      icon={<Icon className="h-3.5 w-3.5" aria-hidden />}
    >
      SLA {meta.label}
    </Badge>
  );
}
