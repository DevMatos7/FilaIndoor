import { Wifi, WifiOff, AlertTriangle, Ban } from "lucide-react";
import { deviceStatus } from "../tokens/colors";
import { Badge } from "../components/Badge";
import { StatusDot } from "../components/StatusDot";
import { cn } from "../utils/cn";

export type DeviceStatusCode = keyof typeof deviceStatus;

const icons = {
  ONLINE: Wifi,
  DEGRADED: AlertTriangle,
  OFFLINE: WifiOff,
  DISABLED: Ban,
} as const;

const tones = {
  ONLINE: "online",
  DEGRADED: "degraded",
  OFFLINE: "offline",
  DISABLED: "disabled",
} as const;

export function DeviceStatus({
  status,
  className,
  variant = "badge",
}: {
  status: string;
  className?: string;
  variant?: "badge" | "dot";
}) {
  const key = (status in deviceStatus ? status : "OFFLINE") as DeviceStatusCode;
  const meta = deviceStatus[key];
  const Icon = icons[key];

  if (variant === "dot") {
    return <StatusDot tone={tones[key]} label={meta.label} className={className} />;
  }

  return (
    <Badge
      className={cn(meta.bg, meta.fg, className)}
      icon={<Icon className="h-3.5 w-3.5" aria-hidden />}
    >
      {meta.label}
    </Badge>
  );
}
