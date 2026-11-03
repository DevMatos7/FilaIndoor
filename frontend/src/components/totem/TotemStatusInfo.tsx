type Props = {
  hint?: string;
};

export function TotemStatusInfo({ hint = "Retire sua senha e continue suas compras normalmente." }: Props) {
  return (
    <footer className="safe-totem-x px-6 pb-8 pt-4 text-center text-brand-100">
      <p className="text-base text-white/80 sm:text-lg">{hint}</p>
      <p className="mt-3 text-sm text-white/55">Ajuda? Procure um colaborador.</p>
    </footer>
  );
}
