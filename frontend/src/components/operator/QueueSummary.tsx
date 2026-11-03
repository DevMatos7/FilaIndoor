type Props = {
  waiting: number;
  priority: number;
  empty?: boolean;
};

export function QueueSummary({ waiting, priority, empty }: Props) {
  return (
    <footer className="safe-op-x border-t border-white/10 px-4 py-4 text-center text-white/80 sm:px-5">
      {empty ? (
        <p className="text-base" role="status">
          Fila sem espera no momento
        </p>
      ) : (
        <p className="text-base sm:text-lg" aria-live="polite">
          <strong className="text-white">{waiting}</strong> aguardando
          <span className="mx-2 text-white/35">·</span>
          <strong className="text-white">{priority}</strong> prioritárias
        </p>
      )}
    </footer>
  );
}
