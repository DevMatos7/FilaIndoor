type Props = {
  number: string;
  priority?: boolean;
  printed: boolean;
};

export function TicketSuccess({ number, priority, printed }: Props) {
  return (
    <div
      className="rounded-2xl bg-white px-6 py-12 text-center text-brand-900 shadow-lg motion-safe:animate-[totemFade_280ms_ease-out] motion-reduce:animate-none"
      role="status"
      aria-live="polite"
    >
      <p className="text-lg font-medium uppercase tracking-wide text-brand-700">Sua senha</p>
      <p className="mt-3 font-sans text-[clamp(4.5rem,18vw,7.5rem)] font-bold leading-none tracking-tight tabular-nums text-brand-900">
        {number}
      </p>
      {priority && (
        <p className="mt-4 text-base font-semibold text-brand-800">Atendimento prioritário</p>
      )}
      <p className="mt-6 text-xl font-semibold text-brand-800">
        {printed ? "Senha impressa" : "Senha registrada"}
      </p>
      <p className="mt-4 text-lg text-ink/75">Você pode continuar suas compras.</p>
      <p className="mt-2 text-base text-ink/60">Acompanhe sua chamada nas telas da loja.</p>
    </div>
  );
}
