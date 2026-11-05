# UX-12 — Visual QA Matrix

Evidências definitivas em `docs/productization/screenshots/final/`.
Capturas geradas por Playwright contra ambiente Docker local (web:5180, api:8010).

Legenda: **PASS** = revisado manualmente aceitável · **PASS\*** = aceitável com débito P2/P3 · **GAP** = estado não capturado nesta sprint (não bloqueante se área crítica coberta).

| ID | Área | Viewport | Estado | Screenshot | Resultado | Defeito |
|----|------|----------|--------|------------|-----------|---------|
| V-LOGIN-01 | Login | 1920×1080 | form | `admin/login-1920x1080.png` | PASS | — |
| V-LOGIN-02 | Login | 390×844 | form | `admin/login-390x844.png` | PASS | — |
| V-CC-01 | Command Center | 1920×1080 | normal | `admin/command-center-1920x1080.png` | PASS | — |
| V-CC-02 | Command Center | 1366×768 | normal | `admin/command-center-1366x768.png` | PASS | — |
| V-CC-03 | Command Center | 768×1024 | tablet | `admin/command-center-768x1024.png` | PASS | — |
| V-CC-04 | Command Center | 390×844 | mobile | `admin/command-center-390x844.png` | PASS | — |
| V-TOT-01 | Totem | 800×1280 | idle | `totem/totem-idle-800x1280.png` | PASS | — |
| V-TOT-02 | Totem | 768×1024 | idle | `totem/totem-idle-768x1024.png` | PASS | — |
| V-TOT-03 | Totem | 800×1280 | unavailable | `totem/totem-unavailable-800x1280.png` | PASS | — |
| V-TOT-04 | Totem | 800×1280 | success/processing | `totem/totem-success-or-processing-800x1280.png` | PASS | — |
| V-OP-01 | Operator | 390×844 | ready | `operator/operator-390x844.png` | PASS | — |
| V-OP-02 | Operator | 768×1024 | ready | `operator/operator-768x1024.png` | PASS | — |
| V-OP-03 | Operator | 390×844 | serving | — | GAP | D-P3-01 |
| V-DSP-01 | Display | 1920×1080 | player base | `display/display-player-1920x1080.png` | PASS | — |
| V-DSP-02 | Display | 1920×1080 | media_queue_footer | `display/display-media-queue-footer-1920x1080.png` | PASS | — |
| V-DSP-03 | Display | 1920×1080 | media_queue_sidebar | `display/display-media-queue-sidebar-1920x1080.png` | PASS | — |
| V-DSP-04 | Display | 1920×1080 | queue_fullscreen | `display/display-queue-fullscreen-1920x1080.png` | PASS | — |
| V-DSP-05 | Display | 1920×1080 | fullscreen_media | `display/display-fullscreen-media-1920x1080.png` | PASS | — |
| V-DSP-06 | Display | 1920×1080 | QUEUE_CALL | `display/display-queue-call-1920x1080.png` | PASS\* | D-P2-01 |
| V-DSP-07 | Display | 1920×1080 | EMERGENCY | `display/display-emergency-1920x1080.png` | PASS | — |
| V-DSP-08 | Display | 1920×1080 | MANUAL | `display/display-manual-1920x1080.png` | PASS\* | D-P2-02 |
| V-DSP-09 | Display | 3840×2160 | footer 4K | `display/display-media-queue-footer-3840x2160.png` | PASS | — |
| V-DSP-10 | Display | 1080×1920 | portrait sanity | `display/display-portrait-1080x1920.png` | PASS | — |
| V-MED-01 | Media Library | 1920×1080 | library | `media/media-library-1920x1080.png` | PASS | — |
| V-MED-02 | Media Library | 1366×768 | library | `media/media-library-1366x768.png` | PASS | — |
| V-MED-03 | Media Library | 390×844 | mobile | `media/media-library-390x844.png` | PASS | — |
| V-MED-04 | Media Library | 1920×1080 | new drawer | `media/media-new-drawer-1920x1080.png` | PASS | — |
| V-PL-01 | Playlist Studio | 1920×1080 | list | `playlist/playlist-studio-1920x1080.png` | PASS | — |
| V-PL-02 | Playlist Studio | 1920×1080 | populated | `playlist/playlist-studio-populated-1920x1080.png` | PASS | — |
| V-PL-03 | Playlist Studio | 390×844 | mobile | `playlist/playlist-studio-390x844.png` | PASS | — |
| V-PRG-01 | Programming | 1920×1080 | studio | `programming/programming-1920x1080.png` | PASS | — |
| V-PRG-02 | Programming | 1366×768 | studio | `programming/programming-1366x768.png` | PASS | — |
| V-PRG-03 | Programming | 1920×1080 | Hoje | `programming/programming-hoje-1920x1080.png` | PASS | — |
| V-PRG-04 | Programming | 1920×1080 | Semana | `programming/programming-semana-1920x1080.png` | PASS | — |
| V-PRG-05 | Programming | 390×844 | mobile | `programming/programming-390x844.png` | PASS | — |
| V-FLT-01 | Fleet | 1920×1080 | list | `fleet/fleet-1920x1080.png` | PASS | — |
| V-FLT-02 | Fleet | 1920×1080 | details | `fleet/fleet-details-1920x1080.png` | PASS | — |
| V-FLT-03 | Fleet | 390×844 | mobile | `fleet/fleet-390x844.png` | PASS | — |
| V-AN-01 | Analytics | 1920×1080 | overview | `analytics/analytics-overview-1920x1080.png` | PASS | — |
| V-AN-02 | Analytics | 1366×768 | overview | `analytics/analytics-overview-1366x768.png` | PASS | — |
| V-AN-03 | Analytics | 1920×1080 | 7d | `analytics/analytics-7d-1920x1080.png` | PASS | — |
| V-AN-04 | Analytics | 1920×1080 | 30d | `analytics/analytics-30d-1920x1080.png` | PASS | — |
| V-AN-05 | Analytics | 390×844 | mobile | `analytics/analytics-390x844.png` | PASS | — |

## Display 2.0 gate shots (obrigatórios)

| Requisito | Arquivo | Status |
|-----------|---------|--------|
| media_queue_footer 1920×1080 | `display-media-queue-footer-1920x1080.png` | PASS |
| media_queue_sidebar 1920×1080 | `display-media-queue-sidebar-1920x1080.png` | PASS |
| queue_fullscreen 1920×1080 | `display-queue-fullscreen-1920x1080.png` | PASS |
| QUEUE_CALL 1920×1080 | `display-queue-call-1920x1080.png` | PASS |
| EMERGENCY 1920×1080 | `display-emergency-1920x1080.png` | PASS |
