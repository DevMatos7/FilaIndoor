import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { findActiveNav } from "./navigation";
import api from "../services/api";

type Crumb = { label: string; to?: string };

export default function Breadcrumbs() {
  const { pathname } = useLocation();
  const { queueId } = useParams();
  const [queueName, setQueueName] = useState<string | null>(null);

  useEffect(() => {
    if (!queueId) {
      setQueueName(null);
      return;
    }
    let alive = true;
    (async () => {
      try {
        const { data } = await api.get<{ name: string }>(`/queues/${queueId}`);
        if (alive) setQueueName(data.name);
      } catch {
        if (alive) setQueueName(null);
      }
    })();
    return () => {
      alive = false;
    };
  }, [queueId]);

  const crumbs = buildCrumbs(pathname, queueId, queueName);

  if (crumbs.length <= 1 && pathname === "/") {
    return (
      <nav aria-label="Breadcrumb" className="text-xs text-ink/50">
        <ol className="flex flex-wrap items-center gap-1">
          <li className="font-medium text-ink/70">Início</li>
        </ol>
      </nav>
    );
  }

  return (
    <nav aria-label="Breadcrumb" className="text-xs text-ink/55">
      <ol className="flex flex-wrap items-center gap-1">
        {crumbs.map((c, i) => {
          const last = i === crumbs.length - 1;
          return (
            <li key={`${c.label}-${i}`} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-3 w-3 shrink-0 text-ink/35" aria-hidden />}
              {last || !c.to ? (
                <span className="font-medium text-ink/80" aria-current={last ? "page" : undefined}>
                  {c.label}
                </span>
              ) : (
                <Link to={c.to} className="hover:text-brand-700 hover:underline">
                  {c.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function buildCrumbs(pathname: string, queueId?: string, queueName?: string | null): Crumb[] {
  const crumbs: Crumb[] = [{ label: "Início", to: "/" }];
  const { group, item } = findActiveNav(pathname);

  if (pathname === "/") return crumbs;

  if (group) crumbs.push({ label: group.label });

  if (queueId) {
    crumbs.push({ label: "Filas", to: "/queues" });
    const detailLabel = queueName || "Detalhe da fila";
    if (pathname.endsWith("/settings")) {
      crumbs.push({ label: detailLabel, to: `/queues/${queueId}` });
      crumbs.push({ label: "Configurações" });
    } else {
      crumbs.push({ label: detailLabel });
    }
    return crumbs;
  }

  if (item) {
    crumbs.push({ label: item.label, to: item.to });
  }

  return crumbs;
}
