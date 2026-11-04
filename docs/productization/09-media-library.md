# UX-7 — Media Library 2.0

**Status:** READY FOR HOMOLOGATION  
**CODE VALIDATION:** PASS (após testes/build)  
**VISUAL VALIDATION:** PENDING  

## Objetivo

Transformar `/media` de CRUD técnico em **biblioteca de conteúdos** (CMS de Digital Signage): encontrar, visualizar, filtrar, adicionar, inspecionar, editar e excluir com segurança.

## Auditoria MediaAsset (campos reais)

| Campo | Presente |
|-------|----------|
| id, store_id, name, media_type | ✓ |
| mime_type, original_filename, storage_key, public_url | ✓ |
| size_bytes, duration_seconds, width, height | ✓ |
| checksum, notes, active | ✓ |
| created_by, created_at, updated_at | ✓ |
| thumbnail_url | ✗ |
| approval_status / workflow | ✗ |
| available_from / expires_at | ✗ |
| usage_count (persistido) | ✗ — calculado aditivamente na API |

**Migration:** 0 — nenhuma alteração de schema.

## Information architecture

```
Conteúdos
  ├── Toolbar (busca · tipo · ordenação · contagem)
  ├── Grid MediaCard
  ├── Drawer Novo conteúdo
  └── Drawer Detalhes (+ editar / excluir)
```

Rota permanece `/media`. UI usa o termo **Conteúdos**.

## StoreContext

Sem seletor local. Troca de loja no Topbar: limpa seleção, skeleton, AbortController, recarrega.

## MediaCard

Pattern real do Design System (`patterns/MediaCard`):

- IMAGE: thumbnail `object-cover` + lazy  
- VIDEO: `preload="metadata"` no card (sem autoplay / sem FFmpeg)  
- WEB: ícone Globe + domínio (iframe só no details)

## Search / filters / sorting

- Busca client-side: nome, filename, URL  
- Filtros: Todos | Imagens | Vídeos | Web  
- Ordenação: Mais recentes | Mais antigos | Nome A–Z  

## Novo conteúdo

Drawer com tipo (Imagem / Vídeo / Página Web) → upload ou URL → nome → salvar.  
Drag-and-drop + input file. Progresso Axios quando disponível.  
Limites via `GET /media/limits` (aditivo).

## Details / Edit / Delete

- Preview IMAGE contain / VIDEO controls / WEB iframe sandbox + abrir nova aba  
- Editar: nome, duração, notes (`PATCH /media/{id}`) — sem replace de arquivo  
- Delete: ConfirmDialog; bloqueado se `usage_count > 0` (playlist)

## Referential safety

`PlaylistItem.asset_id` tem CASCADE no banco; a API **bloqueia** soft/hard delete quando há itens de playlist referenciando o asset (409 Conflict).

## APIs aditivas

| Endpoint | Notas |
|----------|-------|
| GET /media | + `usage_count` batch |
| GET /media/limits | limites MB/MIME |
| GET /media/{id}?store_id= | isolation |
| PATCH /media/{id} | name/notes/duration |
| DELETE …?store_id= | isolation + block por uso |

Storage, URLs públicas e player/playlist **preservados**.

## Accessibility hardening (UX-1 débito)

Drawer / Modal / ConfirmDialog:

- `createPortal`  
- focus trap (Tab cycle)  
- ESC  
- scroll lock  
- focus restore  
- `role="dialog"` + `aria-modal`  
- Confirm destrutivo: foco inicial em **Cancelar**

## Performance

Sem iframe/autoplay por card. Lazy images. Sem paginação nesta sprint (débito se escala).

## States

Loading skeleton grid · empty library · empty filter · error + retry · stale warning.

## Limitations / débitos

- Server thumbnail generation  
- Pagination / virtualization  
- Content expiration / approval  
- Bulk ops / duplicate asset  
- Replace file mantendo asset_id  
- Adicionar à playlist (UX-8)

## DISPLAY 2.0 visual gate

Continua **COMMERCIAL/VISUAL PENDING** — não bloqueia UX-7; bloqueia piloto comercial do Display.
