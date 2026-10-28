from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.modules.realtime.hub import hub

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/v1/store/{store_id}")
async def store_ws(websocket: WebSocket, store_id: str):
    await hub.connect(store_id, websocket)
    try:
        while True:
            # Mantém conexão; cliente pode enviar ping textual
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(store_id, websocket)
    except Exception:  # noqa: BLE001
        await hub.disconnect(store_id, websocket)
