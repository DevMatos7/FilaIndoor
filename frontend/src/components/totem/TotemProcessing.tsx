export function TotemProcessing() {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-2xl bg-white/12 px-6 py-16 text-center text-white"
      role="status"
      aria-live="assertive"
      aria-busy="true"
    >
      <span
        className="mb-6 h-12 w-12 rounded-full border-4 border-white/30 border-t-white motion-safe:animate-spin motion-reduce:animate-none"
        aria-hidden
      />
      <p className="text-2xl font-semibold sm:text-3xl">Estamos emitindo sua senha</p>
      <p className="mt-3 text-lg text-brand-100">Aguarde um instante — não toque novamente.</p>
    </div>
  );
}
