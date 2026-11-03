import { ReactNode } from "react";
import { Inbox } from "lucide-react";
import { cn } from "../utils/cn";

export type EmptyStateProps = {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
};

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-ds border border-dashed border-brand-300/60 bg-surface/60 px-6 py-10 text-center",
        className,
      )}
    >
      <div className="mb-3 text-brand-600">
        {icon ?? <Inbox className="h-8 w-8" aria-hidden />}
      </div>
      <p className="font-sans text-base font-semibold text-brand-900">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-ink/70">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
