import { Link } from "react-router-dom";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { IconButton, Tooltip, cn } from "../design-system";
import { NAV_GROUPS, isNavItemActive, type NavItem } from "./navigation";

type SidebarProps = {
  pathname: string;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onNavigate?: () => void;
  className?: string;
};

function NavLinkItem({
  item,
  active,
  collapsed,
  onNavigate,
}: {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;
  const link = (
    <Link
      to={item.to}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex items-center gap-3 rounded-ds px-3 py-2 text-sm font-medium transition-colors duration-ds",
        collapsed && "justify-center px-2",
        active
          ? "bg-white/15 text-white"
          : "text-brand-100/85 hover:bg-white/10 hover:text-white",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      {!collapsed && <span>{item.label}</span>}
      {collapsed && <span className="sr-only">{item.label}</span>}
    </Link>
  );

  if (collapsed) {
    return (
      <Tooltip content={item.label}>
        {link}
      </Tooltip>
    );
  }
  return link;
}

export default function Sidebar({
  pathname,
  collapsed,
  onToggleCollapsed,
  onNavigate,
  className,
}: SidebarProps) {
  return (
    <aside
      className={cn(
        "flex h-full flex-col bg-brand-900 text-white",
        collapsed ? "w-[72px]" : "w-[272px]",
        className,
      )}
    >
      <div className={cn("flex items-start gap-2 border-b border-white/10 px-4 py-5", collapsed && "justify-center px-2")}>
        <Link to="/" onClick={onNavigate} className={cn("min-w-0", collapsed && "sr-only")}>
          <p className="font-display text-2xl font-semibold tracking-tight">REAL</p>
          <p className="mt-0.5 text-xs text-brand-100/75">Fila & Indoor</p>
        </Link>
        {collapsed && (
          <Link to="/" onClick={onNavigate} aria-label="REAL Fila & Indoor" className="font-display text-lg font-semibold">
            R
          </Link>
        )}
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-2 py-4" aria-label="Navegação principal">
        {NAV_GROUPS.map((group) => (
          <div key={group.id}>
            {!collapsed && (
              <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-brand-200/70">
                {group.label}
              </p>
            )}
            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <li key={item.id}>
                  <NavLinkItem
                    item={item}
                    active={isNavItemActive(pathname, item)}
                    collapsed={collapsed}
                    onNavigate={onNavigate}
                  />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className={cn("border-t border-white/10 p-2", collapsed ? "flex justify-center" : "")}>
        <IconButton
          label={collapsed ? "Expandir menu" : "Recolher menu"}
          icon={collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          onClick={onToggleCollapsed}
          className="text-brand-100 hover:bg-white/10 hover:text-white"
        />
      </div>
    </aside>
  );
}
