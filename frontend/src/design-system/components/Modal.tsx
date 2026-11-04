import { ReactNode, RefObject, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "../utils/cn";
import { useFocusTrap } from "../hooks/useFocusTrap";
import { IconButton } from "./IconButton";

export type ModalProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
  /** Prefer this element on open (e.g. Cancel on destructive confirm). */
  initialFocusRef?: RefObject<HTMLElement | null>;
};

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  className,
  initialFocusRef,
}: ModalProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, panelRef, onClose, { initialFocusRef });

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="presentation">
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
          "relative z-10 w-full max-w-lg rounded-ds-lg border border-brand-100 bg-surface shadow-ds-lg",
          className,
        )}
      >
        <div className="flex items-center justify-between gap-3 border-b border-brand-100 px-4 py-3">
          <h2 id={titleId} className="font-sans text-lg font-semibold text-brand-900">
            {title}
          </h2>
          <IconButton label="Fechar" icon={<X className="h-4 w-4" />} onClick={onClose} />
        </div>
        <div className="px-4 py-4 text-sm text-ink">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2 border-t border-brand-100 px-4 py-3">{footer}</div>
        )}
      </div>
    </div>,
    document.body,
  );
}
