import { useEffect, useState } from "react";

type Props = {
  config?: Record<string, unknown>;
};

/** Local player clock — no API. */
export function ClockZone({ config }: Props) {
  const hour24 = config?.hour24 !== false;
  const showSeconds = config?.show_seconds === true;
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const opts: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    second: showSeconds ? "2-digit" : undefined,
    hour12: !hour24,
  };

  return (
    <div className="flex h-full w-full items-center justify-center tabular-nums text-[clamp(1.25rem,3vw,3rem)] font-semibold text-white/90">
      {now.toLocaleTimeString("pt-BR", opts)}
    </div>
  );
}
