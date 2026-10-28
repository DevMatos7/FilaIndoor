# F0 — Auditoria do código atual

**Projeto:** REAL Fila & Indoor  
**Sprint:** 0 (Auditoria)  
**Data:** 27/10/2026  
**Workspace auditado:** `c:\Projetos\FilaIndoor`  
**Status do gate:** `F0 = PASS`  
**Decisão de base (27/10/2026):** **Opção A — Greenfield em `FilaIndoor`** (projeto do zero)

---

## 0. Decisão homologada

| Item | Valor |
|------|-------|
| Base | **A — Greenfield** em `c:\Projetos\FilaIndoor` |
| Dependência Checklist | Nenhuma (só referência conceitual de padrões) |
| Toledo / CISS | Fora do MVP; plataforma independente |
| Escopo inicial | Açougue: totem → senha → impressão → botoeira → TV/áudio → histórico/BI |

Sprint 1 **ainda não autorizada** até confirmação explícita do usuário.

---

## 1. Veredito

O workspace `FilaIndoor` está **vazio**: sem código-fonte, sem `.git`, sem `README`, sem Docker, sem migrations, sem testes e sem dependências.

O PRD assume “sistema existente” (auth, RBAC, layout, shell admin). Nesse workspace **não há base para reutilizar**.

Existe, no mesmo host, o monorepo irmão **`c:\Projetos\Checklist`** (CheckOps). Com a decisão greenfield, ele **não será** a base do código — apenas inspiração opcional de padrões.

**Consequência:** a Sprint 1 começa com scaffold do monorepo + core de fila (ver §9 / §10).

---

## 2. Estado do workspace `FilaIndoor`

| Item | Resultado |
|------|-----------|
| Arquivos de código | Nenhum |
| Git | Não inicializado (`fatal: not a git repository`) |
| Backend | Ausente |
| Frontend | Ausente |
| Banco / migrations | Ausente |
| Autenticação | Ausente |
| RBAC / permissões | Ausente |
| Layout / design system | Ausente |
| Docker / infra | Ausente |
| Testes | Ausente |
| Integrações | Ausente |
| Documentação prévia | Ausente (criada nesta F0) |

