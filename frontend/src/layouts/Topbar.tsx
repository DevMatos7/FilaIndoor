import { useEffect, useRef, useState } from "react";
import { Bell, LogOut, Menu, User } from "lucide-react";
import { IconButton, Tooltip } from "../design-system";
import api from "../services/api";
import StoreSwitcher from "./StoreSwitcher";

type Me = {
  email: string;
  full_name: string;
  role: string;
};

type TopbarProps = {
  onOpenMobileNav: () => void;
  onLogout: () => void;
};

export default function Topbar({ onOpenMobileNav, onLogout }: TopbarProps) {
  const [me, setMe] = useState<Me | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { data } = await api.get<Me>("/auth/me");
        if (alive) setMe(data);
      } catch {
        if (alive) setMe(null);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const displayName = me?.full_name || "Administrador";
  const initial = displayName.trim().charAt(0).toUpperCase() || "A";

  return (
    <header className="flex h-14 items-center justify-between gap-3 border-b border-brand-100 bg-surface px-3 sm:px-5">
      <div className="flex items-center gap-2">
        <IconButton
          label="Abrir menu"
          icon={<Menu className="h-5 w-5" />}
          onClick={onOpenMobileNav}
          className="lg:hidden"
        />
        <div className="hidden sm:block">
          <StoreSwitcher />
        </div>
      </div>

      <div className="flex items-center gap-1 sm:gap-2">
        <div className="sm:hidden">
          <StoreSwitcher />
        </div>

        <Tooltip content="Alertas operacionais serão disponibilizados em breve">
          <span>
            <IconButton
              label="Alertas"
              icon={<Bell className="h-4 w-4" />}
              disabled
              className="text-ink/40"
            />
          </span>
        </Tooltip>

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-ds px-2 py-1.5 text-sm hover:bg-brand-50"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-700 text-xs font-semibold text-white">
              {initial}
            </span>
            <span className="hidden max-w-[10rem] truncate text-left md:block">
              <span className="block font-medium text-brand-900">{displayName}</span>
              <span className="block text-[11px] text-ink/50">{me?.email || "Conta"}</span>
            </span>
          </button>
          {menuOpen && (
            <div
              role="menu"
              className="absolute right-0 z-40 mt-1 w-52 rounded-ds border border-brand-100 bg-surface py-1 shadow-ds-md"
            >
              <div className="border-b border-brand-50 px-3 py-2 text-xs text-ink/55 md:hidden">
                {me?.email || "Administrador"}
              </div>
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-ink/70"
                disabled
              >
                <User className="h-4 w-4" aria-hidden />
                Conta
              </button>
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-semantic-danger hover:bg-semantic-danger-bg"
                onClick={onLogout}
              >
                <LogOut className="h-4 w-4" aria-hidden />
                Sair
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
