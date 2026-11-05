"""1R.1 smoke: fix Campo Novo timezone + health + sample reconcile subset."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.org.models.entities import Store
from app.modules.queue import models as queue_models  # noqa: F401
from app.modules.retail import models as retail_models  # noqa: F401
from app.modules.retail.health_service import RetailHealthService
from app.modules.retail.models import RetailPrice, RetailProduct, RetailPromotion
from app.modules.retail.providers.ciss_db2 import CissDb2RetailProvider
from app.modules.retail.reconcile_service import RetailReconciliationService
from app.modules.retail.timezone_util import promo_window_active, validate_iana_timezone

ART = REPO / "docs" / "dynamic-retail-content" / "reconciliation" / "module-1-real-gate.json"
TARGET_TZ = "America/Cuiaba"


def main() -> int:
    get_settings.cache_clear()
    db = SessionLocal()
    try:
        store = db.scalar(select(Store).where(Store.name == "Loja Campo Novo"))
        if not store:
            print("FAIL: store missing")
            return 2
        before = store.timezone
        store.timezone = TARGET_TZ
        db.add(store)
        db.commit()
        db.refresh(store)
        print("timezone", before, "->", store.timezone)
        assert validate_iana_timezone(store.timezone) == TARGET_TZ

        health = RetailHealthService(db).health(store.id)
        print("health", health.get("status"), "tz_valid", health.get("timezone_valid"), health.get("timezone"))
        assert health["timezone"] == TARGET_TZ
        assert health["timezone_valid"] is True

        data = json.loads(ART.read_text(encoding="utf-8"))
        # subset: first 10 sample + any with promo tags
        sample = data["sample"]
        subset = []
        for s in sample:
            tags = s.get("tags") or []
            if "promo_expired" in tags or "qty" in tags or len(subset) < 10:
                if s.get("canonical"):
                    subset.append(s)
            if len(subset) >= 12:
                break
        product_ids = [s["canonical"]["product_id"] for s in subset]

        # Classification smoke: historical promos remain inactive under Cuiaba calendar
        from datetime import date

        for s in subset:
            if s.get("promo_status") in {"AFTER_END", "NO_PROMO", "BEFORE_START"}:
                starts = date.fromisoformat(s["promo_start"]) if s.get("promo_start") else None
                ends = date.fromisoformat(s["promo_end"]) if s.get("promo_end") else None
                if s.get("ciss_promo"):
                    active = promo_window_active(starts, ends, TARGET_TZ)
                    assert active is False, s["source_product_id"]

        # Local canonical unchanged for regular/unit
        unchanged = {"regular": 0, "unit": 0, "qty": 0}
        for s in subset:
            prod = db.get(RetailProduct, s["canonical"]["product_id"])
            assert prod
            regular = db.scalar(
                select(RetailPrice).where(
                    RetailPrice.store_id == store.id,
                    RetailPrice.product_id == prod.id,
                    RetailPrice.price_kind == "REGULAR",
                    RetailPrice.active.is_(True),
                )
            )
            assert abs(float(regular.amount) - float(s["ciss_regular"])) < 0.005
            assert (prod.unit or "").strip().upper() == (s["unit"] or "").strip().upper()
            unchanged["regular"] += 1
            unchanged["unit"] += 1
            qty_n = db.scalar(
                select(RetailPrice).where(
                    RetailPrice.store_id == store.id,
                    RetailPrice.product_id == prod.id,
                    RetailPrice.price_kind == "QUANTITY",
                    RetailPrice.active.is_(True),
                )
            )
            # just ensure no exception / still consistent presence
            expected_tiers = s.get("qty_tiers") or []
            if expected_tiers:
                rows = list(
                    db.scalars(
                        select(RetailPrice).where(
                            RetailPrice.store_id == store.id,
                            RetailPrice.product_id == prod.id,
                            RetailPrice.price_kind == "QUANTITY",
                            RetailPrice.active.is_(True),
                        )
                    ).all()
                )
                assert len(rows) == len(expected_tiers)
                unchanged["qty"] += 1

            promo_active = db.scalar(
                select(RetailPromotion).where(
                    RetailPromotion.store_id == store.id,
                    RetailPromotion.product_id == prod.id,
                    RetailPromotion.active.is_(True),
                )
            )
            if s.get("promo_status") != "ACTIVE":
                assert promo_active is None

        rec = RetailReconciliationService(db, provider=CissDb2RetailProvider()).reconcile(store.id, product_ids)
        print("reconcile subset", rec["summary"], "unchanged", unchanged)
        assert rec["summary"]["mismatch"] == 0

        data["store"]["timezone"] = TARGET_TZ
        data["timezone_correction"] = {"from": before, "to": TARGET_TZ, "smoke": "PASS"}
        ART.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("SMOKE PASS")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
