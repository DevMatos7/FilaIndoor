import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  ListOrdered,
  History,
  Image,
  Clapperboard,
  CalendarRange,
  MonitorSmartphone,
  Network,
  BarChart3,
  Database,
  Scale,
  Smartphone,
  Settings2,
  Tags,
} from "lucide-react";

export type NavItem = {
  id: string;
  label: string;
  to: string;
  icon: LucideIcon;
  /** Match ativo também para rotas filhas (prefix). */
  match?: "exact" | "prefix" | "queue-settings";
};

export type NavGroup = {
  id: string;
  label: string;
  items: NavItem[];
};

/**
 * IA visual — URLs existentes preservadas.
 * Início (/) = Command Center operacional (UX-3).
 * Itens futuros sem página própria (Indoor overview, Telas, Ao vivo dedicado)
 * ficam fora até as sprints correspondentes.
 */
export const NAV_GROUPS: NavGroup[] = [
  {
    id: "overview",
    label: "Visão geral",
    items: [{ id: "home", label: "Início", to: "/", icon: LayoutDashboard, match: "exact" }],
  },
  {
    id: "service",
    label: "Atendimento",
    items: [
      { id: "queues", label: "Filas", to: "/queues", icon: ListOrdered, match: "prefix" },
      { id: "history", label: "Histórico", to: "/history", icon: History, match: "exact" },
    ],
  },
  {
    id: "indoor",
    label: "Indoor",
    items: [
      { id: "media", label: "Conteúdos", to: "/media", icon: Image, match: "exact" },
      { id: "retail", label: "Produtos & preços", to: "/retail-content", icon: Tags, match: "prefix" },
      { id: "playlists", label: "Playlists", to: "/playlists", icon: Clapperboard, match: "exact" },
      { id: "channels", label: "Programação", to: "/channels", icon: CalendarRange, match: "exact" },
    ],
  },
  {
    id: "devices",
    label: "Dispositivos",
    items: [
      { id: "fleet", label: "Telas & dispositivos", to: "/devices", icon: MonitorSmartphone, match: "exact" },
      { id: "edge", label: "Edge", to: "/edge", icon: Network, match: "exact" },
    ],
  },
  {
    id: "intel",
    label: "Inteligência",
    items: [{ id: "analytics", label: "Analytics", to: "/analytics", icon: BarChart3, match: "exact" }],
  },
  {
    id: "integrations",
    label: "Integrações",
    items: [
      { id: "ciss", label: "CISS", to: "/integrations", icon: Database, match: "exact" },
      { id: "toledo", label: "Toledo", to: "/toledo", icon: Scale, match: "exact" },
      { id: "real-plus", label: "REAL+", to: "/real-plus", icon: Smartphone, match: "exact" },
    ],
  },
  {
    id: "settings",
    label: "Configurações",
    items: [
      {
        id: "queue-settings",
        label: "Config. de filas",
        to: "/queues",
        icon: Settings2,
        match: "queue-settings",
      },
    ],
  },
];

export function isNavItemActive(pathname: string, item: NavItem): boolean {
  if (item.match === "queue-settings") {
    return /\/queues\/[^/]+\/settings\/?$/.test(pathname);
  }
  if (item.match === "exact" || item.to === "/") {
    return pathname === item.to;
  }
  // Prefixo /queues não inclui /settings (reservado ao item Config.)
  if (item.to === "/queues" && /\/queues\/[^/]+\/settings/.test(pathname)) {
    return false;
  }
  return pathname === item.to || pathname.startsWith(`${item.to}/`);
}

export function findActiveNav(pathname: string): { group?: NavGroup; item?: NavItem } {
  let best: { group: NavGroup; item: NavItem; score: number } | null = null;
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      if (!isNavItemActive(pathname, item)) continue;
      const score =
        item.match === "queue-settings"
          ? 2000
          : item.match === "exact" || item.to === "/"
            ? 1000
            : item.to.length;
      if (!best || score > best.score) best = { group, item, score };
    }
  }
  return best ? { group: best.group, item: best.item } : {};
}
