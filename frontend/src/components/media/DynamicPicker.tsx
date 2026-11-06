import { useEffect, useMemo, useState } from "react";
import { Table2 } from "lucide-react";
import { Alert, Button, Modal, Skeleton } from "../../design-system";
import api from "../../services/api";
import { formatClockDuration } from "../../lib/signageFormat";

export type DynamicContentOption = {
  id: string;
  name: string;
  template_name?: string | null;
  template_slug?: string | null;
  item_count?: number | null;
  page_count?: number | null;
  total_duration_seconds?: number | null;
  status?: string | null;
  freshness?: string | null;
};

type Props = {
  open: boolean;
  onClose: () => void;
  storeId: string;
  onConfirm: (ids: string[]) => Promise<void> | void;
  busy?: boolean;
};

function selectable(row: DynamicContentOption): boolean {
  const status = (row.status || "").toUpperCase();
  const freshness = (row.freshness || "").toUpperCase();
  if (status === "INATIVA" || status === "DADOS DESATUALIZADOS") return false;
  if (freshness === "STALE" || freshness === "FAILED") return false;
  if (status === "ATENÇÃO") {
    // DEGRADED may still be selectable per Module 2 policy
    return freshness === "DEGRADED" || freshness === "FRESH" || !freshness;
  }
  return status === "PRONTA" || !status;
}

export function DynamicPicker({ open, onClose, storeId, onConfirm, busy }: Props) {
  const [rows, setRows] = useState<DynamicContentOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!open || !storeId) return;
    let alive = true;
    setLoading(true);
    setError(null);
    setSelected(new Set());
    api
      .get<DynamicContentOption[]>("/dynamic-content", { params: { store_id: storeId } })
      .then((res) => {
        if (!alive) return;
        setRows(res.data || []);
      })
      .catch(() => {
        if (!alive) return;
        setError("Não foi possível carregar tabelas dinâmicas.");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [open, storeId]);

  const selectableRows = useMemo(() => rows.filter(selectable), [rows]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Adicionar conteúdo dinâmico"
      footer={
        <>
          <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>
            Cancelar
          </Button>
          <Button
            type="button"
            disabled={busy || selected.size === 0}
            onClick={() => void onConfirm([...selected])}
          >
            Adicionar {selected.size > 0 ? `(${selected.size})` : ""}
          </Button>
        </>
      }
    >
      <p className="mb-3 text-sm text-ink/65">Tabelas PRICE_TABLE prontas para a playlist desta loja.</p>
      {error && <Alert variant="danger">{error}</Alert>}
      {loading && <Skeleton.Card />}
      {!loading && selectableRows.length === 0 && (
        <p className="text-sm text-ink/60">Nenhuma tabela selecionável (PRONTA / ATENÇÃO autorizada).</p>
      )}
      <ul className="mt-2 max-h-[50vh] space-y-2 overflow-y-auto" role="listbox" aria-label="Tabelas dinâmicas">
        {rows.map((row) => {
          const ok = selectable(row);
          const checked = selected.has(row.id);
          return (
            <li key={row.id}>
              <button
                type="button"
                role="option"
                aria-selected={checked}
                disabled={!ok || busy}
                onClick={() => ok && toggle(row.id)}
                className={`flex w-full items-start gap-3 rounded-ds border px-3 py-3 text-left transition ${
                  checked ? "border-brand-400 bg-brand-50" : "border-brand-100 hover:bg-brand-50/60"
                } ${!ok ? "cursor-not-allowed opacity-45" : ""}`}
              >
                <Table2 className="mt-0.5 h-5 w-5 shrink-0 text-brand-700" aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold text-brand-900">{row.name}</span>
                  <span className="mt-0.5 block text-xs text-ink/55">
                    PRICE TABLE · {row.template_name || row.template_slug || "template"}
                    {row.item_count != null ? ` · ${row.item_count} produtos` : ""}
                    {row.page_count != null ? ` · ${row.page_count} pág.` : ""}
                    {row.total_duration_seconds != null
                      ? ` · ${formatClockDuration(row.total_duration_seconds)}`
                      : ""}
                    {row.status ? ` · ${row.status}` : ""}
                    {!ok ? " · indisponível" : ""}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </Modal>
  );
}
