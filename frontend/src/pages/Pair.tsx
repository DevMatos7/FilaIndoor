import { useEffect, useMemo, useState } from "react";
import axios from "axios";

const apiBase = import.meta.env.VITE_API_URL || "/api/v1";

function deviceUuid(): string {
  const key = "filaindoor_device_uuid";
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

export default function Pair() {
  const uuid = useMemo(() => deviceUuid(), []);
  const [code, setCode] = useState<string | null>(null);
  const [expiresIn, setExpiresIn] = useState<number | null>(null);
  const [enrolled, setEnrolled] = useState(false);
  const [deviceName, setDeviceName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        const { data } = await axios.post(`${apiBase}/devices/pairing`, {
          device_uuid: uuid,
          device_type: "DISPLAY",
          app_version: "1.0.0",
          name: "Player TV",
        });
        if (cancelled) return;
        if (data.already_enrolled) {
          setEnrolled(true);
          setDeviceName(data.name);
          setCode(null);
        } else {
          setCode(data.pairing_code);
          setExpiresIn(data.expires_in ?? 600);
          setEnrolled(false);
        }
      } catch {
        if (!cancelled) setError("Não foi possível gerar o código de pareamento.");
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [uuid]);

  useEffect(() => {
    if (!expiresIn || enrolled) return;
    const id = window.setInterval(() => {
      setExpiresIn((s) => (s == null || s <= 0 ? 0 : s - 1));
    }, 1000);
    return () => window.clearInterval(id);
  }, [expiresIn != null, enrolled]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-brand-800 via-brand-900 to-ink px-6 text-white">
      <p className="font-display text-4xl font-semibold tracking-tight">REAL</p>
      <h1 className="mt-4 text-2xl font-medium">Pareamento do player</h1>
      {error && <p className="mt-6 text-amber-200">{error}</p>}
      {enrolled && (
        <p className="mt-8 text-center text-lg text-brand-100">
          Dispositivo já vinculado{deviceName ? `: ${deviceName}` : ""}.
          <br />
          Abra o player com o token do display.
        </p>
      )}
      {!enrolled && code && (
        <>
          <p className="mt-10 font-mono text-7xl font-bold tracking-[0.35em]">{code}</p>
          <p className="mt-6 max-w-md text-center text-brand-100">
            No admin, vá em <strong>Dispositivos</strong> → Adicionar e informe este código.
          </p>
          {expiresIn != null && (
            <p className="mt-4 text-sm text-white/60">
              Expira em {Math.floor(expiresIn / 60)}:{String(expiresIn % 60).padStart(2, "0")}
            </p>
          )}
        </>
      )}
      <p className="mt-10 text-xs text-white/40">uuid {uuid.slice(0, 8)}…</p>
    </div>
  );
}
