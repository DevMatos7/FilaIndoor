import { SkipForward } from "lucide-react";

type Props = {
  disabled?: boolean;
  busy?: boolean;
  label?: string;
  onClick: () => void;
};

export function PrimaryAction({ disabled, busy, label = "PRÓXIMA SENHA", onClick }: Props) {
  return (
    <button
      type="button"
      disabled={disabled || busy}
      onClick={onClick}
      className="flex min-h-[104px] w-full items-center justify-center gap-3 rounded-2xl bg-brand-500 px-4 text-2xl font-bold tracking-wide text-white shadow-lg transition enabled:active:scale-[0.985] enabled:active:brightness-95 disabled:cursor-not-allowed disabled:opacity-45 motion-reduce:active:scale-100 sm:min-h-[112px] sm:text-3xl"
      aria-label="Chamar próxima senha"
    >
      <SkipForward className="h-8 w-8 shrink-0" aria-hidden />
      {busy ? "Chamando…" : label}
    </button>
  );
}