Pastas em `c:\Projetos\` no momento da auditoria:

| Pasta | Observação |
|-------|------------|
| `FilaIndoor` | **Vazia** (este workspace) |
| `Checklist` | Monorepo maduro FastAPI + React + Alembic + RBAC |
| `TaskMasterPro` | Stack Node/Express + Vite + Drizzle (menos alinhada ao PRD) |
| `CargaInteligente` | Sem conteúdo útil listado |

---

## 3. Arquitetura encontrada (referência: Checklist)

Usada **somente como referência de padrões**, não como código do workspace atual.

### 3.1 Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, Pydantic v2 |
| Auth | JWT (`python-jose` + `bcrypt`), OAuth2 password |
| Frontend | React 18 + Vite + Tailwind 3 + React Router 6 + Axios |
| Mobile | Expo (fora do escopo imediato do MVP Fila) |
| Rate limit | `slowapi` |
| Testes | `pytest` / `httpx` (backend); Vitest / Playwright (frontend) |
| Infra | Docker Compose (dev) |

Alinhamento com o PRD (§63): **alto** (FastAPI + React + Tailwind + PostgreSQL).

### 3.2 Organização backend (Checklist)

```text
backend/app/
├── api/routes/          # rotas HTTP
├── core/                # config, security, permissions
├── db/                  # session / Base
├── models/              # SQLAlchemy
├── schemas/             # Pydantic
├── services/            # regras de negócio
├── domain/              # domínios isolados (parcial)
├── middleware/
└── utils/
```

Padrão: **modular monolith** com routers → services → models.  
PRD sugere `modules/queue|signage|devices|...` — compatível; no Checklist o agrupamento é mais por pasta plana (`models/`, `services/`, `api/routes/`).

### 3.3 Multi-tenant e entidades reutilizáveis

Já existem conceitos equivalentes ao PRD:

| PRD | Checklist | Notas |
|-----|-----------|-------|
| `companies` | `models/company.py` | `external_code`, brand, feature_flags |
| `stores` | `models/store.py` | `company_id`, `external_code` |
| `departments` | `Sector` (`sector.py`) | Setor por loja — **análogo**, não idêntico |
| Users / operators | `user.py`, papéis | Operador de fila pode mapear para user + escopo |
| RBAC | `rbac.py` + `core/permissions.py` | Permissões por empresa; escopo loja/setor |
| Auditoria | `audit_log.py` | Padrão quem/quando/ação |
| Integrações ERP | `erp_*`, `governed_integration` | CISS/DB2 já explorados no ecossistema |
| Impressão | `equipment_label_print.py` / label print | ESC/POS / etiquetas — possível referência para Sprint 2 |
| Contadores | `ticket_year_counter.py` | Padrão de sequência protegida (tickets TI) — útil para numeração de senha |

**Atenção de nomenclatura:** Checklist já tem `ticket` no sentido de **chamado de TI**, não senha de fila. No módulo Fila, preferir nomes explícitos (`queue_ticket` / schema `queue_*`) se o código for embutido no Checklist, para evitar colisão.

### 3.4 Autenticação e permissões

- JWT stateless (`app/core/security.py`).
- RBAC com tabelas `rbac_permissions`, roles, vínculo role↔permission.
- Escopo empresa → loja → setor.
- Frontend: `navConfig.js` + `navPermissions.js` + `Layout.jsx`.

Permissões do PRD (`queue.*`, `signage.*`, `device.*`, `analytics.view`, `integration.*`) **ainda não existem**; devem ser adicionadas ao catálogo RBAC na Sprint 1 (ou no bootstrap, se greenfield).

### 3.5 Frontend / UX

- Shell: `Layout.jsx`, sidebar via `navigation/`.
- Páginas por domínio em `pages/` e componentes em `components/`.
- Tailwind; estados de loading/empty/error **variam por tela** — o DoD do PRD exige padronizar no módulo Fila.
- Não há TypeScript no frontend web do Checklist (JSX); o PRD pede TypeScript. Decisão necessária na Sprint 1 (ver débitos).

### 3.6 Banco e migrations

- PostgreSQL.
- Alembic presente; **centenas** de versions no Checklist (~126 arquivos em `alembic/versions` no momento da auditoria).
- Índices e multi-tenant já maduros.

### 3.7 Integrações relevantes ao roadmap Fila & Indoor

No Checklist já há superfície para:

- ERP / CISS (leitura, staging, governed integrations).
- Equipamentos, heartbeat-like health, agents.
- Impressão de etiquetas.
- Web push / notificações (útil no PDR REAL+).

Nada disso é fila de atendimento nem video indoor.

### 3.8 O que NÃO existe (nem no Checklist, no escopo Fila)

- `QueueSelectionEngine` / policies de prioridade.
- Lifecycle `WAITING → CALLED → SERVING → …`.
- Totem / emissão de senha.
- Display / WebSocket de chamada.
- Signage (assets, playlists, schedules).
- Edge offline de loja para fila.

---

## 4. Arquivos relevantes (referência Checklist)

### Backend

- `backend/app/main.py` — app FastAPI
- `backend/app/core/security.py`, `permissions.py`, `config.py`
- `backend/app/models/company.py`, `store.py`, `sector.py`, `user.py`, `rbac.py`
- `backend/app/models/ticket_year_counter.py` — referência de contador
- `backend/app/api/routes/auth.py`, `companies.py`, `rbac.py`
- `backend/alembic/` — migrations
- `backend/requirements.txt`

### Frontend

- `frontend/src/App.jsx`, `main.jsx`, `index.css`
- `frontend/src/components/Layout.jsx`
- `frontend/src/navigation/navConfig.js`, `navPermissions.js`
- `frontend/src/pages/Settings.jsx`, `Dashboard.jsx` — padrões de tela admin

### Infra

- `docker-compose.dev.yml` (e correlatos)
- `backend/env.example`

---

## 5. Padrões existentes a preservar (se a base for Checklist)

1. **Modular monolith** — sem microservices no MVP.
2. **Routers finos + services** — regras fora do controller.
3. **SQLAlchemy models + Pydantic schemas**.
4. **Migrations Alembic** para toda mudança de schema.
5. **JWT + RBAC** com escopo empresa/loja.
6. **Não gravar no ERP** a partir de módulos de leitura (já alinhado ao PRD CISS).
7. **Secrets em `.env`**, nunca no repositório.
8. **Reutilizar** Company/Store/User/RBAC — não duplicar.
9. **Navegação admin** via shell existente (`Layout` + `navConfig`).

Se a base for **greenfield em FilaIndoor**, adotar os mesmos princípios e a organização sugerida no PRD (`app/modules/queue/...`), sem copiar o domínio de checklist/tickets TI.

---

## 6. Funcionalidades reutilizáveis (Checklist → Fila)

| Capacidade | Reuso | Observação |
|------------|-------|------------|
| Company / Store | Alto | Direto |
| Sector ≈ Department | Médio | Adaptar ou criar `departments` alinhado ao PRD |
| User + login JWT | Alto | Operador / admin |
| RBAC | Alto | Novas permissões `queue.*` |
| Audit log | Alto | Cancelamentos, regras de prioridade |
| Contador transacional | Médio | Inspirar numeração de senha |
| Label/ESC-POS | Médio | Sprint 2 impressão |
| ERP/CISS adapters | Baixo no MVP | Sprint 12+ |
| Layout admin | Alto | Se embutido no Checklist |
| WebSocket genérico | Baixo | Provavelmente novo para displays |

---

## 7. Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Workspace vazio vs PRD “sistema existente” | Bloqueia Sprint 1 ambígua | Decisão explícita §9 antes de codar |
| Embutir no Checklist: colisão `ticket` | Confusão de domínio / bugs | Prefixo `queue_` / módulo isolado |
| Embutir no Checklist: acoplamento e migrations densas | Deploy arriscado | Módulo isolado + feature flag |
| Greenfield: reimplementar auth/RBAC/admin | Atraso do MVP | Scaffold mínimo + copiar padrões, não features de checklist |
| Frontend Checklist em JSX vs TS do PRD | Inconsistência | Aceitar JSX no admin embutido **ou** TS no greenfield |
| Assumir impressora/rede Toledo | Escopo indevido | MVP nativo; Toledo só após discovery |
| Offline Edge cedo demais | Complexidade | MVP online na LAN; Edge na Sprint 11 |

---

## 8. Débitos / gaps em relação ao PRD (antes de qualquer sprint)

- Sem repositório Git em `FilaIndoor`.
- Sem CI, lint, estrutura de testes.
- Sem especificação de brand tokens da REAL no workspace.
- Sem inventário de hardware (totem, ESC/POS, TVs) — necessário para Sprint 2/4.
- Sem confirmação se o produto é app standalone ou módulo CheckOps.

---

## 9. Decisão obrigatória antes da Sprint 1

Escolher **uma** base:

### Opção A — Greenfield em `FilaIndoor` (recomendação se o produto for independente)

- Inicializar Git + monorepo (`backend/`, `frontend/`, `docs/`).
- Stack PRD: FastAPI + SQLAlchemy + Alembic + PostgreSQL + React + TS + Tailwind.
- Implementar auth/RBAC **mínimos** + entidades company/store/department.
- Admin shell próprio (simples), alinhado ao UX do PRD.
- Pros: isolamento, TypeScript, estrutura `modules/` limpa.  
- Contras: recriar shell/auth; sem reuso imediato de Company real da operação.

### Opção B — Módulo dentro de `Checklist` (recomendação se for produto REAL unificado)

- Abrir/trabalhar no repo Checklist.
- Criar `backend/app/modules/queue/` (ou `services/queue_*` + models `queue_*`).
- Reutilizar Company, Store, Sector/Department, User, RBAC, Layout, nav.
- Novas permissões e item de sidebar “Atendimento / Filas”.
- Pros: identidade, usuários e lojas já existem; deploy conhecido.  
- Contras: cuidado com nome `ticket`; monorepo grande; frontend em JSX.

### Opção C — Novo repo clonando só a espinha do Checklist

- Scaffold FilaIndoor a partir de um subset (auth + company/store + layout).
- Pros: equilíbrio. Contras: custo de extração na Sprint 1.

**Sem essa decisão, a Sprint 1 não deve começar.**

---

## 10. Plano exato para Sprint 1 (após autorização + escolha da base)

Escopo Sprint 1 (inalterado do PRD): core de fila + engine + API + testes. **Sem totem.**

### 10.1 Pré-requisitos (Dia 0 da Sprint 1)

1. Confirmar Opção A, B ou C.
2. Inicializar Git (se A/C) ou branch `feature/queue-indoor-s1` (se B).
3. Subir PostgreSQL (Docker) e pipeline mínima de migration/teste.

### 10.2 Domínio / banco

Criar (ou mapear) tabelas:

- `companies`, `stores`, `departments` — **criar só se não reutilizar**
- `queues`
- `queue_priority_rules`
- `queue_tickets` (ou `tickets` se greenfield sem colisão)
- `ticket_events`
- (opcional S1) `queue_sequences` / uso de advisory lock + tabela de sequência

Índices do PRD §45.

Migration Alembic com downgrade seguro.

### 10.3 Domain services

```text
QueueSelectionEngine
├── FIFOQueuePolicy
├── WeightedPriorityPolicy
└── MaxWaitPolicy (composição / override)
```

State machine:

```text
WAITING → CALLED → SERVING → COMPLETED
CALLED → NO_SHOW
WAITING → CANCELLED
(+ EXPIRED quando regra existir)
```

Numeração transacional (nunca `MAX+1` sem lock).  
MVP regra: 3 normal / 1 prioritária; override se prioridade ≥ 10 min.

Event sourcing leve: toda transição → `ticket_events` imutável.

Idempotência: header `Idempotency-Key` em `POST .../tickets` e `POST .../next`.

### 10.4 API (prefixo conforme base: `/api/v1` greenfield ou convenção Checklist `/api`)

```http
POST /queues/{id}/tickets
GET  /queues/{id}/status
GET  /queues/{id}/waiting
POST /queues/{id}/next
POST /tickets/{id}/recall
POST /tickets/{id}/start
POST /tickets/{id}/complete
POST /tickets/{id}/no-show
POST /tickets/{id}/cancel
```

CRUD mínimo de queues + priority rules para seed/admin técnico (UI admin completa pode ficar enxuta na S1 e completar na S5).

### 10.5 Frontend admin (mínimo S1)

- Item de navegação “Atendimento → Filas” (ou equivalente).
- Telas: listar filas, detalhe/status, waiting list, inspector básico da senha.
- Estados: loading / empty / error / permission denied.
- **Não** construir totem, botoeira nem display.

### 10.6 Testes obrigatórios S1

- Unit: policies (FIFO, weighted, max wait), state machine.
- Integração: lifecycle completo.
- Concorrência: **100** criações simultâneas → 100 números únicos.
- Idempotência: mesma key não duplica ticket / não chama duas senhas.
- Dois `next` concorrentes não atribuem o mesmo ticket.

### 10.7 Documentação ao fechar S1

Atualizar:

- `docs/queue-indoor/progress.md` → `SPRINT 1 = READY FOR HOMOLOGATION`
- Esboços: `domain.md`, `api.md`

### 10.8 Explicitamente fora da Sprint 1

Totem, impressão, botoeira, WebSocket/TV, áudio, signage, CISS, Toledo, Edge, REAL+.

---

## 11. Convenções propostas (greenfield ou módulo)

- Python: tipagem, services sem I/O HTTP, policies puras testáveis.
- IDs: UUID string (padrão Checklist) ou UUID nativo — **uma escolha só**.
- Timezone: armazenar UTC; exibir no timezone da loja.
- Logs estruturados com `request_id`, `store_id`, `queue_id`.
- Feature flags: `TOLEDO_ENABLED=false`; fila nativa sempre disponível.

---

## 12. Gate F0

```text
F0 = PASS
```

Entregas F0:

- [x] Percorrer workspace `FilaIndoor`
- [x] Identificar ausência de stack local
- [x] Mapear referência Checklist (stack, auth, RBAC, layout, migrations, integrações)
- [x] Riscos e reuso
- [x] Plano Sprint 1
- [x] Documento `docs/queue-indoor/f0-audit.md`

**Proibido nesta sprint (cumprido):** refatoração ampla, dependências novas, implementação funcional.

---

## 13. Próximo passo (aguarda o usuário)

Responder com:

1. **Base:** A (greenfield FilaIndoor), B (módulo Checklist) ou C (híbrido).
2. Autorização explícita: **“Pode iniciar Sprint 1”**.

Até lá: **PARE** — nenhuma implementação de Sprint 1.
)
