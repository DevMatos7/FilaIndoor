import { HTMLAttributes, ReactNode } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { cn } from "../utils/cn";

export type AlertVariant = "info" | "success" | "warning" | "danger";

export type AlertProps = HTMLAttributes<HTMLDivElement> & {
  variant?: AlertVariant;
  title?: string;
  icon?: ReactNode;
};

const styles: Record<AlertVariant, string> = {
  info: "border-semantic-info-border bg-semantic-info-bg text-semantic-info",
  success: "border-semantic-success-border bg-semantic-success-bg text-semantic-success",
  warning: "border-semantic-warning-border bg-semantic-warning-bg text-semantic-warning",
  danger: "border-semantic-danger-border bg-semantic-danger-bg text-semantic-danger",
};

const icons: Record<AlertVariant, ReactNode> = {
  info: <Info className="h-4 w-4 shrink-0" aria-hidden />,
  success: <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden />,
  warning: <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />,
  danger: <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />,
};

export function Alert({
  className,
  variant = "info",
  title,
  icon,
  children,
  role,
  ...props
}: AlertProps) {
  const computedRole = role ?? (variant === "danger" ? "alert" : "status");
  return (
    <div
      role={computedRole}
      className={cn("flex gap-3 rounded-ds border px-3 py-2.5 text-sm", styles[variant], className)}
      {...props}
    >
      <span className="mt-0.5">{icon ?? icons[variant]}</span>
      <div>
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={cn(title && "mt-0.5", "text-current/90")}>{children}</div>}
      </div>
    </div>
  );
}
