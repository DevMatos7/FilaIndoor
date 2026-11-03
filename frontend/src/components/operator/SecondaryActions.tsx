import { Check, UserX, Volume2 } from "lucide-react";

type Props = {
  hasTicket: boolean;
  busy?: boolean;
  activeAction?: "recall" | "no_show" | "complete" | null;
  onRecall: () => void;
  onNoShow: () => void;
  onComplete: () => void;
};

export function SecondaryActions({
  hasTicket,
  busy,
  activeAction,
  onRecall,
  onNoShow,
  onComplete,
}: Props) {
  const disabled = !hasTicket || busy;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          disabled={disabled}
          onClick={onRecall}
          className="flex min-h-[72px] flex-col items-center justify-center gap-1 rounded-2xl border-2 border-semantic-warning/70 bg-semantic-warning/15 px-3 text-base font-bold text-semantic-warning transition enabled:active:scale-[0.98] disabled:opacity-40 motion-reduce:active:scale-100 sm:min-h-[80px] sm:text-lg"
          aria-label="Rechamar senha atual"
        >
          <Volume2 className="h-5 w-5" aria-hidden />
          {activeAction === "recall" ? "Rechamando…" : "RECHAMAR"}
        </button>

        {/* Ausente: destrutiva — cor + ícone + texto; sem modal (toque rotineiro no balcão). */}
        <button
          type="button"
          disabled={disabled}
          onClick={onNoShow}
          className="flex min-h-[72px] flex-col items-center justify-center gap-1 rounded-2xl border-2 border-semantic-danger/80 bg-semantic-danger/15 px-3 text-base font-bold text-red-200 transition enabled:active:scale-[0.98] disabled:opacity-40 motion-reduce:active:scale-100 sm:min-h-[80px] sm:text-lg"
          aria-label="Marcar senha como ausente"
        >
          <UserX className="h-5 w-5" aria-hidden />
          {activeAction === "no_show" ? "Registrando…" : "AUSENTE"}
        </button>
      </div>

      <button
        type="button"
        disabled={disabled}
        onClick={onComplete}
        className="flex min-h-[72px] w-full items-center justify-center gap-2 rounded-2xl bg-semantic-success px-4 text-lg font-bold text-white transition enabled:active:scale-[0.985] disabled:opacity-40 motion-reduce:active:scale-100 sm:min-h-[80px] sm:text-xl"
        aria-label="Finalizar atendimento"
      >
        <Check className="h-6 w-6" aria-hidden />
        {activeAction === "complete" ? "Finalizando…" : "FINALIZAR ATENDIMENTO"}
      </button>
    </div>
  );
}
