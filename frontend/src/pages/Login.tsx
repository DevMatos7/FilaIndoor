import { FormEvent, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../services/api";

export default function Login() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("admin@real.local");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const expired = params.get("expired") === "1";
  const nextPath = useMemo(() => {
    const raw = params.get("next") || "/";
    return raw.startsWith("/") ? raw : "/";
  }, [params]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const body = new URLSearchParams();
      body.set("username", email);
      body.set("password", password);
      const { data } = await api.post("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      localStorage.setItem("token", data.access_token);
      navigate(nextPath);
    } catch {
      setError("Falha no login. Verifique usuário e senha.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md border border-brand-100 bg-white/80 p-8 shadow-sm backdrop-blur"
      >
        <h1 className="font-display text-3xl font-semibold text-brand-900">REAL Fila & Indoor</h1>
        <p className="mt-2 text-sm text-ink/70">Acesso administrativo</p>
        {expired && (
          <p className="mt-4 border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" role="status">
            Sessão expirada ou inválida. Entre novamente para carregar lojas e dispositivos.
          </p>
        )}
        <label className="mt-6 block text-sm font-medium">
          E-mail
          <input
            className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2 outline-none focus:border-brand-500"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
          />
        </label>
        <label className="mt-4 block text-sm font-medium">
          Senha
          <input
            className="mt-1 w-full border border-brand-100 bg-sand px-3 py-2 outline-none focus:border-brand-500"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            required
          />
        </label>
        {error && (
          <p className="mt-4 border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading}
          className="mt-6 w-full bg-brand-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
        >
          {loading ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
