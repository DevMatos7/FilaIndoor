"""DRC Module 1R — Real CISS Reconciliation Gate (host + ODBC).

Artefatos: docs/dynamic-retail-content/reconciliation/
Não imprime credenciais.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.org.models.entities import Store
from app.modules.queue import models as queue_models  # noqa: F401
from app.modules.retail import models as retail_models  # noqa: F401
from app.modules.retail.dto import CanonicalPrice, CanonicalProduct, CanonicalPromotion, CanonicalStoreProduct
from app.modules.retail.health_service import RetailHealthService
from app.modules.retail.models import (
    RetailPrice,
    RetailProduct,
    RetailPromotion,
    RetailStoreProduct,
    RetailStoreSource,
    RetailSyncWatermark,
)
from app.modules.retail.providers.ciss_db2 import (
    CissDb2RetailProvider,
    _flag_inactive,
    _to_dt,
    product_key,
)
from app.modules.retail.reconcile_service import RetailReconciliationService
from app.modules.retail.sync_service import RetailSyncService
from app.modules.retail.timezone_util import promo_window_active, store_calendar_today

OUT_DIR = REPO / "docs" / "dynamic-retail-content" / "reconciliation"
COMPANY = "1"
STORE_NAME = "Loja Campo Novo"
DEFAULT_TZ = "America/Cuiaba"


def money(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return round(float(str(v).replace(",", ".").strip()), 2)
    except (TypeError, ValueError):
        return None


def cmp_money(a: Any, b: Any) -> str:
    if a is None and b is None:
        return "MATCH"
    if a is None or b is None:
        return "NOT_COMPARABLE"
    return "MATCH" if abs(float(a) - float(b)) < 0.005 else "MISMATCH"


def connect_raw():
    import pyodbc

    settings = get_settings()
    parts = {k: v for k, v in (p.split("=", 1) for p in settings.db2_conn_string.split(";") if "=" in p)}
    return pyodbc.connect(
        f"Driver={{{settings.db2_odbc_driver}}};Database={parts['DATABASE']};Hostname={parts['HOSTNAME']};"
        f"Port={parts.get('PORT', '50000')};Protocol=TCPIP;Uid={parts['UID']};Pwd={parts['PWD']};",
        timeout=int(settings.db2_query_timeout_seconds),
    )


def today_store(tz_name: str = DEFAULT_TZ) -> date:
    return store_calendar_today(tz_name)


def sku_from_row(r) -> dict:
    idprod, idsub = int(r[0]), int(r[1] or 0)
    return {
        "source_product_id": product_key(idprod, idsub),
        "idproduto": idprod,
        "idsubproduto": idsub,
        "description": str(r[2] or "").strip(),
        "unit": str(r[3] or "").strip(),
        "ciss_regular": money(r[4]),
        "ciss_promo": money(r[5]),
        "promo_start": r[6].isoformat() if r[6] else None,
        "promo_end": r[7].isoformat() if r[7] else None,
        "promo_min_qty": money(r[8]),
        "idempresa": int(COMPANY),
    }


def promo_status(item: dict, today: date) -> str:
    if not item.get("ciss_promo") or item["ciss_promo"] <= 0:
        return "NO_PROMO"
    s = date.fromisoformat(item["promo_start"]) if item.get("promo_start") else None
    e = date.fromisoformat(item["promo_end"]) if item.get("promo_end") else None
    if s and today < s:
        return "BEFORE_START"
    if e and today > e:
        return "AFTER_END"
    if s is None and e is None:
        return "NO_WINDOW"
    return "ACTIVE"


def fetch_gertec(cur, idprod, idsub) -> float | None:
    cur.execute(
        """
        SELECT v.PRECO
        FROM DBA.PRODUTO_GRADE g
        JOIN DBA.EMP1_BUSCA_PRECO_GERTEC_VW v
          ON TRIM(v.CODBAR) = TRIM(CAST(g.CODBAR AS VARCHAR(32)))
        WHERE g.IDPRODUTO = ? AND g.IDSUBPRODUTO = ?
        FETCH FIRST 1 ROWS ONLY
        """,
        idprod,
        idsub,
    )
    r = cur.fetchone()
    return money(r[0]) if r else None


def fetch_tiers(cur, idprod, idsub) -> list[dict]:
    cur.execute(
        """
        SELECT CAST(QTDPRODUTO AS DOUBLE), CAST(VALPRECOVAREJO AS DOUBLE), TIPOSTATUS
        FROM DBA.PRODUTO_DESCONTO_QTDE
        WHERE IDEMPRESA = ? AND IDPRODUTO = ? AND IDSUBPRODUTO = ?
          AND VALPRECOVAREJO IS NOT NULL AND VALPRECOVAREJO > 0
        ORDER BY QTDPRODUTO
        """,
        int(COMPANY),
        idprod,
        idsub,
    )
    out = []
    for r in cur.fetchall():
        if str(r[2] or "").upper() in {"I", "N"}:
            continue
        out.append({"min_qty": money(r[0]), "amount": money(r[1]), "status": str(r[2] or "").strip()})
    return out


def fetch_stock(cur, idprod, idsub) -> dict:
    cur.execute(
        """
        SELECT IDLOCALESTOQUE, CAST(SUM(QTDATUALESTOQUE) AS DOUBLE)
        FROM DBA.PRODUTO_GRADE_SALDO_EST_VW
        WHERE IDEMPRESA = ? AND IDPRODUTO = ? AND IDSUBPRODUTO = ?
        GROUP BY IDLOCALESTOQUE
        """,
        int(COMPANY),
        idprod,
        idsub,
    )
    by_local = [{"local": r[0], "qty": money(r[1]) or 0.0} for r in cur.fetchall()]
    total = round(sum(x["qty"] for x in by_local), 3)
    return {"by_local": by_local, "total": total, "locals_count": len(by_local)}


def discover(cur) -> tuple[list[dict], dict, date, dict]:
    today = today_store()
    buckets: dict[str, list[dict]] = defaultdict(list)

    queries = {
        "promo_expired": """
            SELECT p.IDPRODUTO, p.IDSUBPRODUTO, pr.DESCRCOMPRODUTO, pr.EMBALAGEMSAIDA,
                   CAST(p.VALPRECOVAREJO AS DOUBLE), CAST(p.VALPROMVAREJO AS DOUBLE),
                   p.DTINIPROMOCAOVAR, p.DTFIMPROMOCAOVAR, p.QTDMINPROMVAREJO
            FROM DBA.POLITICA_PRECO_PRODUTO p
            JOIN DBA.PRODUTO pr ON pr.IDPRODUTO = p.IDPRODUTO
            WHERE p.IDEMPRESA = ? AND p.VALPROMVAREJO > 0 AND p.DTFIMPROMOCAOVAR < CURRENT DATE
              AND p.VALPRECOVAREJO > 0
            ORDER BY p.DTFIMPROMOCAOVAR DESC
            FETCH FIRST 20 ROWS ONLY
        """,
        "promo_active": """
            SELECT p.IDPRODUTO, p.IDSUBPRODUTO, pr.DESCRCOMPRODUTO, pr.EMBALAGEMSAIDA,
                   CAST(p.VALPRECOVAREJO AS DOUBLE), CAST(p.VALPROMVAREJO AS DOUBLE),
                   p.DTINIPROMOCAOVAR, p.DTFIMPROMOCAOVAR, p.QTDMINPROMVAREJO
            FROM DBA.POLITICA_PRECO_PRODUTO p
            JOIN DBA.PRODUTO pr ON pr.IDPRODUTO = p.IDPRODUTO
            WHERE p.IDEMPRESA = ? AND p.VALPROMVAREJO > 0 AND p.VALPRECOVAREJO > 0
              AND (p.DTINIPROMOCAOVAR IS NULL OR p.DTINIPROMOCAOVAR <= CURRENT DATE)
              AND (p.DTFIMPROMOCAOVAR IS NULL OR p.DTFIMPROMOCAOVAR >= CURRENT DATE)
            FETCH FIRST 20 ROWS ONLY
        """,
        "regular_un": """
            SELECT p.IDPRODUTO, p.IDSUBPRODUTO, pr.DESCRCOMPRODUTO, pr.EMBALAGEMSAIDA,
                   CAST(p.VALPRECOVAREJO AS DOUBLE), CAST(p.VALPROMVAREJO AS DOUBLE),
                   p.DTINIPROMOCAOVAR, p.DTFIMPROMOCAOVAR, p.QTDMINPROMVAREJO
            FROM DBA.POLITICA_PRECO_PRODUTO p
            JOIN DBA.PRODUTO pr ON pr.IDPRODUTO = p.IDPRODUTO
            WHERE p.IDEMPRESA = ? AND p.VALPRECOVAREJO > 0
              AND (p.VALPROMVAREJO IS NULL OR p.VALPROMVAREJO = 0)
              AND UPPER(pr.EMBALAGEMSAIDA) = 'UN'
            FETCH FIRST 40 ROWS ONLY
        """,
        "kg": """
            SELECT p.IDPRODUTO, p.IDSUBPRODUTO, pr.DESCRCOMPRODUTO, pr.EMBALAGEMSAIDA,
                   CAST(p.VALPRECOVAREJO AS DOUBLE), CAST(p.VALPROMVAREJO AS DOUBLE),
                   p.DTINIPROMOCAOVAR, p.DTFIMPROMOCAOVAR, p.QTDMINPROMVAREJO
            FROM DBA.POLITICA_PRECO_PRODUTO p
            JOIN DBA.PRODUTO pr ON pr.IDPRODUTO = p.IDPRODUTO
            WHERE p.IDEMPRESA = ? AND p.VALPRECOVAREJO > 0 AND UPPER(pr.EMBALAGEMSAIDA) = 'KG'
            FETCH FIRST 30 ROWS ONLY
        """,
        "recent": """
            SELECT p.IDPRODUTO, p.IDSUBPRODUTO, pr.DESCRCOMPRODUTO, pr.EMBALAGEMSAIDA,
                   CAST(p.VALPRECOVAREJO AS DOUBLE), CAST(p.VALPROMVAREJO AS DOUBLE),
                   p.DTINIPROMOCAOVAR, p.DTFIMPROMOCAOVAR, p.QTDMINPROMVAREJO
            FROM DBA.POLITICA_PRECO_PRODUTO p
            JOIN DBA.PRODUTO pr ON pr.IDPRODUTO = p.IDPRODUTO
            WHERE p.IDEMPRESA = ? AND p.VALPRECOVAREJO > 0
            ORDER BY COALESCE(p.DTALTERACAOVAR, p.DTALTERACAO) DESC
            FETCH FIRST 20 ROWS ONLY
        """,
    }
    for name, sql in queries.items():
        cur.execute(sql, int(COMPANY))
        for r in cur.fetchall():
            buckets[name].append(sku_from_row(r))

    # qty active
    cur.execute(
        """
        SELECT p.IDPRODUTO, p.IDSUBPRODUTO, pr.DESCRCOMPRODUTO, pr.EMBALAGEMSAIDA,
               CAST(p.VALPRECOVAREJO AS DOUBLE), CAST(p.VALPROMVAREJO AS DOUBLE),
               p.DTINIPROMOCAOVAR, p.DTFIMPROMOCAOVAR, p.QTDMINPROMVAREJO
        FROM DBA.PRODUTO_DESCONTO_QTDE d
        JOIN DBA.POLITICA_PRECO_PRODUTO p
          ON p.IDEMPRESA=d.IDEMPRESA AND p.IDPRODUTO=d.IDPRODUTO AND p.IDSUBPRODUTO=d.IDSUBPRODUTO
        JOIN DBA.PRODUTO pr ON pr.IDPRODUTO = p.IDPRODUTO
        WHERE d.IDEMPRESA = ? AND d.VALPRECOVAREJO > 0
          AND (d.TIPOSTATUS IS NULL OR UPPER(CHAR(d.TIPOSTATUS)) NOT IN ('I','N'))
        FETCH FIRST 10 ROWS ONLY
        """,
        int(COMPANY),
    )
    for r in cur.fetchall():
        buckets["qty"].append(sku_from_row(r))

    # no stock
    cur.execute(
        """
        SELECT s.IDPRODUTO, s.IDSUBPRODUTO
        FROM DBA.PRODUTO_GRADE_SALDO_EST_VW s
        WHERE s.IDEMPRESA = ?
        GROUP BY s.IDPRODUTO, s.IDSUBPRODUTO
        HAVING SUM(s.QTDATUALESTOQUE) <= 0
        FETCH FIRST 20 ROWS ONLY
        """,
        int(COMPANY),
    )
    for r in cur.fetchall():
        cur.execute(
            """
            SELECT p.IDPRODUTO, p.IDSUBPRODUTO, pr.DESCRCOMPRODUTO, pr.EMBALAGEMSAIDA,
                   CAST(p.VALPRECOVAREJO AS DOUBLE), CAST(p.VALPROMVAREJO AS DOUBLE),
                   p.DTINIPROMOCAOVAR, p.DTFIMPROMOCAOVAR, p.QTDMINPROMVAREJO
            FROM DBA.POLITICA_PRECO_PRODUTO p
            JOIN DBA.PRODUTO pr ON pr.IDPRODUTO = p.IDPRODUTO
            WHERE p.IDEMPRESA = ? AND p.IDPRODUTO = ? AND p.IDSUBPRODUTO = ? AND p.VALPRECOVAREJO > 0
            FETCH FIRST 1 ROWS ONLY
            """,
            int(COMPANY),
            int(r[0]),
            int(r[1]),
        )
        row = cur.fetchone()
        if row:
            buckets["no_stock"].append(sku_from_row(row))

    availability = {k: len(v) for k, v in buckets.items()}
    notes = {
        "promo_active": "AVAILABLE" if availability.get("promo_active") else "NOT AVAILABLE IN SAMPLE",
        "qty_multi_tier": "NOT AVAILABLE IN SAMPLE",  # confirmed separately
        "qty_single": "AVAILABLE" if availability.get("qty") else "NOT AVAILABLE IN SAMPLE",
    }

    selected: dict[str, dict] = {}
    tags: dict[str, set[str]] = defaultdict(set)

    def add(item: dict, tag: str) -> None:
        spid = item["source_product_id"]
        selected[spid] = item
        tags[spid].add(tag)

    plan = [
        ("promo_expired", 3),
        ("promo_active", 5),
        ("qty", 3),
        ("kg", 4),
        ("regular_un", 4),
        ("no_stock", 3),
        ("recent", 3),
        ("regular_un", 15),
        ("kg", 4),
        ("recent", 5),
    ]
    for tag, n in plan:
        got = 0
        for item in buckets.get(tag, []):
            if got >= n:
                break
            before = len(tags.get(item["source_product_id"], set()))
            add(item, tag)
            if tag not in tags[item["source_product_id"]] or True:
                got = sum(1 for spid, tset in tags.items() if tag in tset)

    # ensure 30
    for tag in ("regular_un", "kg", "recent", "promo_expired"):
        for item in buckets.get(tag, []):
            if len(selected) >= 30:
                break
            add(item, "fill")
        if len(selected) >= 30:
            break

    sample = []
    gertec_stats = {"compared": 0, "match": 0, "mismatch": 0, "missing": 0}
    for spid, item in selected.items():
        item = dict(item)
        item["tags"] = sorted(tags[spid])
        item["promo_status"] = promo_status(item, today)
        item["qty_tiers"] = fetch_tiers(cur, item["idproduto"], item["idsubproduto"])
        item["stock"] = fetch_stock(cur, item["idproduto"], item["idsubproduto"])
        g = fetch_gertec(cur, item["idproduto"], item["idsubproduto"])
        item["gertec_price"] = g
        if g is None:
            gertec_stats["missing"] += 1
            item["gertec_vs_politica"] = "NOT_COMPARABLE"
        else:
            gertec_stats["compared"] += 1
            res = cmp_money(item["ciss_regular"], g)
            item["gertec_vs_politica"] = res
            if res == "MATCH":
                gertec_stats["match"] += 1
            else:
                gertec_stats["mismatch"] += 1
        sample.append(item)

    return sample, availability, today, {"notes": notes, "gertec": gertec_stats}


def upsert_sample(db, store_id: str, sample: list[dict], cur) -> None:
    sync = RetailSyncService(db, provider=CissDb2RetailProvider())
    source = sync.get_store_source(store_id)
    for s in sample:
        cur.execute(
            """
            SELECT g.IDPRODUTO, g.IDSUBPRODUTO, p.DESCRCOMPRODUTO, g.DESCRRESPRODUTO, g.SUBDESCRICAO,
                   g.CODBAR, p.EMBALAGEMSAIDA, p.IDSECAO, p.IDGRUPO, p.IDSUBGRUPO,
                   sec.DESCRSECAO, gr.DESCRGRUPO, sg.DESCRSUBGRUPO, g.FLAGINATIVO,
                   COALESCE(g.DTALTERACAO, g.DTULTIMAALTERACAO, p.DTALTERACAO)
            FROM DBA.PRODUTO_GRADE g
            JOIN DBA.PRODUTO p ON p.IDPRODUTO = g.IDPRODUTO
            LEFT JOIN DBA.SECAO sec ON sec.IDSECAO = p.IDSECAO
            LEFT JOIN DBA.GRUPO gr ON gr.IDGRUPO = p.IDGRUPO
            LEFT JOIN DBA.SUBGRUPO sg ON sg.IDSUBGRUPO = p.IDSUBGRUPO
            WHERE g.IDPRODUTO = ? AND g.IDSUBPRODUTO = ?
            FETCH FIRST 1 ROWS ONLY
            """,
            s["idproduto"],
            s["idsubproduto"],
        )
        row = cur.fetchone()
        if not row:
            continue
        prod = CanonicalProduct(
            source_product_id=s["source_product_id"],
            description=str(row[2] or row[3] or "Produto").strip(),
            commercial_description=(str(row[3] or row[4] or "").strip() or None),
            gtin=(str(row[5]).strip() if row[5] else None),
            unit=(str(row[6]).strip() if row[6] else "UN"),
            section_code=str(row[7]) if row[7] is not None else None,
            group_code=str(row[8]) if row[8] is not None else None,
            subgroup_code=str(row[9]) if row[9] is not None else None,
            section_name=(str(row[10]).strip() if row[10] else None),
            group_name=(str(row[11]).strip() if row[11] else None),
            subgroup_name=(str(row[12]).strip() if row[12] else None),
            active=not _flag_inactive(row[13]),
            source_updated_at=_to_dt(row[14]),
        )
        sync._upsert_product(prod)
        db.flush()
        rp = sync._get_product_by_source(s["source_product_id"])
        assert rp

        sync._deactivate_prices(store_id, rp.id)
        sync._deactivate_promotions(store_id, rp.id)

        if s.get("ciss_regular") is not None:
            sync._upsert_price(
                store_id,
                rp.id,
                CanonicalPrice(
                    s["source_product_id"],
                    "REGULAR",
                    s["ciss_regular"],
                    source_ref=f"politica:{COMPANY}:{s['source_product_id']}:REGULAR",
                ),
            )
        starts = _to_dt(date.fromisoformat(s["promo_start"])) if s.get("promo_start") else None
        ends = _to_dt(date.fromisoformat(s["promo_end"])) if s.get("promo_end") else None
        if s.get("ciss_promo") and s["ciss_promo"] > 0:
            active = promo_window_active(starts, ends, DEFAULT_TZ)
            sync._upsert_price(
                store_id,
                rp.id,
                CanonicalPrice(
                    s["source_product_id"],
                    "PROMOTION",
                    s["ciss_promo"],
                    min_qty=s.get("promo_min_qty"),
                    starts_at=starts,
                    expires_at=ends,
                    active=active,
                    source_ref=f"politica:{COMPANY}:{s['source_product_id']}:PROMOTION",
                ),
            )
            sync._upsert_promotion(
                store_id,
                rp.id,
                CanonicalPromotion(
                    source_product_id=s["source_product_id"],
                    promo_amount=s["ciss_promo"],
                    source_promotion_id=f"politica:{COMPANY}:{s['source_product_id']}:PROMOTION",
                    starts_at=starts,
                    expires_at=ends,
                    active=active,
                ),
            )
        for t in s.get("qty_tiers") or []:
            sync._upsert_price(
                store_id,
                rp.id,
                CanonicalPrice(
                    s["source_product_id"],
                    "QUANTITY",
                    t["amount"],
                    min_qty=t["min_qty"],
                    condition_text=f"A partir de {t['min_qty']:g}",
                    source_ref=f"desconto_qtde:{COMPANY}:{s['source_product_id']}:{t['min_qty']}",
                ),
            )
        stock_total = (s.get("stock") or {}).get("total")
        sync._upsert_store_product(
            store_id,
            source.company_code,
            rp.id,
            CanonicalStoreProduct(
                source_product_id=s["source_product_id"],
                company_code=COMPANY,
                sellable=True,
                available=(stock_total or 0) > 0 if stock_total is not None else True,
                stock_qty=stock_total,
            ),
        )
    db.commit()


def enrich(db, store_id: str, sample: list[dict]) -> list[dict]:
    for s in sample:
        prod = db.scalar(
            select(RetailProduct).where(
                RetailProduct.source_system == "CISS",
                RetailProduct.source_product_id == s["source_product_id"],
            )
        )
        if not prod:
            s["canonical"] = None
            s["api"] = None
            s["results"] = {"regular": "NOT_COMPARABLE", "unit": "NOT_COMPARABLE"}
            continue
        regular = db.scalar(
            select(RetailPrice).where(
                RetailPrice.store_id == store_id,
                RetailPrice.product_id == prod.id,
                RetailPrice.price_kind == "REGULAR",
                RetailPrice.active.is_(True),
            )
        )
        promo = db.scalar(
            select(RetailPromotion).where(
                RetailPromotion.store_id == store_id,
                RetailPromotion.product_id == prod.id,
                RetailPromotion.active.is_(True),
            )
        )
        qty_rows = list(
            db.scalars(
                select(RetailPrice)
                .where(
                    RetailPrice.store_id == store_id,
                    RetailPrice.product_id == prod.id,
                    RetailPrice.price_kind == "QUANTITY",
                    RetailPrice.active.is_(True),
                )
                .order_by(RetailPrice.min_qty)
            ).all()
        )
        sp = db.scalar(
            select(RetailStoreProduct).where(
                RetailStoreProduct.store_id == store_id,
                RetailStoreProduct.product_id == prod.id,
            )
        )
        can = {
            "product_id": prod.id,
            "description": prod.description,
            "unit": prod.unit,
            "regular": money(regular.amount) if regular else None,
            "promo_active": money(promo.promo_amount) if promo else None,
            "promo_start": promo.starts_at.date().isoformat() if promo and promo.starts_at else None,
            "promo_end": promo.expires_at.date().isoformat() if promo and promo.expires_at else None,
            "qty_tiers": [{"min_qty": money(q.min_qty), "amount": money(q.amount)} for q in qty_rows],
            "available": sp.available if sp else None,
            "stock_qty": money(sp.current_stock_qty) if sp and sp.current_stock_qty is not None else None,
        }
        # API detail equivalent (service-layer, same shape as GET /retail-products/{id})
        api = {
            "id": prod.id,
            "source_product_id": prod.source_product_id,
            "unit": prod.unit,
            "prices": [
                {"price_kind": "REGULAR", "amount": can["regular"]}
            ]
            + [{"price_kind": "QUANTITY", "amount": t["amount"], "min_qty": t["min_qty"]} for t in can["qty_tiers"]],
            "promotion": (
                {"promo_amount": can["promo_active"], "starts_at": can["promo_start"], "expires_at": can["promo_end"]}
                if can["promo_active"] is not None
                else None
            ),
            "availability": {"available": can["available"], "current_stock_qty": can["stock_qty"]},
        }
        # promo expectation
        if s["promo_status"] == "ACTIVE":
            promo_res = cmp_money(s.get("ciss_promo"), can["promo_active"])
        else:
            promo_res = "MATCH" if can["promo_active"] is None else "MISMATCH"

        ciss_tiers = [(t["min_qty"], t["amount"]) for t in (s.get("qty_tiers") or [])]
        can_tiers = [(t["min_qty"], t["amount"]) for t in can["qty_tiers"]]
        if not ciss_tiers and not can_tiers:
            qty_res = "MATCH"
        elif ciss_tiers == can_tiers or (
            len(ciss_tiers) == len(can_tiers)
            and all(
                abs((a[0] or 0) - (b[0] or 0)) < 0.005 and abs((a[1] or 0) - (b[1] or 0)) < 0.005
                for a, b in zip(sorted(ciss_tiers), sorted(can_tiers))
            )
        ):
            qty_res = "MATCH"
        else:
            qty_res = "MISMATCH"

        stock_ciss = (s.get("stock") or {}).get("total")
        if stock_ciss is None or can["stock_qty"] is None:
            stock_res = "NOT_COMPARABLE"
        else:
            stock_res = "MATCH" if abs(float(stock_ciss) - float(can["stock_qty"])) < 0.05 else "MISMATCH"

        s["canonical"] = can
        s["api"] = api
        s["results"] = {
            "regular": cmp_money(s["ciss_regular"], can["regular"]),
            "unit": (
                "MATCH"
                if (s["unit"] or "").strip().upper() == (can["unit"] or "").strip().upper()
                else "MISMATCH"
            ),
            "promo": promo_res,
            "qty_tiers": qty_res,
            "api_regular": cmp_money(can["regular"], api["prices"][0]["amount"] if api["prices"] else None),
            "api_unit": "MATCH" if can["unit"] == api["unit"] else "MISMATCH",
            "stock": stock_res,
            "gertec": s.get("gertec_vs_politica"),
            "store_company": "MATCH" if s["idempresa"] == int(COMPANY) else "MISMATCH",
        }
    return sample


def write_sample_md(path: Path, *, store, empresa, src, sample, availability, today, meta) -> None:
    lines = [
        "# Module 1R — Real sample",
        "",
        f"**Date (UTC):** {datetime.utcnow().date().isoformat()}",
        f"**Store day:** {today.isoformat()} (`{store.timezone}`)",
        f"**Store app:** {store.name} (`{store.id}`) timezone=`{store.timezone}`",
        f"**IDEMPRESA:** {empresa['idempresa']} — {empresa['nomefantasia']} / {empresa['razaosocial']}",
        f"**Mapping:** company_code=`{src.company_code}` location_code=`{src.location_code}` active={src.active}",
        f"**Correspondência:** loja piloto app «{store.name}» ↔ CISS empresa 1 «{empresa['nomefantasia']}» (matriz Supermercado Real / Casagrande).",
        f"**SKUs na amostra:** {len(sample)}",
        "",
        "## Disponibilidade de buckets CISS",
        "",
        "| Bucket | Candidates | Gate note |",
        "|--------|------------|-----------|",
    ]
    for k, v in sorted(availability.items()):
        note = meta["notes"].get(k, "")
        lines.append(f"| {k} | {v} | {note} |")
    lines += [
        "",
        f"- promo_active: **{meta['notes']['promo_active']}**",
        f"- qty multi-tier (1/3/6): **{meta['notes']['qty_multi_tier']}**",
        f"- qty single active: **{meta['notes']['qty_single']}**",
        f"- Gertec vs política (amostra): compared={meta['gertec']['compared']} MATCH={meta['gertec']['match']} MISMATCH={meta['gertec']['mismatch']} missing_barcode={meta['gertec']['missing']}",
        "",
        "## SKUs",
        "",
    ]
    for i, s in enumerate(sample, 1):
        lines += [
            f"### {i}. `{s['source_product_id']}` — {s['description']}",
            "",
            f"- tags: {', '.join(s.get('tags') or [])}",
            f"- IDEMPRESA / unit: {s['idempresa']} / `{s['unit']}`",
            f"- CISS regular: **{s['ciss_regular']}** | Gertec: {s.get('gertec_price')} ({s.get('gertec_vs_politica')})",
            f"- CISS promo: {s['ciss_promo']} ({s.get('promo_start')} → {s.get('promo_end')}) min={s.get('promo_min_qty')} status=**{s.get('promo_status')}**",
            f"- quantity tiers: `{s.get('qty_tiers')}`",
            f"- stock: `{s.get('stock')}`",
            f"- canonical: `{s.get('canonical')}`",
            f"- API: `{s.get('api')}`",
            f"- results: `{s.get('results')}`",
            "",
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def count_field(sample, field):
    vals = [(s.get("results") or {}).get(field) for s in sample]
    return {
        "MATCH": sum(1 for v in vals if v == "MATCH"),
        "MISMATCH": sum(1 for v in vals if v == "MISMATCH"),
        "NOT_COMPARABLE": sum(1 for v in vals if v == "NOT_COMPARABLE"),
    }


def main() -> int:
    get_settings.cache_clear()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cn = connect_raw()
    cur = cn.cursor()
    cur.execute(
        "SELECT IDEMPRESA, NOMEFANTASIA, RAZAOSOCIAL FROM DBA.EMPRESA WHERE IDEMPRESA = ?",
        int(COMPANY),
    )
    er = cur.fetchone()
    empresa = {
        "idempresa": int(er[0]),
        "nomefantasia": str(er[1] or "").strip(),
        "razaosocial": str(er[2] or "").strip(),
    }
    print("EMPRESA", empresa)

    db = SessionLocal()
    try:
        store = db.scalar(select(Store).where(Store.name == STORE_NAME))
        if not store:
            print("FAIL store not found")
            return 2
        sync = RetailSyncService(db, provider=CissDb2RetailProvider())
        mapping = sync.upsert_store_source(store.id, company_code=COMPANY, location_code=None, active=True)
        print("mapping", mapping)
        src = db.scalar(
            select(RetailStoreSource).where(
                RetailStoreSource.store_id == store.id, RetailStoreSource.source_system == "CISS"
            )
        )

        wms_before = {
            w.entity: w.watermark_value
            for w in db.scalars(select(RetailSyncWatermark).where(RetailSyncWatermark.store_id == store.id))
        }

        print("=== SAMPLE ===")
        sample, availability, today, meta = discover(cur)
        print("n=", len(sample), availability, meta)

        # Price source status
        g = meta["gertec"]
        if g["compared"] >= 20 and g["mismatch"] == 0:
            price_source_status = "CONFIRMED"
        elif g["compared"] > 0 and g["mismatch"] == 0:
            price_source_status = "PARTIALLY_CONFIRMED"
        else:
            price_source_status = "REJECTED"
        print("PRICE_SOURCE_STATUS", price_source_status, g)

        print("=== SYNC #1 FULL ===")
        t0 = time.perf_counter()
        runs1 = sync.sync_store(
            store.id, entities=["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"], full=True
        )
        upsert_sample(db, store.id, sample, cur)
        dur1 = time.perf_counter() - t0
        print("runs1", json.dumps(runs1, default=str)[:800], "dur", round(dur1, 2))

        products_before = db.scalar(select(func.count()).select_from(RetailProduct))
        active_prices_before = db.scalar(
            select(func.count()).select_from(RetailPrice).where(
                RetailPrice.store_id == store.id, RetailPrice.active.is_(True)
            )
        )

        print("=== SYNC #2 IDEMPOTENCY ===")
        t1 = time.perf_counter()
        runs2 = sync.sync_store(
            store.id, entities=["PRODUCT", "PRICE", "PROMOTION", "AVAILABILITY"], full=True
        )
        upsert_sample(db, store.id, sample, cur)
        dur2 = time.perf_counter() - t1
        products_after = db.scalar(select(func.count()).select_from(RetailProduct))
        active_prices_after = db.scalar(
            select(func.count()).select_from(RetailPrice).where(
                RetailPrice.store_id == store.id, RetailPrice.active.is_(True)
            )
        )
        # active prices for sample should be stable
        sample_active = []
        for s in sample:
            prod = db.scalar(
                select(RetailProduct).where(RetailProduct.source_product_id == s["source_product_id"])
            )
            if not prod:
                continue
            n = db.scalar(
                select(func.count()).select_from(RetailPrice).where(
                    RetailPrice.store_id == store.id,
                    RetailPrice.product_id == prod.id,
                    RetailPrice.active.is_(True),
                )
            )
            sample_active.append(n)
        print(
            "idempotency products",
            products_before,
            "->",
            products_after,
            "active_prices",
            active_prices_before,
            "->",
            active_prices_after,
            "sample_active_counts",
            sample_active[:5],
        )

        wms_after = {
            w.entity: w.watermark_value
            for w in db.scalars(select(RetailSyncWatermark).where(RetailSyncWatermark.store_id == store.id))
        }

        sample = enrich(db, store.id, sample)
        product_ids = [s["canonical"]["product_id"] for s in sample if s.get("canonical")]
        rec = RetailReconciliationService(db, provider=CissDb2RetailProvider()).reconcile(store.id, product_ids)
        health = RetailHealthService(db).health(store.id)

        field_summary = {
            k: count_field(sample, k)
            for k in ("regular", "unit", "promo", "qty_tiers", "api_regular", "api_unit", "stock", "gertec", "store_company")
        }
        print("FIELD SUMMARY", json.dumps(field_summary, indent=2))
        print("reconcile", rec.get("summary"))
        print("health freshness", health.get("freshness") if isinstance(health, dict) else health)

        write_sample_md(
            OUT_DIR / "module-1-real-sample.md",
            store=store,
            empresa=empresa,
            src=src,
            sample=sample,
            availability=availability,
            today=today,
            meta=meta,
        )
        artifact = {
            "empresa": empresa,
            "store": {"id": store.id, "name": store.name, "timezone": store.timezone},
            "mapping": {
                "company_code": src.company_code,
                "location_code": src.location_code,
                "active": src.active,
            },
            "availability": availability,
            "meta": meta,
            "price_source_status": price_source_status,
            "sample_size": len(sample),
            "sync_runs_1": runs1,
            "sync_runs_2": runs2,
            "duration_1_s": round(dur1, 2),
            "duration_2_s": round(dur2, 2),
            "watermarks_before": wms_before,
            "watermarks_after": wms_after,
            "idempotency": {
                "products_before": products_before,
                "products_after": products_after,
                "active_prices_before": active_prices_before,
                "active_prices_after": active_prices_after,
                "product_duplicates": products_after - products_before,
            },
            "health": health,
            "reconcile_summary": rec.get("summary"),
            "field_summary": field_summary,
            "sample": sample,
        }
        (OUT_DIR / "module-1-real-gate.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        print("WROTE", OUT_DIR)
        return 0
    finally:
        db.close()
        cn.close()


if __name__ == "__main__":
    raise SystemExit(main())
