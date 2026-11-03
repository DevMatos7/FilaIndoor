import { ReactNode } from "react";
import { cn } from "../utils/cn";
import { Card, CardContent } from "./Card";

export type MetricCardProps = {
  label: string;
  value: ReactNode;
  hint?: string;
  trend?: ReactNode;
  status?: "default" | "success" | "warning" | "danger";
  icon?: ReactNode;
  className?: string;
};

const statusBar: Record<NonNullable<MetricCardProps["status"]>, string> = {
  default: "",
  success: "border-l-4 border-l-semantic-success",
  warning: "border-l-4 border-l-semantic-warning",
  danger: "border-l-4 border-l-semantic-danger",
};

export function MetricCard({
  label,
  value,
  hint,
  trend,
  status = "default",
  icon,
  className,
}: MetricCardProps) {
  return (
    <Card className={cn(statusBar[status], className)}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs uppercase tracking-wide text-ink/55">{label}</p>
          {icon && <span className="text-brand-600">{icon}</span>}
        </div>
        <p className="mt-2 font-sans text-metric tabular-nums text-brand-900">{value}</p>
        {(hint || trend) && (
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink/50">
            {hint && <span>{hint}</span>}
            {trend}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
