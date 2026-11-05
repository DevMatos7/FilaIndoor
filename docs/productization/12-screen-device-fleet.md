# UX-10 — Screen & Device Fleet

**Status:** READY FOR HOMOLOGATION  
**CODE VALIDATION:** PASS  
**VISUAL VALIDATION:** PENDING  

## Objetivo

Transformar `/devices` em **Telas & dispositivos**: responder quais telas/dispositivos existem na loja, o que cada tela deveria exibir, quais estão online e quais precisam de intervenção.

Fluxo fechado: Conteúdo → Playlist → Programação → Canal → **Tela → Player → Health**.

## Auditoria — modelo real

### Device (`devices`)

| Campo | Notas |
|-------|--------|
| `id`, `store_id`, `department_id` | isolamento |
| `display_id` | FK unique → Display (1:1) |
| `device_type` | `DISPLAY\|KIOSK\|PRINTER\|BUTTON\|EDGE` |
| `name`, `device_uuid` | |
| `status` | persistido; **status API = computado** |
| `last_seen_at`, `app_version`, `config_version`, `ip_address` | |
| `audio_enabled`, `pairing_*`, `enrolled_at`, `metadata` | |

### Display (`displays`)

| Campo | Notas |
|-------|--------|
| `id`, `store_id`, `department_id`, `queue_id` | |
| `name`, `code`, `token` | token = auth player |
| `active` | habilitado admin ≠ online |
| `audio_enabled`, `audio_template` | |
| `playlist_id`, `channel_id`, `screen_group_id` | canal só em Display |

### ScreenGroup

`store_id`, `channel_id`, `name`, `active` — organização secundária. Sem target SCREEN_GROUP em overrides (débito).

### Edge

Sem appliance ORM. `EdgeOutboxEvent` + sync counts. Tipo `EDGE` em `DEVICE_TYPES`; card sintético “Edge da loja” no fleet se não houver device EDGE enrolled.

### Relação Device ↔ Display

Entidades separadas. `Device.display_id` unique. `ensure_for_display` cria device espelho. **FleetItem** unifica: um card por TV (não duplica Device+Display).

Precedência de nome: **Display.name** > Device.name.

## Status model (fonte única)

`DeviceService._compute_status` — mesma regra do Command Center:

| Condição | Status |
|----------|--------|
| `status_stored == DISABLED` | DISABLED |
| sem store / sem last_seen | OFFLINE |
| age ≤ **90s** | ONLINE |
| age ≤ **300s** | DEGRADED |
| senão | OFFLINE |

`active` (Display/admin) ≠ `status` (saúde). Heartbeat player: ~30s.

Edge CC/Fleet: `failed > 0` ou `pending > 20` → DEGRADED.

## APIs

| Endpoint | Notas |
|----------|--------|
| `GET /devices/fleet?store_id=` | **novo** — summary, items (FleetItem), edge, groups, channels; **sem token bruto** |
| `POST /displays/{id}/channel` | assign com validação cross-store |
| `PATCH /displays/{id}` | agora valida canal/grupo da mesma loja; resposta sem token |
| `GET /devices/overview` | legado; filtro `store_id` opcional; token mascarado (`token_configured`) |
| enable/disable | `POST /devices/{id}/enable\|disable` (existentes) |
| pairing | `/devices/pairing`, `/devices/enroll`, `/pair` preservados |

### FleetItem (conceitual)

`id`, `device_id`, `display_id`, `name`, `device_type`, `status`, `last_seen*`, `channel`, `layout`, `programmed`, `overrides`, `diagnostics`, `token_configured`.

## Programado vs confirmado

```text
Programado agora: <playlist>   ← ScheduleService.active_at
confirmed: false               ← NÃO é Proof of Play
```

TV online ≠ conteúdo reproduzindo. Débito: `playback_events` / Proof of Play.

## Channel assignment

Só DISPLAY. Cross-store → **422**. Bump `config_version` → player refresca via mecanismo existente.

## UI

- StoreContext; sem seletor local
- KPIs MetricCard; filtros tipo/status; busca nome/código/canal/depto
- Cards + Details Drawer + diagnóstico
- Parear (enroll); enable/disable com ConfirmDialog
- ScreenGroups listados secundariamente
- Edge card + link `/edge`
- Auto-refresh 30s (pausa se `document.hidden`); stale snapshot

## Segurança

- Fleet nunca expõe token completo
- Overview/PATCH admin sem token bruto
- Isolamento store em fleet + channel assign

## Migrations

**0.**

## Limitações / débitos

- Device Commands / remote reboot / screenshot
- Proof of Play
- ScreenGroup override target
- Fleet pagination
- Store timezone (débito UX-9)
- Display 2.0 visual gate ainda PENDING

## Critérios

```text
Fleet /devices ✓
StoreContext ✓
status = CC thresholds ✓
channel assign + cross-store 422 ✓
programmed ≠ confirmed ✓
token não exposto ✓
player config após channel change ✓
build + testes ✓
VISUAL PENDING
```
