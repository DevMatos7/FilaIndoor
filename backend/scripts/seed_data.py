"""Seed inicial: empresa Real, loja Campo Novo, Açougue, fila, admin, totem e terminais."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.modules.org.models.entities import Company, Department, Store, User
from app.modules.queue.models import entities as queue_entities  # noqa: F401
from app.modules.queue.models.entities import Display, Queue, Terminal
from app.modules.queue.services.queue_service import QueueService
from app.modules.signage import models as signage_models  # noqa: F401
from app.modules.signage.models import Channel, MediaAsset, Playlist
from app.modules.signage.playlist_service import PlaylistService
from app.modules.signage.schedule_service import ScheduleService
from app.modules.signage.service import SignageService
from app.modules.devices import models as device_models  # noqa: F401
from app.modules.devices.service import DeviceService


def main() -> None:
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        company = db.scalar(select(Company).where(Company.name == "Real Supermercado"))
        if not company:
            company = Company(name="Real Supermercado", external_code="REAL")
            db.add(company)
            db.flush()

        store = db.scalar(select(Store).where(Store.name == "Loja Campo Novo", Store.company_id == company.id))
        if not store:
            store = Store(company_id=company.id, name="Loja Campo Novo", external_code="CAMPO_NOVO")
            db.add(store)
            db.flush()

        dept = db.scalar(select(Department).where(Department.store_id == store.id, Department.code == "ACOU"))
        if not dept:
            dept = Department(store_id=store.id, code="ACOU", name="Açougue")
            db.add(dept)
            db.flush()

        queue = db.scalar(select(Queue).where(Queue.department_id == dept.id, Queue.name == "Fila Açougue"))
        if not queue:
            db.commit()
            service = QueueService(db)
            queue = service.create_queue(
                department_id=dept.id,
                name="Fila Açougue",
                normal_weight=3,
                priority_weight=1,
                priority_max_wait_seconds=600,
            )
            queue = db.get(Queue, queue.id)

        assert queue is not None
        queue.kiosk_enabled = True
        queue.kiosk_token = settings.default_kiosk_token
        queue.department_display_name = "Açougue"
        db.add(queue)

        admin = db.scalar(select(User).where(User.email == settings.default_admin_email))
        if not admin:
            admin = User(
                email=settings.default_admin_email,
                full_name="Administrador",
                hashed_password=hash_password(settings.default_admin_password),
                role="admin",
                company_id=company.id,
                store_id=store.id,
            )
            db.add(admin)

        operator = db.scalar(select(User).where(User.email == "operator@real.local"))
        if not operator:
            operator = User(
                email="operator@real.local",
                full_name="Operador Açougue",
                hashed_password=hash_password("operator123"),
                role="operator",
                company_id=company.id,
                store_id=store.id,
            )
            db.add(operator)

        for code, name in (("ACOU-1", "Balcão 1"), ("ACOU-2", "Balcão 2")):
            existing = db.scalar(
                select(Terminal).where(Terminal.department_id == dept.id, Terminal.code == code)
            )
            if not existing:
                db.add(Terminal(department_id=dept.id, code=code, name=name))

        displays = [
            ("TV-ACOU-1", "TV Açougue 1", "display-acougue-audio", True),
            ("TV-ACOU-2", "TV Açougue 2", "display-acougue-silent", False),
        ]
        for code, name, token, audio in displays:
            existing = db.scalar(select(Display).where(Display.token == token))
            if not existing:
                db.add(
                    Display(
                        store_id=store.id,
                        department_id=dept.id,
                        queue_id=queue.id,
                        name=name,
                        code=code,
                        token=token,
                        audio_enabled=audio,
                        audio_template="Senha {number}. Favor dirigir-se ao {department}.",
                    )
                )

        db.commit()

        demo_media = db.scalar(
            select(MediaAsset).where(MediaAsset.store_id == store.id, MediaAsset.name == "Promo Açougue Demo")
        )
        if not demo_media:
            svg = (
                b'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">'
                b'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
                b'<stop offset="0%" stop-color="#1f6b4a"/><stop offset="100%" stop-color="#0b2e22"/>'
                b"</linearGradient></defs>"
                b'<rect width="1280" height="720" fill="url(#g)"/>'
                b'<text x="640" y="320" fill="#fff" font-size="72" text-anchor="middle" '
                b'font-family="Georgia, serif">REAL</text>'
                b'<text x="640" y="400" fill="#c8e6d8" font-size="36" text-anchor="middle" '
                b'font-family="sans-serif">Ofertas do A\xc3\xa7ougue</text>'
                b"</svg>"
            )
            SignageService(db).create_upload(
                store_id=store.id,
                name="Promo Açougue Demo",
                filename="promo-acougue.svg",
                content_type="image/svg+xml",
                content=svg,
                duration_seconds=12,
                notes="Seed Sprint 7",
            )
            demo_media = db.scalar(
                select(MediaAsset).where(MediaAsset.store_id == store.id, MediaAsset.name == "Promo Açougue Demo")
            )

        pl_svc = PlaylistService(db)
        default_pl = db.scalar(
            select(Playlist).where(Playlist.store_id == store.id, Playlist.name == "Playlist Açougue")
        )
        if not default_pl:
            created = pl_svc.create(
                store_id=store.id,
                name="Playlist Açougue",
                description="Seed Sprint 8",
                is_default=True,
            )
            default_pl = db.get(Playlist, created["id"])
            if demo_media and default_pl:
                pl_svc.add_item(default_pl.id, asset_id=demo_media.id, duration_seconds=12)

        if default_pl:
            for token in ("display-acougue-audio", "display-acougue-silent"):
                d = db.scalar(select(Display).where(Display.token == token))
                if d and not d.playlist_id:
                    d.playlist_id = default_pl.id
                    db.add(d)
            db.commit()

        sch_svc = ScheduleService(db)
        channel = db.scalar(select(Channel).where(Channel.store_id == store.id, Channel.name == "Canal Açougue"))
        if not channel and default_pl:
            created_ch = sch_svc.create_channel(
                store_id=store.id,
                name="Canal Açougue",
                default_playlist_id=default_pl.id,
            )
            channel = db.get(Channel, created_ch["id"])
            if channel:
                sch_svc.create_group(store_id=store.id, channel_id=channel.id, name="TVs Açougue")
                sch_svc.create_schedule(
                    channel_id=channel.id,
                    playlist_id=default_pl.id,
                    name="Horário comercial",
                    start_time="08:00",
                    end_time="21:00",
                    days_of_week=[0, 1, 2, 3, 4, 5, 6],
                    priority="NORMAL",
                )
                for token in ("display-acougue-audio", "display-acougue-silent"):
                    d = db.scalar(select(Display).where(Display.token == token))
                    if d:
                        d.channel_id = channel.id
                        db.add(d)
                db.commit()

        # Sprint 10 — registry de devices para TVs seed
        dev_svc = DeviceService(db)
        for token in ("display-acougue-audio", "display-acougue-silent"):
            d = db.scalar(select(Display).where(Display.token == token))
            if d:
                device = dev_svc.ensure_for_display(d)
                print(f"  device={device.id} status={device.status} display={d.code}")

        t1 = db.scalar(select(Terminal).where(Terminal.department_id == dept.id, Terminal.code == "ACOU-1"))
        tv1 = db.scalar(select(Display).where(Display.token == "display-acougue-audio"))

        print("Seed OK")
        print(f"  admin: {settings.default_admin_email} / {settings.default_admin_password}")
        print("  operator: operator@real.local / operator123")
        print(f"  company={company.id}")
        print(f"  store={store.id}")
        print(f"  department={dept.id}")
        print(f"  queue={queue.id}")
        print(f"  kiosk_token={queue.kiosk_token}")
        print(f"  totem=/totem/{queue.id}?token={queue.kiosk_token}")
        if t1:
            print(f"  operator=/operator/{queue.id}?terminal={t1.id}")
        if tv1:
            print(f"  display=/display/{queue.id}?token={tv1.token}")
            print(f"  display_silent=/display/{queue.id}?token=display-acougue-silent")
    finally:
        db.close()


if __name__ == "__main__":
    main()
