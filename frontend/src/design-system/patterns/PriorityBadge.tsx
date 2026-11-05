import { AlertTriangle, Flame, CircleDot } from "lucide-react";
import { Badge, type BadgeTone } from "../components/Badge";

export type SchedulePriority = "NORMAL" | "HIGH" | "EMERGENCY" | string;

const META: Record<
  string,
  { label: string; tone: BadgeTone; icon: typeof CircleDot }
> = {
  NORMAL: { label: "Programação normal", tone: "neutral", icon: CircleDot },
  HIGH: { label: "Prioritária", tone: "warning", icon: AlertTriangle },
  EMERGENCY: { label: "Emergencial", tone: "danger", icon: Flame },
};

export function PriorityBadge({ priority }: { priority: SchedulePriority }) {
  const key = (priority || "NORMAL").toUpperCase();
  const meta = META[key] || META.NORMAL;
  const Icon = meta.icon;
  return (
    <Badge tone={meta.tone} icon={<Icon className="h-3 w-3" aria-hidden />}>
      {meta.label}
    </Badge>
  );
}

export function priorityLabel(priority: string) {
  return META[(priority || "NORMAL").toUpperCase()]?.label || priority;
}
