import { Link, useLocation } from "react-router-dom";
import { Drawer, cn } from "../design-system";
import { NAV_GROUPS, isNavItemActive } from "./navigation";

type MobileNavigationProps = {
  open: boolean;
  onClose: () => void;
};

export default function MobileNavigation({ open, onClose }: MobileNavigationProps) {
  const { pathname } = useLocation();

  return (
    <Drawer open={open} onClose={onClose} title="Menu" side="left" className="max-w-[300px]">
      <div className="mb-4">
        <p className="font-display text-xl font-semibold text-brand-900">REAL</p>
        <p className="text-xs text-ink/55">Fila & Indoor</p>
      </div>
      <nav aria-label="Navegação mobile" className="space-y-5">
        {NAV_GROUPS.map((group) => (
          <div key={group.id}>
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-ink/45">
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = isNavItemActive(pathname, item);
                return (
                  <li key={item.id}>
                    <Link
                      to={item.to}
                      onClick={onClose}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex items-center gap-3 rounded-ds px-3 py-2.5 text-sm font-medium",
                        active
                          ? "bg-brand-50 text-brand-800"
                          : "text-ink/80 hover:bg-brand-50/70",
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" aria-hidden />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </Drawer>
  );
}
