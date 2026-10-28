import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

const nav = [
  { to: "/", label: "Dashboard" },
  { to: "/analytics", label: "Analytics" },
  { to: "/queues", label: "Filas" },
  { to: "/history", label: "Histórico" },
  { to: "/media", label: "Mídias" },
  { to: "/playlists", label: "Playlists" },
  { to: "/channels", label: "Canais" },
  { to: "/devices", label: "Dispositivos" },
  { to: "/edge", label: "Edge" },
  { to: "/integrations", label: "CISS" },
  { to: "/toledo", label: "Toledo" },
  { to: "/real-plus", label: "REAL+" },
];

export default function AppLayout() {
  const navigate = useNavigate();

  function logout() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="border-b border-brand-100 bg-brand-900 text-white lg:border-b-0 lg:border-r lg:border-brand-700">
        <div className="px-5 py-6">
          <Link to="/" className="font-display text-2xl font-semibold tracking-tight">
            REAL Fila
          </Link>
          <p className="mt-1 text-sm text-brand-100/80">Atendimento & Indoor</p>
        </div>
        <nav className="flex gap-2 overflow-x-auto px-3 pb-4 lg:flex-col lg:overflow-visible">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium transition ${
                  isActive ? "bg-white/15 text-white" : "text-brand-100 hover:bg-white/10"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden px-5 pb-6 lg:block">
          <button
            type="button"
            onClick={logout}
            className="text-sm text-brand-100 underline-offset-2 hover:underline"
          >
            Sair
          </button>
        </div>
      </aside>
      <main className="px-4 py-6 sm:px-8">
        <Outlet />
      </main>
    </div>
  );
}
