# UX-2 — Information Architecture

## Domínios do produto (admin)

```text
VISÃO GERAL → Início
ATENDIMENTO → Filas, Histórico
INDOOR → Conteúdos, Playlists, Programação
DISPOSITIVOS → Fleet, Edge
INTELIGÊNCIA → Analytics
INTEGRAÇÕES → CISS, Toledo, REAL+
CONFIGURAÇÕES → Config. de filas
```

Itens futuros **ainda sem página** (não exibidos nesta sprint):

- Central da operação (UX-3)
- Indoor → Visão geral / Telas (UX-7/10)
- Atendimento → Ao vivo dedicado

---

## Mapeamento de rotas (URLs preservadas)

| Nav | Rota |
|-----|------|
| Início | `/` |
| Filas | `/queues` (+ `/queues/:id`) |
| Config. de filas | ativo em `/queues/:id/settings` |
| Histórico | `/history` |
| Conteúdos | `/media` |
| Playlists | `/playlists` |
| Programação | `/channels` |
| Fleet | `/devices` |
| Edge | `/edge` |
| Analytics | `/analytics` |
| CISS | `/integrations` |
| Toledo | `/toledo` |
| REAL+ | `/real-plus` |

Rotas públicas **fora** do shell:

```text
/login  /totem/:queueId  /operator/:queueId
/display/:queueId  /pair  /real-plus/:queueId
```

Não houve migração para `/indoor/*` — fica para sprints futuras com redirects.

---

## StoreContext

Arquivo: `frontend/src/context/StoreContext.tsx`

### Dados

- `stores`, `selectedStoreId`, `selectedStore`
- `loading`, `error`
- `setSelectedStore(id, { syncUrl? })`

### Prioridade de seleção

1. `?store=<id>` na URL  
2. `localStorage` (`real-selected-store`)  
3. primeira loja da API  

### Decisão de URL

- Troca de loja no switcher **sincroniza** `?store=` quando `syncUrl` (padrão true).
- Carga inicial **não polui** a URL se a loja veio só do localStorage.
- Deep-links `/media?store=abc` sincronizam o contexto.

### Migração nesta sprint

| Página | StoreContext |
|--------|--------------|
| Dashboard | disponível via shell (KPIs ainda globais) |
| Media | **migrada** — sem select local |
| Playlists, Channels, Devices, Edge, Integrations | **legacy select** (débito) |

---

## Breadcrumbs

Componente: `layouts/Breadcrumbs.tsx`

Exemplos:

```text
Início
Atendimento > Filas
Atendimento > Filas > {nome} > Configurações
Indoor > Conteúdos
Integrações > CISS
```

Nome da fila: `GET /queues/:id` leve no breadcrumb; fallback `"Detalhe da fila"`.
