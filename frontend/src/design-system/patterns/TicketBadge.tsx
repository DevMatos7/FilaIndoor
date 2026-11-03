import { Ticket, Star, Sparkles } from "lucide-react";
import { ticketType } from "../tokens/colors";
import { Badge } from "../components/Badge";
import { cn } from "../utils/cn";

export type TicketTypeCode = keyof typeof ticketType;

const icons = {
  NORMAL: Ticket,
  PRIORITY: Star,
  PRIORITY_PLUS: Sparkles,
} as const;

export function TicketBadge({ type, className }: { type: string; className?: string }) {
  const key = (type in ticketType ? type : "NORMAL") as TicketTypeCode;
  const meta = ticketType[key];
  const Icon = icons[key];

  return (
    <Badge className={cn(meta.className, className)} icon={<Icon className="h-3.5 w-3.5" aria-hidden />}>
      {meta.label}
    </Badge>
  );
}
