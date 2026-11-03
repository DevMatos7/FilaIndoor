import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Alert, Button, Card, CardContent, Input } from "../design-system";
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

  useEffect(() => {
    document.body.classList.add("atmosphere-login");
    return () => document.body.classList.remove("atmosphere-login");
  }, []);

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
      <Card className="w-full max-w-md shadow-ds-md backdrop-blur">
        <CardContent className="p-8">
          <form onSubmit={onSubmit}>
            <h1 className="font-display text-3xl font-semibold text-brand-900">REAL Fila & Indoor</h1>
            <p className="mt-2 text-sm text-ink/70">Acesso administrativo</p>

            {expired && (
              <Alert variant="warning" className="mt-4" title="Sessão expirada">
                Entre novamente para carregar lojas e dispositivos.
              </Alert>
            )}

            <div className="mt-6 space-y-4">
              <Input
                label="E-mail"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="username"
              />
              <Input
                label="Senha"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>

            {error && (
              <Alert variant="danger" className="mt-4">
                {error}
              </Alert>
            )}

            <Button type="submit" className="mt-6 w-full" loading={loading}>
              {loading ? "Entrando…" : "Entrar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
