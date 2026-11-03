import { ReactNode, useId, useState } from "react";
import { cn } from "../utils/cn";

export type TooltipProps = {
  content: ReactNode;
  children: ReactNode;
  className?: string;
};

/** Tooltip leve (hover/focus). Débito: posicionamento avançado / portal em UX futura. */
export function Tooltip({ content, children, className }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span
      className={cn("relative inline-flex", className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span aria-describedby={open ? id : undefined}>{children}</span>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute bottom-full left-1/2 z-40 mb-2 -translate-x-1/2 whitespace-nowrap rounded-ds bg-brand-900 px-2 py-1 text-xs text-white shadow-ds"
        >
          {content}
        </span>
      )}
    </span>
  );
}
