# UX-12 — QA Defect Register

Ambiente: Docker local (`docker compose`) · Playwright Chromium · 2026-11-05.

## Resumo

| Severidade | Abertos | Corrigidos nesta sprint |
|------------|---------|------------------------|
| P0 | 0 | 0 |
| P1 | 0 | 2 (test/env blockers resolvidos) |
| P2 | 2 | 1 |
| P3 | 3 | 0 |

**Gate de defeitos:** P0=0 · P1=0 → elegível a GO / CONDITIONAL GO.

---

## Corrigidos na UX-12

### D-FIX-01 — nginx `/media` conflitando com SPA
- **Severidade original:** P1 (Media Library / assets quebrados atrás do proxy)
- **Fix:** `frontend/nginx.conf` — proxy apenas `/media/files/`
- **Reteste:** Media Library E2E + screenshots PASS

### D-FIX-02 — PrivateRoute sem `next=`
- **Severidade original:** P2 (redirect pós-login perdia destino)
- **Fix:** `App.tsx` Private preserva `pathname+search` em `?next=`
- **Reteste:** login válido → `/analytics` PASS

### D-FIX-03 — `/auth/me` 500 com `admin@real.local`
- **Severidade original:** P2 (console/network 500 no happy path admin)
- **Fix:** `MeResponse.email: str` (não `EmailStr`) — `.local` é reserved
- **Reteste:** shell/admin rotas sem 500 no me

### D-FIX-04 — Totem E2E sem kiosk token
- **Severidade original:** P1 de teste (falso “unavailable”)
- **Fix:** fixture `kioskToken=kiosk-acougue-demo` + URL `?token=`
- **Reteste:** idle + double-tap ≤ +1 senha PASS

---

## Abertos — P2

### D-P2-01 — QUEUE_CALL: footer base permanece legível sob overlay
- **Área:** Display 2.0
- **Evidência:** `display-queue-call-1920x1080.png`
- **Descrição:** Arquitetura mantém mídia/base montada; footer da fila aparece em baixa opacidade atrás do overlay. Chamada (número + instrução) permanece legível.
- **Gate:** não bloqueante (intenção “base não desmonta”); polish de contraste overlay.
- **Follow-up:** POST-PILOT — reforçar scrim / z-index do overlay QUEUE_CALL.

### D-P2-02 — MANUAL overlay: título da mídia base ainda visível
- **Área:** Display 2.0
- **Evidência:** `display-manual-1920x1080.png` / `display-queue-call-or-manual-1920x1080.png`
- **Descrição:** Texto promocional da playlist pode colidir visualmente com título do MANUAL quando overlay não é full-bleed opaco.
- **Gate:** não bloqueante para piloto operacional (EMERGENCY e QUEUE_CALL críticos OK).
- **Follow-up:** POST-PILOT — scrim unificado para MANUAL/CAMPAIGN.

---

## Abertos — P3

### D-P3-01 — Cobertura visual Operator serving / empty / priority
- Screenshots dedicados não estabilizados nesta rodada (ready capturado).
- Follow-up: ampliar spec Operator.

### D-P3-02 — Matrix visual parcial (Media details, Playlist MediaPicker/preview, Fleet offline/Edge, Analytics SLA/comparison)
- Áreas funcionam via E2E smoke; estados cosméticos extras ficam como backlog de baseline.

### D-P3-03 — StoreSwitcher label genérico “Loja” em alguns frames
- Dados/seed; não impede troca de loja (E2E shell cobre StoreSwitcher).

---

## Console / network

| Achado | Classificação |
|--------|---------------|
| `/auth/me` 500 com EmailStr (pré-fix) | corrigido D-FIX-03 |
| 4xx em testes negativos (login inválido) | esperado |
| Warnings pytest `RealtimeHub.broadcast` never awaited | pré-existente / não regressão UX-12 |

---

## Não são defeitos (débito de produto já conhecido)

Ver `16-final-productization-report.md` § Débitos: Edge local ticketing, Store timezone, Proof of Play, Device Commands, SLA policy source-of-truth, etc.
