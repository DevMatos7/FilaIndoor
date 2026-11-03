import { useEffect, useRef, useState } from "react";
import { LogOut, MoreVertical, RefreshCw } from "lucide-react";

type Props = {
  department: string;
  terminalName?: string | null;
  derivedState: "PRONTO" | "ATENDENDO" | "ENCERRADO" | "PAUSADO";
  onSwitchTerminal: () => void;
  onLogout: () => void;
};

export function OperatorHeader({
  department,
  terminalName,
  derivedState,
  onSwitchTerminal,
  onLogout,
}: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const stateLabel =
    derivedState === "ATENDENDO"
      ? "Atendendo"
      : derivedState === "ENCERRADO"
        ? "Encerrado"
        : derivedState === "PAUSADO"
          ? "Pausado"
          : "Pronto";

  return (
    <header className="safe-op-x flex items-start justify-between gap-3 border-b border-white/10 px-4 py-3 sm:px-5">
      <div className="min-w-0">
        <p className="text-sm font-bold tracking-tight text-white/90">REAL</p>
        <h1 className="truncate text-xl font-semibold sm:text-2xl">{department}</h1>
        {terminalName && <p className="truncate text-sm text-white/60">{terminalName}</p>}
      </div>

      <div className="flex items-center gap-2">
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${
            derivedState === "ATENDENDO"
              ? "bg-brand-500/25 text-brand-100"
              : derivedState === "ENCERRADO" || derivedState === "PAUSADO"
                ? "bg-semantic-warning-bg text-semantic-warning"
                : "bg-white/10 text-white/80"
          }`}
        >
          {stateLabel}
        </span>

        <div className="relative" ref={ref}>
          <button
            type="button"
            aria-label="Menu do operador"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-white/15 text-white/80 hover:bg-white/10"
          >
            <MoreVertical className="h-5 w-5" aria-hidden />
          </button>
          {open && (
            <div
              role="menu"
              className="absolute right-0 z-20 mt-2 w-48 overflow-hidden rounded-xl border border-white/15 bg-[#15241c] py-1 shadow-lg"
            >
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-3 text-left text-sm hover:bg-white/10"
                onClick={() => {
                  setOpen(false);
                  onSwitchTerminal();
                }}
              >
                <RefreshCw className="h-4 w-4" aria-hidden /> Trocar balcão
              </button>
              <button
                type="button"
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-3 text-left text-sm text-white/80 hover:bg-white/10"
                onClick={() => {
                  setOpen(false);
                  onLogout();
                }}
              >
                <LogOut className="h-4 w-4" aria-hidden /> Sair
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
