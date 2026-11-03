import { terminalLabel, type Terminal } from "./types";

type Props = {
  terminals: Terminal[];
  departmentName?: string;
  onSelect: (id: string) => void;
  onLogout?: () => void;
};

export function TerminalSelector({ terminals, departmentName, onSelect, onLogout }: Props) {
  const many = terminals.length > 8;

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[#0f1a15] px-4 py-8 font-sans text-white">
      <div className="mx-auto w-full max-w-lg flex-1">
        <p className="text-center text-2xl font-bold">REAL</p>
        {departmentName && (
          <p className="mt-2 text-center text-sm uppercase tracking-[0.16em] text-brand-200">{departmentName}</p>
        )}
        <h1 className="mt-6 text-center text-2xl font-semibold">Onde você está atendendo?</h1>
        <p className="mt-2 text-center text-sm text-white/60">Escolha o balcão deste turno</p>

        {terminals.length === 0 ? (
          <p className="mt-10 text-center text-white/70" role="status">
            Nenhum balcão disponível neste departamento.
          </p>
        ) : many ? (
          <label className="mt-8 block text-sm">
            Balcão
            <select
              className="mt-2 w-full rounded-xl border border-white/20 bg-black/30 px-4 py-3 text-base text-white"
              defaultValue=""
              onChange={(e) => {
                if (e.target.value) onSelect(e.target.value);
              }}
            >
              <option value="" disabled>
                Selecione…
              </option>
              {terminals.map((t) => (
                <option key={t.id} value={t.id} className="text-ink">
                  {terminalLabel(t)}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <div className="mt-8 flex flex-col gap-3">
            {terminals.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => onSelect(t.id)}
                className="min-h-[72px] rounded-2xl border border-white/20 bg-white/10 px-5 py-4 text-left text-xl font-semibold transition hover:bg-white/15 enabled:active:scale-[0.99] motion-reduce:active:scale-100"
              >
                {terminalLabel(t)}
                <span className="mt-1 block text-sm font-normal text-white/55">Balcão ativo</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {onLogout && (
        <div className="mx-auto mt-6 w-full max-w-lg text-center">
          <button type="button" onClick={onLogout} className="text-sm text-white/55 underline-offset-2 hover:underline">
            Sair
          </button>
        </div>
      )}
    </div>
  );
}
