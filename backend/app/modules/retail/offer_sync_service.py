"""Sync PROMOCAO_GESTAO (+ items) and PRODUTO_CADEIA_PRECO into retail offer domain."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.retail.freshness import utcnow
from app.modules.retail.models import (
    RetailOfferCampaign,
    RetailOfferItem,
    RetailPriceChain,
    RetailProduct,
    RetailProductPriceChain,
)
from app.modules.retail.providers.base import RetailDataProvider
from app.modules.retail.providers.ciss_db2 import CissDb2RetailProvider

logger = logging.getLogger(__name__)


class RetailOfferSyncService:
    def __init__(self, db: Session, provider: RetailDataProvider | None = None):
        self.db = db
        self.provider = provider or CissDb2RetailProvider()

    def sync_offers(self, store_id: str, *, company_code: str, limit: int = 30) -> dict[str, Any]:
        fetch = getattr(self.provider, "fetch_offer_campaigns", None)
        fetch_items = getattr(self.provider, "fetch_offer_items", None)
        if not callable(fetch) or not callable(fetch_items):
            return {"status": "SKIPPED", "reason": "provider_no_offers", "changed_product_ids": []}

        campaigns = fetch(company_code=company_code, active_only=True, limit=limit)
        changed: set[str] = set()
        inserted = updated = skipped = 0
        for camp in campaigns:
            row = self.db.scalar(
                select(RetailOfferCampaign).where(
                    RetailOfferCampaign.store_id == store_id,
                    RetailOfferCampaign.source_system == "CISS",
                    RetailOfferCampaign.source_offer_id == camp["source_offer_id"],
                )
            )
            if not row:
                row = RetailOfferCampaign(
                    store_id=store_id,
                    source_system="CISS",
                    source_offer_id=camp["source_offer_id"],
                    name=camp["name"],
                    starts_at=camp.get("starts_at"),
                    expires_at=camp.get("expires_at"),
                    active=bool(camp.get("active", True)),
                    source_updated_at=camp.get("source_updated_at"),
                    synced_at=utcnow(),
                )
                self.db.add(row)
                self.db.flush()
                inserted += 1
            else:
                row.name = camp["name"]
                row.starts_at = camp.get("starts_at")
                row.expires_at = camp.get("expires_at")
                row.active = bool(camp.get("active", True))
                row.source_updated_at = camp.get("source_updated_at")
                row.synced_at = utcnow()
                updated += 1

            items = fetch_items(
                company_code=company_code, source_offer_id=camp["source_offer_id"], limit=500
            )
            seen_products: set[str] = set()
            for it in items:
                prod = self.db.scalar(
                    select(RetailProduct).where(
                        RetailProduct.source_system == "CISS",
                        RetailProduct.source_product_id == it["source_product_id"],
                    )
                )
                if not prod:
                    skipped += 1
                    continue
                seen_products.add(prod.id)
                chain_id = None
                if it.get("source_chain_id"):
                    chain = self.db.scalar(
                        select(RetailPriceChain).where(
                            RetailPriceChain.source_system == "CISS",
                            RetailPriceChain.source_chain_id == str(it["source_chain_id"]),
                        )
                    )
                    chain_id = chain.id if chain else None

                item_row = self.db.scalar(
                    select(RetailOfferItem).where(
                        RetailOfferItem.campaign_id == row.id,
                        RetailOfferItem.product_id == prod.id,
                    )
                )
                if not item_row:
                    item_row = RetailOfferItem(
                        campaign_id=row.id,
                        product_id=prod.id,
                        price_chain_id=chain_id,
                        regular_price=it.get("regular_price"),
                        offer_price=it.get("offer_price"),
                        raw_offer_price=it.get("raw_offer_price"),
                        calculation_type=it.get("calculation_type") or "DIRECT",
                        active=bool(it.get("active", True)),
                        synced_at=utcnow(),
                    )
                    self.db.add(item_row)
                    changed.add(prod.id)
                else:
                    before = (
                        item_row.offer_price,
                        item_row.calculation_type,
                        item_row.active,
                        item_row.regular_price,
                    )
                    item_row.price_chain_id = chain_id
                    item_row.regular_price = it.get("regular_price")
                    item_row.offer_price = it.get("offer_price")
                    item_row.raw_offer_price = it.get("raw_offer_price")
                    item_row.calculation_type = it.get("calculation_type") or "DIRECT"
                    item_row.active = bool(it.get("active", True))
                    item_row.synced_at = utcnow()
                    after = (
                        item_row.offer_price,
                        item_row.calculation_type,
                        item_row.active,
                        item_row.regular_price,
                    )
                    if before != after:
                        changed.add(prod.id)

            # deactivate missing items for this campaign
            existing_items = list(
                self.db.scalars(select(RetailOfferItem).where(RetailOfferItem.campaign_id == row.id)).all()
            )
            for ei in existing_items:
                if ei.product_id not in seen_products and ei.active:
                    ei.active = False
                    ei.synced_at = utcnow()
                    changed.add(ei.product_id)

        self.db.commit()
        logger.info(
            "retail.offer.sync store=%s campaigns=%s changed=%s",
            store_id,
            len(campaigns),
            len(changed),
        )
        return {
            "status": "SUCCESS",
            "campaigns": len(campaigns),
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "changed_product_ids": sorted(changed),
        }

    def sync_price_chains(self, *, limit: int = 2000) -> dict[str, Any]:
        fetch = getattr(self.provider, "fetch_price_chains", None)
        if not callable(fetch):
            return {"status": "SKIPPED", "reason": "provider_no_chains", "changed_product_ids": []}
        rows = fetch(limit=limit)
        inserted = updated = linked = 0
        changed: set[str] = set()
        for r in rows:
            chain = self.db.scalar(
                select(RetailPriceChain).where(
                    RetailPriceChain.source_system == "CISS",
                    RetailPriceChain.source_chain_id == r["source_chain_id"],
                )
            )
            if not chain:
                chain = RetailPriceChain(
                    source_system="CISS",
                    source_chain_id=r["source_chain_id"],
                    description=r["description"],
                    gondola_label=r.get("gondola_label"),
                    source_updated_at=r.get("source_updated_at"),
                    synced_at=utcnow(),
                )
                self.db.add(chain)
                self.db.flush()
                inserted += 1
            else:
                chain.description = r["description"]
                chain.gondola_label = r.get("gondola_label")
                chain.source_updated_at = r.get("source_updated_at")
                chain.synced_at = utcnow()
                updated += 1

            spid = r.get("source_product_id")
            if not spid:
                continue
            prod = self.db.scalar(
                select(RetailProduct).where(
                    RetailProduct.source_system == "CISS",
                    RetailProduct.source_product_id == spid,
                )
            )
            if not prod:
                continue
            link = self.db.scalar(
                select(RetailProductPriceChain).where(
                    RetailProductPriceChain.product_id == prod.id,
                    RetailProductPriceChain.price_chain_id == chain.id,
                )
            )
            if not link:
                self.db.add(
                    RetailProductPriceChain(
                        product_id=prod.id, price_chain_id=chain.id, synced_at=utcnow()
                    )
                )
                linked += 1
                changed.add(prod.id)
        self.db.commit()
        return {
            "status": "SUCCESS",
            "read": len(rows),
            "inserted": inserted,
            "updated": updated,
            "linked": linked,
            "changed_product_ids": sorted(changed),
        }
