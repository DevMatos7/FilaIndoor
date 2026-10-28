from app.core.config import get_settings
from app.modules.toledo.providers.base import NativeQueueProvider, ToledoBridge
from app.modules.toledo.providers.toledo import ToledoProvider


def build_toledo_provider(*, confirmed: dict[str, bool] | None = None) -> ToledoProvider:
    settings = get_settings()
    return ToledoProvider(
        enabled=bool(settings.toledo_enabled),
        mode=settings.toledo_mode,
        base_url=settings.toledo_api_base_url or None,
        api_key=settings.toledo_api_key or None,
        mock=bool(settings.toledo_mock),
        confirmed=confirmed,
    )


def build_native_provider() -> NativeQueueProvider:
    return NativeQueueProvider()


__all__ = [
    "NativeQueueProvider",
    "ToledoBridge",
    "ToledoProvider",
    "build_toledo_provider",
    "build_native_provider",
]
