import { ReactNode } from "react";

/** Full-bleed TV frame — never inherits admin shell. */
export function DisplayShell({ children }: { children: ReactNode }) {
  return (
    <div className="display-shell relative h-[100dvh] w-screen overflow-hidden bg-[#0c2b1e] font-sans text-white">
      {/* TV overscan safe margin for critical content lives in children */}
      {children}
    </div>
  );
}
