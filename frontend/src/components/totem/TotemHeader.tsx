type Props = {
  wordmark?: string;
  department: string;
  prompt?: string;
};

export function TotemHeader({ wordmark = "REAL", department, prompt }: Props) {
  return (
    <header className="safe-totem-x px-6 pb-2 pt-8 text-center text-white sm:pt-10">
      <p className="text-4xl font-bold tracking-tight sm:text-5xl" aria-label={wordmark}>
        {wordmark}
      </p>
      <h1 className="mt-3 text-2xl font-semibold uppercase tracking-[0.18em] text-brand-100 sm:text-3xl">
        {department}
      </h1>
      {prompt && (
        <p className="mx-auto mt-5 max-w-md text-lg font-medium text-white/90 sm:text-xl">{prompt}</p>
      )}
    </header>
  );
}
