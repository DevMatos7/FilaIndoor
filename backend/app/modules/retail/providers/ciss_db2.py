from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.modules.retail.dto import (
    CanonicalPrice,
    CanonicalProduct,
    CanonicalPromotion,
    CanonicalStoreProduct,
)
from app.modules.retail.providers.base import RetailDataProvider

# CISS DATE fields are calendar-day; pilot stores use America/Sao_Paulo.
_PROMO_TZ = ZoneInfo("America/Sao_Paulo")


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _promo_window_active(starts: Any, ends: Any) -> bool:
    """Active when today (store TZ) is within [start, end]. Missing both ends → inactive."""
    today = datetime.now(_PROMO_TZ).date()
    s = _as_date(starts)
    e = _as_date(ends)
    if s is None and e is None:
        return False
    if s is not None and today < s:
        return False
    if e is not None and today > e:
        return False
    return True


def _flag_true(value: Any) -> bool:
    return str(value or "").strip().upper() in {"T", "S", "Y", "1"}


def _flag_inactive(value: Any) -> bool:
    # FLAGINATIVO: T = inativo
    return str(value or "").strip().upper() == "T"


def _to_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day") and not isinstance(value, datetime):
        # date
        return datetime.combine(value, time.min)
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def product_key(id_produto: Any, id_sub: Any) -> str:
    return f"{int(id_produto)}:{int(id_sub or 0)}"


