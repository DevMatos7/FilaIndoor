import { DisplayBrand } from "./DisplayBrand";

export function DisplayUnavailable() {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-[#0c2b1e] px-[5%] text-center">
      <DisplayBrand size="lg" />
      <p className="mt-8 text-[clamp(1.25rem,2.2vw,2rem)] font-medium text-white/85">
        Esta tela está temporariamente indisponível.
      </p>
      <p className="mt-3 text-[clamp(0.95rem,1.4vw,1.25rem)] text-white/55">
        Em breve voltamos a compartilhar novidades com você.
      </p>
    </div>
  );
}
