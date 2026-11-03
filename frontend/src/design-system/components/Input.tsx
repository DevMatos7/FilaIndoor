import { InputHTMLAttributes, ReactNode, forwardRef, useId } from "react";
import { cn } from "../utils/cn";

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string;
  leading?: ReactNode;
};

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, label, hint, error, leading, id, required, disabled, ...props },
  ref,
) {
  const autoId = useId();
  const inputId = id || autoId;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-ink">
          {label}
          {required && (
            <span className="ml-0.5 text-semantic-danger" aria-hidden>
              *
            </span>
          )}
        </label>
      )}
      <div className={cn("relative", label && "mt-1")}>
        {leading && (
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-ink/45">
            {leading}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          required={required}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={[hintId, errorId].filter(Boolean).join(" ") || undefined}
          className={cn(
            "w-full rounded-ds border bg-surface-muted px-3 py-2 text-sm text-ink transition-colors duration-ds",
            "placeholder:text-ink/40 disabled:cursor-not-allowed disabled:opacity-60",
            "border-brand-100 focus:border-brand-500",
            error && "border-semantic-danger-border focus:border-semantic-danger",
            leading ? "pl-9" : undefined,
            className,
          )}
          {...props}
        />
      </div>
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