class CissDb2RetailProvider(RetailDataProvider):
    """Adapter DB2 CISS — READ ONLY. SQL não vaza para API/frontend."""

    name = "ciss_db2"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.schema = (self.settings.db2_schema or "DBA").strip()
        if not re.fullmatch(r"[A-Za-z0-9_]+", self.schema):
            raise ValidationError("DB2_SCHEMA inválido")

    @property
    def configured(self) -> bool:
        return bool(self.settings.db2_conn_string or self.settings.ciss_db2_dsn)

    def capabilities(self) -> dict[str, Any]:
        return {
            **super().capabilities(),
            "configured": self.configured,
            "schema": self.schema,
            "note": "Configure DB2_CONN_STRING ou CISS_DB2_DSN",
        }

    def _connect(self):
        if not self.configured:
            raise ValidationError("DB2 não configurado")
        try:
            import pyodbc
        except ImportError as exc:  # pragma: no cover
            raise ValidationError("pyodbc não instalado no ambiente") from exc

        raw = self.settings.db2_conn_string or self.settings.ciss_db2_dsn
        if "Driver=" in raw or "DRIVER=" in raw:
            conn_str = raw
        else:
            parts = {k: v for k, v in (p.split("=", 1) for p in raw.split(";") if "=" in p)}
            driver = self.settings.db2_odbc_driver
            conn_str = (
                f"Driver={{{driver}}};"
                f"Database={parts.get('DATABASE')};"
                f"Hostname={parts.get('HOSTNAME')};"
                f"Port={parts.get('PORT', '50000')};"
                f"Protocol={parts.get('PROTOCOL', 'TCPIP')};"
                f"Uid={parts.get('UID')};"
                f"Pwd={parts.get('PWD')};"
            )
        timeout = int(self.settings.db2_query_timeout_seconds)
        return pyodbc.connect(conn_str, timeout=timeout)

    def _map_product_row(self, row: Any) -> CanonicalProduct:
        return CanonicalProduct(
            source_product_id=product_key(row[0], row[1]),
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

    def fetch_products(self, *, since: datetime | None = None, limit: int = 500) -> list[CanonicalProduct]:
        limit = max(1, min(limit, 5000))
        sql = f"""
            SELECT g.IDPRODUTO, g.IDSUBPRODUTO, p.DESCRCOMPRODUTO, g.DESCRRESPRODUTO, g.SUBDESCRICAO,
                   g.CODBAR, p.EMBALAGEMSAIDA, p.IDSECAO, p.IDGRUPO, p.IDSUBGRUPO,
                   s.DESCRSECAO, gr.DESCRGRUPO, sg.DESCRSUBGRUPO, g.FLAGINATIVO,
                   COALESCE(g.DTALTERACAO, g.DTULTIMAALTERACAO, p.DTALTERACAO) AS DTALT
            FROM {self.schema}.PRODUTO_GRADE g
            JOIN {self.schema}.PRODUTO p ON p.IDPRODUTO = g.IDPRODUTO
            LEFT JOIN {self.schema}.SECAO s ON s.IDSECAO = p.IDSECAO
            LEFT JOIN {self.schema}.GRUPO gr ON gr.IDGRUPO = p.IDGRUPO
            LEFT JOIN {self.schema}.SUBGRUPO sg ON sg.IDSUBGRUPO = p.IDSUBGRUPO
            WHERE 1=1
        """
        params: list[Any] = []
        if since:
            sql += " AND COALESCE(g.DTALTERACAO, g.DTULTIMAALTERACAO, p.DTALTERACAO) > ?"
            params.append(since)
        sql += " ORDER BY COALESCE(g.DTALTERACAO, g.DTULTIMAALTERACAO, p.DTALTERACAO) DESC FETCH FIRST ? ROWS ONLY"
        params.append(limit)

        cn = self._connect()
        try:
            cur = cn.cursor()
            cur.execute(sql, params)
            return [self._map_product_row(row) for row in cur.fetchall()]
        finally:
            cn.close()

    def fetch_products_by_ids(self, source_product_ids: list[str]) -> list[CanonicalProduct]:
        """Fetch pontual por chave canônica — usado na reconciliação de amostra."""
        out: list[CanonicalProduct] = []
        if not source_product_ids:
            return out
        cn = self._connect()
        try:
            cur = cn.cursor()
            sql = f"""
                SELECT g.IDPRODUTO, g.IDSUBPRODUTO, p.DESCRCOMPRODUTO, g.DESCRRESPRODUTO, g.SUBDESCRICAO,
                       g.CODBAR, p.EMBALAGEMSAIDA, p.IDSECAO, p.IDGRUPO, p.IDSUBGRUPO,
                       s.DESCRSECAO, gr.DESCRGRUPO, sg.DESCRSUBGRUPO, g.FLAGINATIVO,
                       COALESCE(g.DTALTERACAO, g.DTULTIMAALTERACAO, p.DTALTERACAO) AS DTALT
                FROM {self.schema}.PRODUTO_GRADE g
                JOIN {self.schema}.PRODUTO p ON p.IDPRODUTO = g.IDPRODUTO
                LEFT JOIN {self.schema}.SECAO s ON s.IDSECAO = p.IDSECAO
                LEFT JOIN {self.schema}.GRUPO gr ON gr.IDGRUPO = p.IDGRUPO
                LEFT JOIN {self.schema}.SUBGRUPO sg ON sg.IDSUBGRUPO = p.IDSUBGRUPO
                WHERE g.IDPRODUTO = ? AND g.IDSUBPRODUTO = ?
                FETCH FIRST 1 ROWS ONLY
            """
            for spid in source_product_ids:
                try:
                    a, b = spid.split(":", 1)
                    cur.execute(sql, int(a), int(b))
                except ValueError:
                    continue
                row = cur.fetchone()
                if row:
                    out.append(self._map_product_row(row))
            return out
        finally:
            cn.close()

    def fetch_prices_for_products(
        self, *, company_code: str, source_product_ids: list[str]
    ) -> list[CanonicalPrice]:
        """Preços/promo/qty apenas para SKUs informados (gate de reconciliação)."""
        out: list[CanonicalPrice] = []
        if not source_product_ids:
            return out
        cn = self._connect()
        try:
            cur = cn.cursor()
            for spid in source_product_ids:
                try:
                    idprod, idsub = [int(x) for x in spid.split(":", 1)]
                except ValueError:
                    continue
                cur.execute(
                    f"""
                    SELECT CAST(VALPRECOVAREJO AS DOUBLE), CAST(VALPROMVAREJO AS DOUBLE),
                           DTINIPROMOCAOVAR, DTFIMPROMOCAOVAR, QTDMINPROMVAREJO,
                           COALESCE(DTALTERACAOVAR, DTALTERACAO)
                    FROM {self.schema}.POLITICA_PRECO_PRODUTO
                    WHERE IDEMPRESA = ? AND IDPRODUTO = ? AND IDSUBPRODUTO = ?
                      AND VALPRECOVAREJO IS NOT NULL AND VALPRECOVAREJO > 0
                    FETCH FIRST 1 ROWS ONLY
                    """,
                    int(company_code),
                    idprod,
                    idsub,
                )
                r = cur.fetchone()
                if not r:
                    continue
                regular = _num(r[0])
                promo = _num(r[1])
                starts, ends, min_qty, src_at = _to_dt(r[2]), _to_dt(r[3]), _num(r[4]), _to_dt(r[5])
                if regular is not None:
                    out.append(
                        CanonicalPrice(
                            spid,
                            "REGULAR",
                            regular,
                            source_ref=f"politica:{company_code}:{spid}:REGULAR",
                            source_updated_at=src_at,
                        )
                    )
                if promo is not None and promo > 0:
                    out.append(
                        CanonicalPrice(
                            spid,
                            "PROMOTION",
                            promo,
                            min_qty=min_qty,
                            starts_at=starts,
                            expires_at=ends,
                            active=_promo_window_active(starts, ends),
                            source_ref=f"politica:{company_code}:{spid}:PROMOTION",
                            source_updated_at=src_at,
                        )
                    )
                cur.execute(
                    f"""
                    SELECT CAST(QTDPRODUTO AS DOUBLE), CAST(VALPRECOVAREJO AS DOUBLE), TIPOSTATUS, DTATUALIZACAO
                    FROM {self.schema}.PRODUTO_DESCONTO_QTDE
                    WHERE IDEMPRESA = ? AND IDPRODUTO = ? AND IDSUBPRODUTO = ?
                      AND VALPRECOVAREJO IS NOT NULL AND VALPRECOVAREJO > 0
                    ORDER BY QTDPRODUTO
                    """,
                    int(company_code),
                    idprod,
                    idsub,
                )
                for q in cur.fetchall():
                    if str(q[2] or "").upper() in {"I", "N"}:
                        continue
                    qty, amount = _num(q[0]), _num(q[1])
                    if qty is None or amount is None:
                        continue
                    out.append(
                        CanonicalPrice(
                            spid,
                            "QUANTITY",
                            amount,
                            min_qty=qty,
                            condition_text=f"A partir de {qty:g}",
                            source_ref=f"desconto_qtde:{company_code}:{spid}:{qty}",
                            source_updated_at=_to_dt(q[3]),
                        )
                    )
            return out
        finally:
            cn.close()

    def fetch_store_products(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalStoreProduct]:
        limit = max(1, min(limit, 5000))
        sql = f"""
            SELECT pe.IDPRODUTO, pe.IDSUBPRODUTO, pe.IDEMPRESA, pe.FLAGPERMITEVENDA, pe.DTALTERACAO
            FROM {self.schema}.PRODUTO_EMPRESA pe
            WHERE pe.IDEMPRESA = ?
        """
        params: list[Any] = [int(company_code)]
        if since:
            sql += " AND pe.DTALTERACAO > ?"
            params.append(since)
        sql += " ORDER BY pe.DTALTERACAO DESC FETCH FIRST ? ROWS ONLY"
        params.append(limit)
        cn = self._connect()
        try:
            cur = cn.cursor()
            cur.execute(sql, params)
            return [
                CanonicalStoreProduct(
                    source_product_id=product_key(r[0], r[1]),
                    company_code=str(r[2]),
                    sellable=_flag_true(r[3]) or str(r[3]).upper() == "T",
                    available=True,
                    source_updated_at=_to_dt(r[4]),
                )
                for r in cur.fetchall()
            ]
        finally:
            cn.close()

    def fetch_prices(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalPrice]:
        limit = max(1, min(limit, 10000))
        # CAST AS DOUBLE: driver ODBC IBM devolve DECIMAL(15,6) sem escala
        # (ex.: 2.19 → Decimal('2190000')); CHAR/DOUBLE preservam o valor real.
        sql = f"""
            SELECT IDPRODUTO, IDSUBPRODUTO,
                   CAST(VALPRECOVAREJO AS DOUBLE) AS VALPRECOVAREJO,
                   CAST(VALPROMVAREJO AS DOUBLE) AS VALPROMVAREJO,
                   DTINIPROMOCAOVAR, DTFIMPROMOCAOVAR, QTDMINPROMVAREJO,
                   COALESCE(DTALTERACAOVAR, DTALTERACAO) AS DTALT
            FROM {self.schema}.POLITICA_PRECO_PRODUTO
            WHERE IDEMPRESA = ?
              AND VALPRECOVAREJO IS NOT NULL
              AND VALPRECOVAREJO > 0
        """
        params: list[Any] = [int(company_code)]
        if since:
            sql += " AND COALESCE(DTALTERACAOVAR, DTALTERACAO) > ?"
            params.append(since)
        sql += " ORDER BY COALESCE(DTALTERACAOVAR, DTALTERACAO) DESC FETCH FIRST ? ROWS ONLY"
        params.append(limit)

        cn = self._connect()
        try:
            cur = cn.cursor()
            cur.execute(sql, params)
            out: list[CanonicalPrice] = []
            for r in cur.fetchall():
                spid = product_key(r[0], r[1])
                regular = _num(r[2])
                promo = _num(r[3])
                starts = _to_dt(r[4])
                ends = _to_dt(r[5])
                min_qty = _num(r[6])
                src_at = _to_dt(r[7])
                if regular is not None:
                    out.append(
                        CanonicalPrice(
                            spid,
                            "REGULAR",
                            regular,
                            source_ref=f"politica:{company_code}:{spid}:REGULAR",
                            source_updated_at=src_at,
                        )
                    )
                if promo is not None and promo > 0:
                    out.append(
                        CanonicalPrice(
                            spid,
                            "PROMOTION",
                            promo,
                            min_qty=min_qty,
                            starts_at=starts,
                            expires_at=ends,
                            active=_promo_window_active(starts, ends),
                            source_ref=f"politica:{company_code}:{spid}:PROMOTION",
                            condition_text=(f"A partir de {min_qty:g}" if min_qty and min_qty > 1 else None),
                            source_updated_at=src_at,
                        )
                    )
            # quantity discounts — CAST AS DOUBLE also on QTDPRODUTO (ODBC scale bug: 50 → 50000)
            qsql = f"""
                SELECT IDPRODUTO, IDSUBPRODUTO,
                       CAST(QTDPRODUTO AS DOUBLE) AS QTDPRODUTO,
                       CAST(VALPRECOVAREJO AS DOUBLE) AS VALPRECOVAREJO,
                       TIPOSTATUS, DTATUALIZACAO
                FROM {self.schema}.PRODUTO_DESCONTO_QTDE
                WHERE IDEMPRESA = ?
                  AND VALPRECOVAREJO IS NOT NULL
                  AND VALPRECOVAREJO > 0
                FETCH FIRST ? ROWS ONLY
            """
            cur.execute(qsql, int(company_code), min(limit, 2000))
            for r in cur.fetchall():
                if str(r[4] or "").upper() in {"I", "N"}:  # inactive heuristics
                    continue
                qty = _num(r[2])
                amount = _num(r[3])
                if amount is None or qty is None:
                    continue
                spid = product_key(r[0], r[1])
                out.append(
                    CanonicalPrice(
                        spid,
                        "QUANTITY",
                        amount,
                        min_qty=qty,
                        condition_text=f"A partir de {qty:g}",
                        source_ref=f"desconto_qtde:{company_code}:{spid}:{qty}",
                        source_updated_at=_to_dt(r[5]),
                    )
                )
            return out[:limit]
        finally:
            cn.close()

    def fetch_promotions(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalPromotion]:
        prices = self.fetch_prices(company_code=company_code, since=since, limit=limit)
        out: list[CanonicalPromotion] = []
        for p in prices:
            if p.price_kind != "PROMOTION":
                continue
            out.append(
                CanonicalPromotion(
                    source_product_id=p.source_product_id,
                    promo_amount=p.amount,
                    source_promotion_id=p.source_ref,
                    promotion_type="NORMAL" if not p.min_qty or p.min_qty <= 1 else "QUANTITY",
                    starts_at=p.starts_at,
                    expires_at=p.expires_at,
                    condition_text=p.condition_text,
                    active=p.active,
                    source_updated_at=p.source_updated_at,
                )
            )
        return out[:limit]

    def fetch_availability(
        self, *, company_code: str, since: datetime | None = None, limit: int = 500
    ) -> list[CanonicalStoreProduct]:
        limit = max(1, min(limit, 5000))
        sql = f"""
            SELECT IDEMPRESA, IDPRODUTO, IDSUBPRODUTO, SUM(QTDATUALESTOQUE) AS QTD
            FROM {self.schema}.PRODUTO_GRADE_SALDO_EST_VW
            WHERE IDEMPRESA = ?
            GROUP BY IDEMPRESA, IDPRODUTO, IDSUBPRODUTO
            FETCH FIRST ? ROWS ONLY
        """
        cn = self._connect()
        try:
            cur = cn.cursor()
            cur.execute(sql, int(company_code), limit)
            out: list[CanonicalStoreProduct] = []
            for r in cur.fetchall():
                qty = _num(r[3]) or 0.0
                out.append(
                    CanonicalStoreProduct(
                        source_product_id=product_key(r[1], r[2]),
                        company_code=str(r[0]),
                        sellable=True,
                        available=qty > 0,
                        stock_qty=qty,
                    )
                )
            return out
        finally:
            cn.close()

    def fetch_availability_for_products(
        self, *, company_code: str, source_product_ids: list[str]
    ) -> list[CanonicalStoreProduct]:
        out: list[CanonicalStoreProduct] = []
        if not source_product_ids:
            return out
        cn = self._connect()
        try:
            cur = cn.cursor()
            for spid in source_product_ids:
                try:
                    idprod, idsub = [int(x) for x in spid.split(":", 1)]
                except ValueError:
                    continue
                cur.execute(
                    f"""
                    SELECT CAST(SUM(QTDATUALESTOQUE) AS DOUBLE)
                    FROM {self.schema}.PRODUTO_GRADE_SALDO_EST_VW
                    WHERE IDEMPRESA = ? AND IDPRODUTO = ? AND IDSUBPRODUTO = ?
                    """,
                    int(company_code),
                    idprod,
                    idsub,
                )
                r = cur.fetchone()
                qty = _num(r[0]) if r and r[0] is not None else 0.0
                out.append(
                    CanonicalStoreProduct(
                        source_product_id=spid,
                        company_code=str(company_code),
                        sellable=True,
                        available=(qty or 0) > 0,
                        stock_qty=qty or 0.0,
                    )
                )
            return out
        finally:
            cn.close()
