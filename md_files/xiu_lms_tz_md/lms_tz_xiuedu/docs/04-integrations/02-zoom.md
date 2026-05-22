# 02. Zoom Integratsiyasi

## Maqsad

Zoom platformasi orqali sinxron live darslarni o'tkazish va boshqarish. Server-to-Server OAuth, webhooks, recordings.

## Funksional talablar

- Avtomatik meeting yaratish
- Talabalarni qo'shish (registrants)
- Avtomatik join URL yaratish
- Recording'ni qabul qilish
- Davomatni avtomatik kuzatish
- Cloud recording'larni MinIO'ga ko'chirish

## Zoom hisob va sozlash

### 1. Zoom akkaunt
- **Pro plan** yoki yuqorisi (cloud recording uchun)
- **Server-to-Server OAuth app** yaratish (Zoom App Marketplace'da)
- Permissions:
  - `meeting:read:admin`
  - `meeting:write:admin`
  - `recording:read:admin`
  - `user:read:admin`

### 2. Webhook events (sozlash)
- `meeting.started`
- `meeting.ended`
- `meeting.participant_joined`
- `meeting.participant_left`
- `recording.completed`
- `recording.transcript_completed`

### 3. Maxfiy ma'lumotlar (.env)

```env
ZOOM_ACCOUNT_ID=xxx
ZOOM_CLIENT_ID=xxx
ZOOM_CLIENT_SECRET=xxx
ZOOM_WEBHOOK_SECRET_TOKEN=xxx
```

## Zoom client implementatsiyasi

```python
# app/integrations/zoom/client.py
import httpx
from datetime import datetime, timedelta
from app.core.config import settings


class ZoomClient:
    BASE_URL = "https://api.zoom.us/v2"
    OAUTH_URL = "https://zoom.us/oauth/token"
    
    def __init__(self):
        self.account_id = settings.ZOOM_ACCOUNT_ID
        self.client_id = settings.ZOOM_CLIENT_ID
        self.client_secret = settings.ZOOM_CLIENT_SECRET
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
    
    async def get_access_token(self) -> str:
        """Server-to-Server OAuth token olish"""
        if self._token and self._token_expires_at and datetime.utcnow() < self._token_expires_at:
            return self._token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_URL,
                data={
                    "grant_type": "account_credentials",
                    "account_id": self.account_id,
                },
                auth=(self.client_id, self.client_secret),
            )
            response.raise_for_status()
            data = response.json()
            
            self._token = data["access_token"]
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"] - 60)
            
            return self._token
    
    async def _request(self, method: str, path: str, **kwargs):
        token = await self.get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.BASE_URL}{path}",
                headers={"Authorization": f"Bearer {token}"},
                **kwargs,
            )
            response.raise_for_status()
            return response.json() if response.content else {}
    
    # === Users ===
    async def get_user(self, email: str) -> dict:
        return await self._request("GET", f"/users/{email}")
    
    async def create_user(self, email: str, first_name: str, last_name: str) -> dict:
        return await self._request("POST", "/users", json={
            "action": "create",
            "user_info": {
                "email": email,
                "type": 1,  # Basic
                "first_name": first_name,
                "last_name": last_name,
            },
        })
    
    # === Meetings ===
    async def create_meeting(
        self,
        host_email: str,
        topic: str,
        start_time: datetime,
        duration_minutes: int,
        agenda: str = "",
        password: str | None = None,
    ) -> dict:
        """Meeting yaratish"""
        return await self._request(
            "POST",
            f"/users/{host_email}/meetings",
            json={
                "topic": topic,
                "type": 2,  # 2 = scheduled meeting
                "start_time": start_time.isoformat() + "Z",
                "duration": duration_minutes,
                "timezone": "Asia/Tashkent",
                "agenda": agenda,
                "password": password,
                "settings": {
                    "host_video": True,
                    "participant_video": False,
                    "join_before_host": False,
                    "mute_upon_entry": True,
                    "watermark": False,
                    "use_pmi": False,
                    "approval_type": 0,  # automatically approve
                    "audio": "both",
                    "auto_recording": "cloud",
                    "waiting_room": True,
                    "registrants_email_notification": False,
                    "meeting_authentication": False,
                },
            },
        )
    
    async def update_meeting(self, meeting_id: int, data: dict) -> dict:
        return await self._request("PATCH", f"/meetings/{meeting_id}", json=data)
    
    async def delete_meeting(self, meeting_id: int) -> dict:
        return await self._request("DELETE", f"/meetings/{meeting_id}")
    
    async def get_meeting(self, meeting_id: int) -> dict:
        return await self._request("GET", f"/meetings/{meeting_id}")
    
    # === Registrants ===
    async def add_registrant(
        self,
        meeting_id: int,
        email: str,
        first_name: str,
        last_name: str,
    ) -> dict:
        """Talabani meetingga qo'shish — natijada unique join URL keladi"""
        return await self._request(
            "POST",
            f"/meetings/{meeting_id}/registrants",
            json={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            },
        )
    
    # === Recordings ===
    async def get_meeting_recordings(self, meeting_id: int) -> dict:
        return await self._request("GET", f"/meetings/{meeting_id}/recordings")
    
    async def download_recording(self, download_url: str) -> bytes:
        """Recording'ni yuklab olish"""
        token = await self.get_access_token()
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.get(
                download_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            return response.content
    
    # === Participants ===
    async def get_participants(self, meeting_uuid: str) -> dict:
        """Tugagan meeting ishtirokchilari"""
        return await self._request(
            "GET",
            f"/past_meetings/{meeting_uuid}/participants?page_size=300"
        )
```

## Live session yaratish (service)

```python
# app/modules/live/service.py

class LiveService:
    def __init__(self, repo, zoom: ZoomClient):
        self.repo = repo
        self.zoom = zoom
    
    async def create_live_session(
        self, 
        course_id: int, 
        host_id: int,
        title: str,
        scheduled_start: datetime,
        duration_minutes: int,
    ) -> LiveSession:
        host = await get_user(host_id)
        course = await get_course(course_id)
        
        # 1. Zoom user mavjudligini tekshirish (yoki yaratish)
        try:
            await self.zoom.get_user(host.email)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Foydalanuvchi yo'q — yaratish
                await self.zoom.create_user(
                    email=host.email,
                    first_name=host.full_name.split()[0],
                    last_name=" ".join(host.full_name.split()[1:]),
                )
            else:
                raise
        
        # 2. Meetingni yaratish
        meeting = await self.zoom.create_meeting(
            host_email=host.email,
            topic=title,
            start_time=scheduled_start,
            duration_minutes=duration_minutes,
            agenda=f"Course: {course.title}",
        )
        
        # 3. DB'ga saqlash
        session = await self.repo.create(
            course_id=course_id,
            host_id=host_id,
            title=title,
            provider="zoom",
            provider_meeting_id=str(meeting["id"]),
            provider_join_url=meeting["join_url"],
            provider_host_url=meeting["start_url"],
            provider_password=meeting.get("password"),
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_start + timedelta(minutes=duration_minutes),
        )
        
        # 4. Talabalarni registrant sifatida qo'shish (Celery)
        from app.workers.live import register_students
        register_students.delay(session.id)
        
        return session
    
    async def get_join_url(self, session_id: int, user_id: int) -> str:
        """Talaba uchun unique join URL"""
        session = await self.repo.get(session_id)
        user = await get_user(user_id)
        
        # Registrant qo'shish (agar oldindan qilinmagan bo'lsa)
        result = await self.zoom.add_registrant(
            meeting_id=int(session.provider_meeting_id),
            email=user.email,
            first_name=user.full_name.split()[0],
            last_name=" ".join(user.full_name.split()[1:]),
        )
        
        return result["join_url"]  # bu unique URL


@celery_app.task
async def register_students(session_id: int):
    """Kursning barcha talabalarini Zoom registrant qilish"""
    session = await get_session(session_id)
    students = await get_course_students(session.course_id)
    
    zoom = ZoomClient()
    for student in students:
        try:
            await zoom.add_registrant(
                meeting_id=int(session.provider_meeting_id),
                email=student.email,
                first_name=student.full_name.split()[0],
                last_name=" ".join(student.full_name.split()[1:]),
            )
        except Exception as e:
            # Log va davom etish
            logger.error(f"Failed to register {student.email}: {e}")
```

## Webhook handler

```python
# app/api/v1/webhooks.py
import hmac
import hashlib
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException

@router.post("/zoom")
async def zoom_webhook(request: Request, background: BackgroundTasks):
    body = await request.body()
    
    # 1. URL validation (Zoom dastlabki tekshiruv)
    payload = json.loads(body)
    if payload.get("event") == "endpoint.url_validation":
        plain_token = payload["payload"]["plainToken"]
        encrypted_token = hmac.new(
            settings.ZOOM_WEBHOOK_SECRET_TOKEN.encode(),
            plain_token.encode(),
            hashlib.sha256
        ).hexdigest()
        return {
            "plainToken": plain_token,
            "encryptedToken": encrypted_token,
        }
    
    # 2. Imzo tekshiruvi
    timestamp = request.headers.get("x-zm-request-timestamp")
    signature_header = request.headers.get("x-zm-signature")
    
    message = f"v0:{timestamp}:{body.decode()}"
    expected_signature = "v0=" + hmac.new(
        settings.ZOOM_WEBHOOK_SECRET_TOKEN.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature_header, expected_signature):
        raise HTTPException(401, "Invalid signature")
    
    # 3. Eventni qayta ishlash (background)
    background.add_task(process_zoom_event, payload)
    
    return {"status": "ok"}


async def process_zoom_event(payload: dict):
    event = payload["event"]
    obj = payload["payload"]["object"]
    
    if event == "meeting.started":
        await handle_meeting_started(obj)
    elif event == "meeting.ended":
        await handle_meeting_ended(obj)
    elif event == "meeting.participant_joined":
        await handle_participant_joined(obj)
    elif event == "meeting.participant_left":
        await handle_participant_left(obj)
    elif event == "recording.completed":
        await handle_recording_completed(obj)


async def handle_meeting_started(obj: dict):
    meeting_id = obj["id"]
    session = await find_session_by_meeting_id(str(meeting_id))
    if session:
        session.status = "live"
        session.actual_start = datetime.utcnow()
        await save(session)


async def handle_meeting_ended(obj: dict):
    meeting_id = obj["id"]
    session = await find_session_by_meeting_id(str(meeting_id))
    if session:
        session.status = "ended"
        session.actual_end = datetime.utcnow()
        await save(session)
        
        # Davomatni hisoblash
        from app.workers.live import calculate_attendance
        calculate_attendance.delay(session.id)


async def handle_participant_joined(obj: dict):
    meeting_id = obj["id"]
    participant = obj["participant"]
    
    session = await find_session_by_meeting_id(str(meeting_id))
    user = await find_user_by_email(participant["user_email"])
    
    if session and user:
        attendance = await get_or_create_attendance(session.id, user.id)
        attendance.joined_at = parse_zoom_time(participant["join_time"])
        attendance.join_count += 1
        attendance.provider_user_id = participant["user_id"]
        await save(attendance)


async def handle_participant_left(obj: dict):
    meeting_id = obj["id"]
    participant = obj["participant"]
    
    session = await find_session_by_meeting_id(str(meeting_id))
    user = await find_user_by_email(participant["user_email"])
    
    if session and user:
        attendance = await get_attendance(session.id, user.id)
        if attendance:
            left_at = parse_zoom_time(participant["leave_time"])
            attendance.left_at = left_at
            
            # Qatnashgan vaqtini hisoblash
            session_duration = (left_at - attendance.joined_at).total_seconds()
            attendance.duration_seconds += int(session_duration)
            
            await save(attendance)


async def handle_recording_completed(obj: dict):
    """Cloud recording tayyor bo'lganda"""
    meeting_id = obj["id"]
    session = await find_session_by_meeting_id(str(meeting_id))
    
    if not session:
        return
    
    # Recording'ni MinIO'ga ko'chirish (Celery)
    from app.workers.live import import_zoom_recording
    
    for recording in obj["recording_files"]:
        if recording["file_type"] == "MP4":
            import_zoom_recording.delay(
                session_id=session.id,
                download_url=recording["download_url"],
                duration=recording.get("duration"),
            )
```

## Recording'ni MinIO'ga ko'chirish

```python
# app/workers/live.py

@celery_app.task(bind=True, max_retries=3)
def import_zoom_recording(self, session_id: int, download_url: str, duration: int = None):
    try:
        zoom = ZoomClient()
        
        # 1. Yuklab olish
        video_bytes = await zoom.download_recording(download_url)
        
        # 2. MinIO'ga yuklash
        from app.utils.storage import upload_to_minio
        path = f"recordings/{session_id}_{uuid4()}.mp4"
        url = await upload_to_minio(video_bytes, path)
        
        # 3. Sessiyaga biriktirish
        session = await get_session(session_id)
        session.recording_url = url
        session.recording_status = "ready"
        await save(session)
        
        # 4. Transkodlash (HLS)
        from app.workers.video import transcode_video
        transcode_video.delay(session.id, source_url=url)
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)
```

## Acceptance kriteriyalar

- [ ] Server-to-Server OAuth ishlaydi
- [ ] Meeting yaratish, tahrirlash, o'chirish
- [ ] Talabalarni registrant qilish
- [ ] Webhook qabul qilish va imzo tekshirish
- [ ] Davomatni avtomatik hisoblash
- [ ] Recording'ni MinIO'ga ko'chirish
- [ ] HLS transkodlash
- [ ] Recording'ga subtitr (Whisper)
- [ ] Xatolar bo'lsa retry
- [ ] Test coverage ≥ 75%
