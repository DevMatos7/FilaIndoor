import { Circle, PauseCircle, StopCircle } from "lucide-react";
import { queueStatus } from "../tokens/colors";
import { Badge } from "../components/Badge";
import { cn } from "../utils/cn";

export type QueueStatusCode = keyof typeof queueStatus;

const icons = {
  OPEN: Circle,
  PAUSED: PauseCircle,
  CLOSED: StopCircle,
} as const;

export function QueueStatus({ status, className }: { status: string; className?: string }) {
  const key = (status in queueStatus ? status : "CLOSED") as QueueStatusCode;
  const meta = queueStatus[key];
  const Icon = icons[key];

  return (
    <Badge
      className={cn(meta.bg, meta.fg, className)}
      icon={<Icon className="h-3.5 w-3.5" aria-hidden />}
    >
      {meta.label}
    </Badge>
  );
}
