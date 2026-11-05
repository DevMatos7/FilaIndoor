"""CLI: python -m app.tools.retail_data_sync --store <id> [--entity PRICE] [--full]"""
from __future__ import annotations

import argparse
import json
import sys

from app.db.session import SessionLocal
from app.modules.retail.sync_service import RetailSyncService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retail Data Foundation sync (CISS read-only)")
    parser.add_argument("--store", required=True, help="store UUID")
    parser.add_argument(
        "--entity",
        action="append",
        dest="entities",
        help="PRODUCT|PRICE|PROMOTION|AVAILABILITY (repeatable)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Ignora watermark (uso explícito obrigatório para full scan)",
    )
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        svc = RetailSyncService(db)
        results = svc.sync_store(args.store, entities=args.entities, full=args.full)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0 if all(r.get("status") == "SUCCESS" for r in results) else 2
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
