from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.analytics.routes import router as analytics_router
from app.modules.auth.routes import router as auth_router
from app.modules.org.routes.org import router as org_router
from app.modules.queue.routes.devices_admin import router as devices_admin_router
from app.modules.queue.routes.kiosk import router as kiosk_router
from app.modules.queue.routes.player import router as player_router
from app.modules.queue.routes.queues import router as queue_router
from app.modules.queue.routes.terminals import router as terminals_router
from app.modules.realtime.hub import hub
from app.modules.realtime.routes import router as realtime_router
from app.modules.signage.playlist_routes import router as playlist_router
from app.modules.signage.routes import router as signage_router
from app.modules.signage.schedule_routes import router as schedule_router
from app.modules.signage.storage import media_root
from app.modules.devices.routes import router as device_mgmt_router
from app.modules.devices import models as device_models  # noqa: F401
from app.modules.edge.routes import router as edge_router
from app.modules.edge import models as edge_models  # noqa: F401
from app.modules.integration.routes import router as integration_router
from app.modules.integration import models as integration_models  # noqa: F401
from app.modules.toledo.routes import router as toledo_router
from app.modules.toledo import models as toledo_models  # noqa: F401
from app.modules.real_plus.routes import router as real_plus_router
from app.modules.real_plus import models as real_plus_models  # noqa: F401

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.on_event("startup")
async def _bind_realtime_loop():
    import asyncio

    hub.bind_loop(asyncio.get_running_loop())
    media_root()  # garante pasta de storage

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "api": settings.api_prefix,
        "frontend": "http://localhost:5180",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


api = settings.api_prefix
app.include_router(auth_router, prefix=api)
app.include_router(org_router, prefix=api)
app.include_router(queue_router, prefix=api)
app.include_router(kiosk_router, prefix=api)
app.include_router(terminals_router, prefix=api)
app.include_router(player_router, prefix=api)
app.include_router(devices_admin_router, prefix=api)
app.include_router(device_mgmt_router, prefix=api)
app.include_router(edge_router, prefix=api)
app.include_router(integration_router, prefix=api)
app.include_router(toledo_router, prefix=api)
app.include_router(real_plus_router, prefix=api)
app.include_router(analytics_router, prefix=api)
app.include_router(signage_router, prefix=api)
app.include_router(playlist_router, prefix=api)
app.include_router(schedule_router, prefix=api)
app.include_router(realtime_router)

# Arquivos de mídia (Sprint 7) — /media/files/{store_id}/...
app.mount(
    settings.media_public_prefix,
    StaticFiles(directory=str(media_root())),
    name="media_files",
)
