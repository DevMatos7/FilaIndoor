type Props = {
  config?: Record<string, unknown>;
};

/**
 * MVP: static ticker text (no marquee). Motion deferred to avoid complexity;
 * respects prefers-reduced-motion if animation is added later.
 */
export function TickerZone({ config }: Props) {
  const text = String(config?.text || "Bem-vindo à REAL");
  return (
    <div className="flex h-full w-full items-center overflow-hidden bg-black/25 px-[3%]">
      <p className="truncate text-[clamp(0.9rem,1.6vw,1.5rem)] font-medium text-white/85">{text}</p>
    </div>
  );
}
