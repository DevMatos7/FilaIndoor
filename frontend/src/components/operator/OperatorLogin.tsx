import { FormEvent, ReactNode, useState } from "react";

type Props = {
  onSubmit: (email: string, password: string) => Promise<void>;
  error?: string | null;
};

export function OperatorLogin({ onSubmit, error }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handle(e: FormEvent) {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      await onSubmit(email, password);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <OperatorShellLite>
      <form
        onSubmit={handle}
        className="w-full max-w-md rounded-2xl border border-white/15 bg-white/8 px-6 py-8 shadow-lg backdrop-blur-sm"
      >
        <p className="text-center text-3xl font-bold tracking-tight">REAL</p>
        <h1 className="mt-3 text-center text-xl font-semibold">Acesso ao atendimento</h1>
        <p className="mt-1 text-center text-sm text-white/65">Identifique-se para operar o balcão</p>

        <label className="mt-8 block text-sm font-medium text-white/85">
          Usuário
          <input
            className="mt-1.5 w-full rounded-xl border border-white/20 bg-black/25 px-4 py-3 text-base text-white outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-400"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            autoComplete="username"
            required
            placeholder="seu.usuario@loja"
          />
        </label>

        <label className="mt-4 block text-sm font-medium text-white/85">
          Senha
          <input
            className="mt-1.5 w-full rounded-xl border border-white/20 bg-black/25 px-4 py-3 text-base text-white outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-400"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            autoComplete="current-password"
            required
          />
        </label>

        {error && (
          <p className="mt-4 rounded-xl border border-semantic-warning-border bg-semantic-warning-bg px-3 py-2 text-sm text-semantic-warning" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="mt-6 min-h-[56px] w-full rounded-xl bg-white text-lg font-bold text-brand-900 transition enabled:active:scale-[0.99] disabled:opacity-60 motion-reduce:active:scale-100"
        >
          {submitting ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </OperatorShellLite>
  );
}

function OperatorShellLite({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-[#0f1a15] px-4 py-8 font-sans text-white">
      {children}
    </div>
  );
}
