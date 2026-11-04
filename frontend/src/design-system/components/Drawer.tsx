import { ReactNode, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "../utils/cn";
import { useFocusTrap } from "../hooks/useFocusTrap";
import { IconButton } from "./IconButton";

export type DrawerProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  side?: "right" | "left";
  footer?: ReactNode;
  className?: string;
};

export function Drawer({
  open,
  onClose,
  title,
  children,
  side = "right",
  footer,
  className,
}: DrawerProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, panelRef, onClose);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50" role="presentation">
      <button
        type="button"
        className="absolute inset-0 bg-brand-950/50"
        aria-label="Fechar"
        tabIndex={-1}
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          "absolute top-0 flex h-full w-full max-w-md flex-col bg-surface shadow-ds-lg",
          "max-sm:max-w-none",
          side === "right" ? "right-0" : "left-0",
          className,
        )}
      >
        <div className="flex items-center justify-between gap-3 border-b border-brand-100 px-4 py-3">
          <h2 id={titleId} className="font-sans text-lg font-semibold text-brand-900">
            {title}
          </h2>
          <IconButton label="Fechar" icon={<X className="h-4 w-4" />} onClick={onClose} />
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-4 text-sm text-ink">{children}</div>
        {footer && <div className="border-t border-brand-100 px-4 py-3">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}
