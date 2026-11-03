import { DisplayBrand } from "./DisplayBrand";

/** Branded empty-media / soft fallback — never mentions CMS paths. */
export function DisplayFallback() {
  return (
    <div className="absolute inset-0 flex items-center justify-center overflow-hidden bg-gradient-to-br from-brand-800 via-brand-900 to-[#071a12]">
      <div
        className="pointer-events-none absolute inset-0 opacity-50"
        style={{
          background:
            "radial-gradient(circle at 15% 25%, rgba(255,255,255,0.14) 0, transparent 38%), radial-gradient(circle at 85% 65%, rgba(90,154,122,0.35) 0, transparent 45%)",
        }}
      />
      <div className="display-safe relative z-10 max-w-[70%] px-[4%] text-center">
        <DisplayBrand size="lg" />
        <p className="mt-6 text-[clamp(1.25rem,2.4vw,2.25rem)] font-medium text-brand-50">
          É bom ter você aqui.
        </p>
        <p className="mt-4 text-[clamp(1rem,1.6vw,1.5rem)] leading-relaxed text-white/70">
          Ofertas, novidades e informações para deixar sua compra ainda melhor.
        </p>
      </div>
    </div>
  );
}
