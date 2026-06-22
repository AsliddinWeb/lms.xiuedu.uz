"""LiveKit room admin — xonani o'chirish va ishtirokchi huquqlarini boshqarish.

`egress.py` bilan bir xil pattern (Twirp API, http://livekit:7880). Best-effort:
xato bo'lsa chaqiruvchi log qiladi, lekin asosiy oqim to'xtamaydi.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _api_url() -> str:
    url = settings.LIVEKIT_URL_INTERNAL
    return url.replace("wss://", "https://").replace("ws://", "http://")


def _make_api():  # noqa: ANN201
    from livekit import api

    return api.LiveKitAPI(
        _api_url(), settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET
    )


async def delete_room(room_name: str) -> None:
    """Xonani o'chiradi — barcha ishtirokchilar darhol uziladi.

    Host darsni yakunlaganda chaqiriladi: talabalar avtomatik chiqib ketadi
    (RoomEvent.Disconnected -> frontend 'tugadi' ekraniga o'tadi).
    """
    from livekit import api

    lk = _make_api()
    try:
        await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
        logger.info("room.deleted", room=room_name)
    finally:
        await lk.aclose()


async def set_screenshare_permission(
    room_name: str, identity: str, *, allow: bool
) -> None:
    """Ishtirokchiga ekran ulashish huquqini beradi/oladi (host boshqaradi).

    Talaba default `camera`+`microphone` bilan keladi; host ruxsat berganda
    `screen_share` qo'shiladi.
    """
    from livekit import api

    sources = [
        api.TrackSource.CAMERA,
        api.TrackSource.MICROPHONE,
    ]
    if allow:
        sources.append(api.TrackSource.SCREEN_SHARE)
        sources.append(api.TrackSource.SCREEN_SHARE_AUDIO)

    lk = _make_api()
    try:
        await lk.room.update_participant(
            api.UpdateParticipantRequest(
                room=room_name,
                identity=identity,
                permission=api.ParticipantPermission(
                    can_subscribe=True,
                    can_publish=True,
                    can_publish_data=True,
                    can_publish_sources=sources,
                ),
            )
        )
        logger.info(
            "room.screenshare_permission",
            room=room_name,
            identity=identity,
            allow=allow,
        )
    finally:
        await lk.aclose()
