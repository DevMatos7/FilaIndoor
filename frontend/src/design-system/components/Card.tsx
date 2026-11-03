import { HTMLAttributes, ReactNode } from "react";
import { cn } from "../utils/cn";

export type CardProps = HTMLAttributes<HTMLDivElement> & {
  interactive?: boolean;
};

export function Card({ className, interactive, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-ds border border-brand-100 bg-surface/90 shadow-ds",
        interactive && "transition-colors duration-ds hover:border-brand-400",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  title,
  description,
  action,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  title?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-3 px-4 pt-4", className)} {...props}>
      <div>
        {title && <h3 className="font-sans text-section-title text-brand-900">{title}</h3>}
        {description && <p className="mt-1 text-sm text-ink/70">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-4 py-4", className)} {...props} />;
}
