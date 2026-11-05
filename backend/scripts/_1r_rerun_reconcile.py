"""Re-run targeted reconcile on Module 1R sample product ids."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.queue import models as queue_models  # noqa: F401
from app.modules.retail import models as retail_models  # noqa: F401
from app.modules.retail.providers.ciss_db2 import CissDb2RetailProvider
from app.modules.retail.reconcile_service import RetailReconciliationService

ART = REPO / "docs" / "dynamic-retail-content" / "reconciliation" / "module-1-real-gate.json"
GERTEC = REPO / "docs" / "dynamic-retail-content" / "reconciliation" / "gertec-price-truth.json"


def main() -> None:
    get_settings.cache_clear()
    data = json.loads(ART.read_text(encoding="utf-8"))
    gertec = json.loads(GERTEC.read_text(encoding="utf-8"))
    store_id = data["store"]["id"]
    product_ids = [s["canonical"]["product_id"] for s in data["sample"] if s.get("canonical")]
    db = SessionLocal()
    try:
        rec = RetailReconciliationService(db, provider=CissDb2RetailProvider()).reconcile(store_id, product_ids)
        data["reconcile_summary"] = rec.get("summary")
        data["reconcile_results"] = rec.get("results")
        data["price_source_status"] = gertec["price_source_status"]
        data["gertec_confirmation"] = {
            "compared": gertec["compared"],
            "match": gertec["match"],
            "mismatch": gertec["mismatch"],
        }
        ART.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("reconcile", rec.get("summary"))
        # field rollup from reconcile
        fields = ["regular_price", "unit", "promotion", "quantity_tiers", "availability"]
        for f in fields:
            vals = [r["fields"].get(f, {}).get("result") for r in rec["results"] if "fields" in r]
            print(
                f,
                {
                    "MATCH": vals.count("MATCH"),
                    "MISMATCH": vals.count("MISMATCH"),
                    "NOT_COMPARABLE": vals.count("NOT_COMPARABLE"),
                },
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
