import { ButtonHTMLAttributes, forwardRef, ReactNode } from "react";
import { cn } from "../utils/cn";

export type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  icon: ReactNode;
  variant?: "ghost" | "secondary";
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { className, label, icon, variant = "ghost", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-ds transition-colors duration-ds",
        "disabled:pointer-events-none disabled:opacity-50",
        variant === "ghost" && "text-brand-700 hover:bg-brand-50",
        variant === "secondary" && "border border-brand-100 bg-surface text-brand-700 hover:bg-brand-50",
        className,
      )}
      {...props}
    >
      {icon}
    </button>
  );
});
