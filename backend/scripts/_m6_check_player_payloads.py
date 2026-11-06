"""Verify Module 6 seeded dynamic payloads (descriptions + images)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.dynamic_content.content_service import DynamicContentService
from app.modules.dynamic_content.models import DynamicContent
from app.modules.org.models.entities import Store

SEED = ROOT.parent / "frontend" / "e2e" / ".auth" / "drc6-seed.json"


def main() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        store = db.get(Store, seed["store_id"])
        svc = DynamicContentService(db)
        out = {}
        for key, cid in seed["contents"].items():
            resolved = svc.resolve(cid, store.id)
            row = db.get(DynamicContent, cid)
            # player-shaped via resolve return
            pages = resolved.get("pages") or resolved.get("snapshot", {}).get("pages") or []
            if not pages and isinstance(resolved.get("items"), list):
                pages = [{"items": resolved["items"]}]
            items = []
            for p in pages:
                items.extend(p.get("items") or [])
            sample = []
            for it in items[:6]:
                desc = it.get("description") or ""
                sample.append(
                    {
                        "description": desc[:60],
                        "price": it.get("display_price") or it.get("price"),
                        "image": bool((it.get("image") or {}).get("url") if isinstance(it.get("image"), dict) else it.get("image_url")),
                        "banned_id": desc == (it.get("source_product_id") or "___"),
                    }
                )
            out[key] = {
                "content_type": row.content_type if row else None,
                "status": resolved.get("status") or resolved.get("publish_status"),
                "items": len(items),
                "with_image": sum(1 for s in sample if s["image"]),
                "sample": sample,
            }
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
