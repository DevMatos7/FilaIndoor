/** Formatador central pt-BR / BRL — não usar toFixed espalhado na UI. */

export function formatBrl(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(String(value).replace(",", "."));
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);
}

export function formatUnit(unit?: string | null): string {
  return (unit || "").trim().toLowerCase();
}
