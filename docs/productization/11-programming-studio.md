# UX-9 — Programming Studio

**Status:** READY FOR HOMOLOGATION  
**CODE VALIDATION:** PASS  
**VISUAL VALIDATION:** PENDING  

## Objetivo

Transformar `/channels` de CRUD técnico (Channel + Schedule + ScreenGroup) em **Programming Studio**: responder visualmente *qual conteúdo*, *em qual canal*, *em quais dias/horários*, *com qual prioridade* — sem exigir interpretação de enums/arrays técnicos.

URL preservada: `/channels`. Nav/UI: **Programação**.

## Auditoria — contrato real (código)

### Channel (`channels`)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID string | PK |
| `store_id` | FK stores | isolamento por loja |
| `name` | string | |
| `layout` | string | legacy, default `queue_media_split` |
| `layout_template_id` | FK layout_templates \| null | UX-6B |
| `default_playlist_id` | string \| null | conteúdo padrão |
| `active` | bool | soft-delete |
| `created_at` / `updated_at` | datetime | |

### Schedule (`schedules`)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID string | PK |
| `channel_id` | FK channels | |
| `playlist_id` | FK playlists | |
| `name` | string | título da programação |
| `start_date` / `end_date` | date \| null | vigência; null = sem limite |
| `start_time` / `end_time` | time | HH:MM; overnight se start > end |
| `days_of_week` | CSV string | ISO weekday `0=seg … 6=dom` |
| `priority` | NORMAL \| HIGH \| EMERGENCY | pesos 10 / 50 / 100 |
| `active` | bool | soft-delete |

### Semântica temporal (`ScheduleService.active_at`)

- Fonte de verdade compartilhada com o player (`resolve_playlist_for_display`).
- Horários: relógio do servidor (`utcnow` naive) — **sem timezone novo**.
- Intervalo normal: `start_time <= t <= end_time` (minuto truncado).
- Overnight (`start > end`): `t >= start OR t <= end`.
- Datas: fora de `[start_date, end_date]` (quando definidos) → não casa.
- Dia: `datetime.weekday()` ∈ `days_of_week`.
- Empate: maior `PRIORITY_WEIGHT`; desempate por `name`.
- Sem match → `default_playlist_id` (`source: channel_default`).

### Schedule.priority ≠ ScreenOverride.priority

| | Schedule | ScreenOverride (UX-6C) |
|--|----------|------------------------|
| Papel | Conteúdo **base** da agenda | Interrupção **temporária** da tela |
| Escopo | Canal | Display |
| EMERGENCY | Agenda base de alta prioridade | Override de emergência na TV |

O Studio **não** cria ScreenOverride.

## Banco / migrations

**0 migrations.** Experiência sobre domínio existente.

## APIs aditivas

| Endpoint | Uso |
|----------|-----|
| `GET /channels/{id}/programming-overview` | channel + current + next + schedules + conflicts |
| `GET /channels/{id}/next` | próximo início de agenda |
| `GET /channels/{id}/conflicts?structural=true` | conflitos estruturais |
| `DELETE /channels/{id}` | soft-delete; 409 se display/grupo em uso |

Endpoints legados (`/now`, CRUD) preservados. Overview chama o mesmo `active_at` do player.

### Conflict kinds

- `AMBIGUOUS` — mesma prioridade + overlap (datas ∩ dias ∩ horários)
- `RESOLVED_BY_PRIORITY` — prioridades diferentes; maior peso vence (warning, não bloqueio)

## StoreContext

Sem seletor local de loja. Troca → AbortController, limpa canal/`?channel=`, limpa overview, skeleton, recarrega canais.

Deep-link: `?channel=<id>` (restaurado se pertence à loja).

## Information architecture

```
Programação
├── Lista/cards de canais
├── Canal selecionado
│   ├── Agora / Próximo
│   ├── Hoje | Semana
│   └── Configuração (conteúdo padrão, layout, nome)
└── Drawer: Nova/editar programação
```

Channel ≠ Screen (UX-10). Channel ≠ Playlist (playlist = sequência; canal = quando toca).

## UI

- **PageHeader:** Programação · “Defina quando cada playlist será exibida…” · + Nova programação
- **Conteúdo padrão:** `default_playlist_id` com seletor visual (nome, itens, duração)
- **Layout:** nomes amigáveis + mini preview de zonas; legacy resolvido via Layout Engine
- **Timeline Hoje / Semana:** cards com nome, playlist, horário, dias, PriorityBadge, conflito textual
- **Form:** Playlist → Quando → Horário → Dias (toggles + presets) → Período → Prioridade → Resumo
- **Persistência:** imediata (Salvando… / Programação salva)
- ScreenGroup: não protagonista (UX-10)

## Responsividade

| Viewport | Comportamento |
|----------|---------------|
| 390×844 | canal select + dia único + lista |
| 768×1024 | cards por dia |
| 1366+ / 1920 | channel rail + Agora/Próximo + timeline 7 colunas |

## Acessibilidade

- PriorityBadge: ícone + texto + cor
- Conflito: texto/ícone (“Conflito de horário” / “Prioridade define a exibição”)
- Cards com `aria-label` descritivo
- Day toggles, Tabs, Drawer focus trap / restore

## Isolamento / segurança

- Playlist cross-store → 422
- Layout de outra loja → 422; system/global OK
- Delete channel bloqueado com displays/grupos ativos
- Delete schedule = soft-delete; playlist intacta

## Testes

`tests/integration/test_programming_studio_ux9.py` — overview = `/now` = player; AMBIGUOUS; EMERGENCY>HIGH; cross-store; delete 409; boundaries/overnight.

## Limitações / débitos

- Sem drag/resize na timeline, month view, publish/draft, copy schedule
- Atribuição Canal → Telas = UX-10
- Screenshots live: VISUAL PENDING
- Overnight: weekday checado no dia civil atual (semântica histórica do backend)

## Critérios

```text
Programming Studio em /channels ✓
StoreContext ✓
Agora/Próximo via active_at ✓
Hoje + Semana ✓
Prioridade traduzida ✓
Conflitos estruturais ✓
Default playlist + layout ✓
cross-store rejeitado ✓
player/layout/override regressão ✓
VISUAL PENDING
```
