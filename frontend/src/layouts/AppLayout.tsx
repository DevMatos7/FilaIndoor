import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { StoreProvider } from "../context/StoreContext";
import Breadcrumbs from "./Breadcrumbs";
import MobileNavigation from "./MobileNavigation";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

const SIDEBAR_KEY = "real-shell-sidebar";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_KEY) === "collapsed";
  } catch {
    return false;
  }
}

function Shell() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Tablet: inicia recolhida se ainda não houver preferência salva
  useEffect(() => {
    try {
      if (localStorage.getItem(SIDEBAR_KEY) != null) return;
      if (window.matchMedia("(min-width: 768px) and (max-width: 1023px)").matches) {
        setCollapsed(true);
      }
    } catch {
      /* ignore */
    }
  }, []);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_KEY, next ? "collapsed" : "expanded");
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  function logout() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  return (
    <div className="flex min-h-screen bg-surface-muted">
      <div className="sticky top-0 hidden h-screen shrink-0 lg:block">
        <Sidebar
          pathname={pathname}
          collapsed={collapsed}
          onToggleCollapsed={toggleCollapsed}
        />
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenMobileNav={() => setMobileOpen(true)} onLogout={logout} />
        <div className="border-b border-brand-100/80 bg-surface px-4 py-2 sm:px-6">
          <Breadcrumbs />
        </div>
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-[1400px]">
            <Outlet />
          </div>
        </main>
      </div>

      <MobileNavigation open={mobileOpen} onClose={() => setMobileOpen(false)} />
    </div>
  );
}

export default function AppLayout() {
  return (
    <StoreProvider>
      <Shell />
    </StoreProvider>
  );
}
