type Props = {
  config?: Record<string, unknown>;
};

export function TextZone({ config }: Props) {
  const text = String(config?.text || "");
  const align = String(config?.align || "center");
  if (!text) return null;
  return (
    <div
      className={`flex h-full w-full items-center px-[4%] text-[clamp(1rem,2vw,2rem)] font-medium text-white/90 ${
        align === "left" ? "justify-start text-left" : align === "right" ? "justify-end text-right" : "justify-center text-center"
      }`}
    >
      {text}
    </div>
  );
}
