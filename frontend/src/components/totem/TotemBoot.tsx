type Props = {
  wordmark?: string;
};

export function TotemBoot({ wordmark = "REAL" }: Props) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 text-center text-white" aria-busy="true">
      <p className="text-5xl font-bold tracking-tight">{wordmark}</p>
      <p className="mt-6 text-xl text-brand-100">Preparando atendimento…</p>
      <span
        className="mt-8 h-10 w-10 rounded-full border-4 border-white/25 border-t-white motion-safe:animate-spin motion-reduce:animate-none"
        aria-hidden
      />
    </div>
  );
}
