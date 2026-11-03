import { SelectHTMLAttributes, forwardRef, useId } from "react";
import { cn } from "../utils/cn";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  hint?: string;
  error?: string;
};

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, label, hint, error, id, required, disabled, children, ...props },
  ref,
) {
  const autoId = useId();
  const selectId = id || autoId;
  const hintId = hint ? `${selectId}-hint` : undefined;
  const errorId = error ? `${selectId}-error` : undefined;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={selectId} className="block text-sm font-medium text-ink">
          {label}
          {required && (
            <span className="ml-0.5 text-semantic-danger" aria-hidden>
              *
            </span>
          )}
        </label>
      )}
      <select
        ref={ref}
        id={selectId}
        required={required}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={[hintId, errorId].filter(Boolean).join(" ") || undefined}
        className={cn(
          "mt-1 w-full rounded-ds border border-brand-100 bg-surface-muted px-3 py-2 text-sm text-ink",
          "disabled:cursor-not-allowed disabled:opacity-60",
          "focus:border-brand-500",
          error && "border-semantic-danger-border",
          label ? "" : "mt-0",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      {hint && !error && (
        <p id={hintId} className="mt-1 text-xs text-ink/55">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="mt-1 text-xs text-semantic-danger" role="alert">
          {error}
        </p>
      )}
    </div>
  );
});
