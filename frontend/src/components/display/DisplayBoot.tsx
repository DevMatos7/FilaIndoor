import { DisplayBrand } from "./DisplayBrand";

export function DisplayBoot() {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-[#0c2b1e]" aria-busy="true">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(circle at 18% 20%, rgba(255,255,255,0.12) 0, transparent 42%), radial-gradient(circle at 82% 70%, rgba(31,107,74,0.45) 0, transparent 48%)",
        }}
      />
      <DisplayBrand size="lg" className="relative z-10" />
      <span
        className="relative z-10 mt-10 h-10 w-10 rounded-full border-4 border-white/20 border-t-white motion-safe:animate-spin motion-reduce:animate-none"
        aria-hidden
      />
    </div>
  );
}
