import { ReactNode } from "react";
import { cn } from "../utils/cn";

export type TabItem = {
  id: string;
  label: string;
  disabled?: boolean;
};

export type TabsProps = {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
  trailing?: ReactNode;
};

export function Tabs({ items, value, onChange, className, trailing }: TabsProps) {
  return (
    <div className={cn("flex flex-wrap items-center justify-between gap-3 border-b border-brand-100", className)}>
      <div role="tablist" className="flex flex-wrap gap-1">
        {items.map((item) => {
          const selected = item.id === value;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={selected}
              disabled={item.disabled}
              onClick={() => onChange(item.id)}
              className={cn(
                "-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors duration-ds",
                "disabled:cursor-not-allowed disabled:opacity-40",
                selected
                  ? "border-brand-700 text-brand-800"
                  : "border-transparent text-ink/60 hover:text-brand-700",
              )}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {trailing}
    </div>
  );
}
