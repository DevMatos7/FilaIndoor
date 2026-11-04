# UX-8 — Playlist Studio

**Status:** READY FOR HOMOLOGATION  
**CODE VALIDATION:** PASS (após testes/build)  
**VISUAL VALIDATION:** PENDING  

## Objetivo

Transformar `/playlists` em um **Playlist Studio**: montar visualmente a sequência de conteúdos (ordem, duração, preview), usando a Media Library (UX-7) como fonte via MediaPicker.

## Auditoria (contrato real)

| Operação | Endpoint | Notas |
|----------|----------|-------|
| list/create/get/patch/delete | `/playlists` | soft delete (`active=False`) |
| add item | `POST …/items` | mesma asset pode repetir |
| bulk add | `POST …/items/bulk` | ordem = ordem do array |
| reorder | `PATCH …/items/reorder` | `item_ids` completo |
| duration | `PATCH …/items/{id}` | `duration_seconds >= 1` |
| player | `resolve_for_store` | `item.duration \|\| asset.duration \|\| 10` |

**Duration model (fonte única UI + player):**  
`effectiveDuration = PlaylistItem.duration_seconds || asset.duration_seconds || 10`  
Na prática o item sempre recebe duração ao adicionar (`asset.duration || 10`).

**Migration:** 0.

## Information architecture

```
Playlists list | Studio
                 ├── header (nome, contagem, duração total, salvar status)
                 ├── Preview (16:9 / 9:16, play/pause, prev/next)
                 └── Sequência (thumb, duração, drag + move up/down)
MediaPicker Drawer ← UX-7 patterns
```

Deep-link: `?playlist=<id>`.

## StoreContext

Sem seletor local. Troca de loja → AbortController, limpa seleção, skeleton.

## MediaPicker

- Busca / filtro tipo / grid MediaCard
- Multi-select; ordem de inserção = ordem de seleção
- Sem iframe no grid; só store atual

## Timeline / reorder

- Drag-and-drop otimista + rollback
- Ações acessíveis: Mover para cima / baixo
- Busy lock evita reorders concorrentes

## Preview

- Local/admin (sem WS/heartbeat/overrides)
- `StudioPreview` — muted; Play explícito; WEB iframe só após Play
- Clique no item → salta preview

## Referential safety

Delete bloqueado (409) se playlist estiver em:

- `Channel.default_playlist_id`
- `Schedule.playlist_id` (ativos)
- `Display.playlist_id` (ativos)

`usage` / `usage_count` / `total_duration_seconds` aditivos na API.

## Store isolation

- Asset de outra loja → ValidationError (já existia)
- `store_id` opcional em update/delete/items/reorder

## Persistence model

Cada ação persiste imediatamente. UI: Salvando… / Salvo / Erro — sem botão “Salvar playlist”.

## Accessibility

Focus trap UX-7 preservado; picker com `aria-pressed`; drag handle + alternativas teclado; preview controls rotulados.

## Limitations / débitos

- Virtualização de timeline grande  
- Preview com Layout Engine (canal)  
- Versioning / draft-publish  
- Transições por item  

## DISPLAY 2.0

Gate comercial/visual permanece PENDING (não alterado nesta sprint).
