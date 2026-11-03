type Props = {
  variant: "printer" | "server";
  ticketNumber?: string;
  onRetry?: () => void;
};

export function TotemError({ variant, ticketNumber, onRetry }: Props) {
  if (variant === "printer") {
    return (
      <div
        className="rounded-2xl border-2 border-semantic-warning bg-semantic-warning-bg px-6 py-10 text-center text-brand-900"
        role="alert"
      >
        <p className="text-lg font-medium">Sua senha foi registrada</p>
        {ticketNumber && (
          <p className="mt-3 font-sans text-5xl font-bold tabular-nums sm:text-6xl">{ticketNumber}</p>
        )}
        <p className="mt-6 text-xl font-semibold">A impressão não foi concluída.</p>
        <p className="mt-2 text-lg text-ink/75">Procure um colaborador.</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-white px-6 py-12 text-center text-brand-900 shadow-lg" role="alert">
      <p className="text-2xl font-semibold sm:text-3xl">Não foi possível emitir sua senha agora.</p>
      <p className="mt-4 text-lg text-ink/75">Por favor, procure um colaborador.</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="totem-btn mt-8 min-h-[64px] w-full max-w-sm rounded-2xl bg-brand-700 px-6 py-4 text-lg font-bold text-white transition enabled:active:scale-[0.98] motion-reduce:active:scale-100"
        >
          Tentar novamente
        </button>
      )}
    </div>
  );
}
