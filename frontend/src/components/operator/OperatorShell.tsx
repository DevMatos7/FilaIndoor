import { ReactNode } from "react";

export function OperatorShell({ children }: { children: ReactNode }) {
  return (
    <div className="operator-root flex min-h-[100dvh] flex-col bg-[#0f1a15] font-sans text-white">
      {children}
    </div>
  );
}
