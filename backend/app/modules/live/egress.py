"""LiveKit Egress — server-side recording (Phase 32).

Backend livekit-server'ning Egress API'siga (Twirp, http://livekit:7880) ulanadi;
livekit so'rovni redis orqali egress worker'ga uzatadi. Egress xonaga qo'shilib
(room composite, grid) yozadi va MinIO'ga (S3) yuklaydi. Tugagach livekit
webhook (`egress_ended`) yuboradi.

Browser recording (useLiveRecorder) fallback sifatida qoladi — bu modul
qo'shimcha "server yozuvi" rejimi.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _api_url() -> str:
    """LiveKit HTTP (Twirp) URL — ws://... dan http://... ga."""
    url = settings.LIVEKIT_URL_INTERNAL
    return url.replace("wss://", "https://").replace("ws://", "http://")


def _s3_endpoint() -> str:
    scheme = "https" if settings.MINIO_USE_SSL else "http"
    return f"{scheme}://{settings.MINIO_ENDPOINT}"


def _make_api():  # noqa: ANN201 — livekit api obyektini async ichida yaratish kerak
    from livekit import api

    return api.LiveKitAPI(
        _api_url(), settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET
    )


async def start_room_composite(room_name: str, object_key: str) -> str:
    """Xona yozuvini boshlaydi -> egress_id qaytaradi. MinIO'ga MP4 yuklanadi."""
    from livekit import api

    lk = _make_api()
    try:
        req = api.RoomCompositeEgressRequest(
            room_name=room_name,
            layout="grid",
            file_outputs=[
                api.EncodedFileOutput(
                    file_type=api.EncodedFileType.MP4,
                    filepath=object_key,
                    s3=api.S3Upload(
                        access_key=settings.MINIO_ACCESS_KEY,
                        secret=settings.MINIO_SECRET_KEY,
                        bucket=settings.MINIO_BUCKET,
                        endpoint=_s3_endpoint(),
                        region="us-east-1",
                        force_path_style=True,
                    ),
                )
            ],
        )
        info = await lk.egress.start_room_composite_egress(req)
        logger.info("egress.started", room=room_name, egress_id=info.egress_id)
        return info.egress_id
    finally:
        await lk.aclose()


async def stop(egress_id: str) -> None:
    from livekit import api

    lk = _make_api()
    try:
        await lk.egress.stop_egress(api.StopEgressRequest(egress_id=egress_id))
        logger.info("egress.stopped", egress_id=egress_id)
    finally:
        await lk.aclose()


async def list_active() -> list:
    """Faol egresslar — connectivity test uchun ham (read API)."""
    from livekit import api

    lk = _make_api()
    try:
        res = await lk.egress.list_egress(api.ListEgressRequest())
        return list(res.items)
    finally:
        await lk.aclose()
