# 08. Live Classes (Sinxron Darslar) Moduli

## Maqsad

Real vaqtda audio/video darslar o'tkazish. Zoom asosiy provayder, BigBlueButton/Jitsi alternativ. Avtomatik davomat, yozib olish, izohlash.

## Normativ asos
- **VM 559-qaror Nizom 21-band:** sinxron va asinxron rejimlar majburiy

## Funksional talablar

### 1. Live dars rejalashtirish

- O'qituvchi yangi dars yaratadi
- Sana, vaqt, davomiyligi
- Kurs/dars bilan bog'lash
- Talabalar avtomatik chaqiriladi
- Email/SMS/Push xabarnoma
- Kalendarga qo'shiladi

### 2. Provayderlar

| Provayder | Holati | Foydalanish |
|-----------|--------|-------------|
| **Zoom** | Asosiy | Ko'pchilik holatlar |
| **BigBlueButton** | Self-hosted alternativ | Maxsus | 
| **Jitsi Meet** | Self-hosted, yengil | Kichik darslar |

Tizim bir necha provayder bilan ishlay oladi (har bir OTM o'zi tanlaydi).

### 3. Dars o'tkazish

- O'qituvchi platforma ichidan kiradi (host)
- Talabalar — link yoki "Qo'shilish" tugmasi orqali
- Embedded ko'rinish (platforma ichida)
- Yoki yangi tab/oynada

### 4. Funksiyalar (Zoom orqali)

- Audio / video
- Ekran ulashish
- Whiteboard (interaktiv doska)
- Chat
- Q&A
- Polling (so'rov)
- Breakout rooms
- Reactions / hands-up
- Yozib olish (cloud yoki local)
- Live streaming (YouTube/Facebook)

### 5. Davomat (avtomatik)

- Talaba xonaga kirgan vaqt
- Chiqib ketgan vaqt
- Jami davomiyligi
- Minimum davomiyligi (75%) — davomat hisoblanishi uchun
- Statistika dashboard

### 6. Yozib olish (recording)

- Avtomatik yoki qo'lda
- Cloud'da saqlash (MinIO yoki Zoom Cloud)
- Avtomatik transkodlash (HLS)
- Dars sahifasiga avtomatik biriktirish
- Talaba qayta ko'ra oladi
- Subtitr (Whisper)

### 7. Live exam proctoring (kelajakda)

- Imtihon vaqtida live kuzatuv
- O'qituvchi ko'p talabani bir vaqtda kuzata oladi
- Tafsilotlar: [09-exams-proctoring.md](09-exams-proctoring.md)

### 8. Kalendar

- Talaba/o'qituvchi kalendari
- iCal eksport
- Google/Outlook bilan sync (ixtiyoriy)
- Reminderlar (15 min, 1 soat oldin)

## API Endpoints

```
# Live sessiyalar
GET    /api/v1/live-sessions                  # ro'yxat
POST   /api/v1/live-sessions                  # yaratish
GET    /api/v1/live-sessions/{id}
PATCH  /api/v1/live-sessions/{id}
DELETE /api/v1/live-sessions/{id}             # bekor qilish

POST   /api/v1/live-sessions/{id}/start       # darsni boshlash
POST   /api/v1/live-sessions/{id}/end         # darsni tugatish

# Qo'shilish
GET    /api/v1/live-sessions/{id}/join-info   # join URL, params
POST   /api/v1/live-sessions/{id}/join        # qo'shilganligini belgilash
POST   /api/v1/live-sessions/{id}/leave       # chiqib ketganligini belgilash

# Davomat
GET    /api/v1/live-sessions/{id}/attendance  # davomat ro'yxati
POST   /api/v1/live-sessions/{id}/attendance  # qo'lda belgilash

# Yozuvlar
GET    /api/v1/live-sessions/{id}/recordings
POST   /api/v1/live-sessions/{id}/recordings  # qo'lda yuklash

# Webhook (Zoom)
POST   /api/v1/webhooks/zoom                  # Zoom event'lar

# Kalendar
GET    /api/v1/calendar/my-sessions           # mening darslarim
GET    /api/v1/calendar/export.ics            # iCal eksport
```

## Database modellari

```sql
-- Live sessiya
CREATE TABLE live_sessions (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT REFERENCES courses(id) ON DELETE CASCADE,
    lesson_id BIGINT REFERENCES lessons(id),
    
    title VARCHAR(500) NOT NULL,
    description TEXT,
    
    provider VARCHAR(20) NOT NULL,                 -- 'zoom', 'bbb', 'jitsi'
    
    -- Provayder ma'lumotlari
    provider_meeting_id VARCHAR(100),
    provider_join_url TEXT,
    provider_host_url TEXT,
    provider_password VARCHAR(50),
    
    -- Vaqt
    scheduled_start TIMESTAMP NOT NULL,
    scheduled_end TIMESTAMP NOT NULL,
    actual_start TIMESTAMP,
    actual_end TIMESTAMP,
    
    -- Host
    host_id BIGINT REFERENCES users(id),
    
    -- Status
    status VARCHAR(20) DEFAULT 'scheduled',        -- 'scheduled', 'live', 'ended', 'cancelled'
    
    -- Sozlamalar
    settings JSONB DEFAULT '{}',                   -- waiting room, mute, etc.
    
    -- Yozib olish
    auto_record BOOLEAN DEFAULT TRUE,
    recording_url TEXT,
    recording_status VARCHAR(20),                  -- 'pending', 'processing', 'ready'
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Davomat
CREATE TABLE live_attendance (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT REFERENCES live_sessions(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id),
    
    joined_at TIMESTAMP,
    left_at TIMESTAMP,
    duration_seconds INT DEFAULT 0,
    
    -- Bir necha marta kirib chiqishi mumkin
    join_count INT DEFAULT 1,
    
    -- Status
    is_present BOOLEAN DEFAULT FALSE,              -- 75%+ vaqt qatnashgan
    attendance_method VARCHAR(20) DEFAULT 'auto',  -- 'auto', 'manual'
    marked_by BIGINT REFERENCES users(id),
    
    -- Provayder ma'lumotlari
    provider_user_id VARCHAR(100),
    
    UNIQUE(session_id, user_id)
);

-- Webhook hodisalari (audit)
CREATE TABLE live_webhook_events (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    session_id BIGINT REFERENCES live_sessions(id),
    payload JSONB,
    received_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP
);
```

## Zoom integratsiyasi (qisqa misol)

Tafsilotlar: [04-integrations/02-zoom.md](../04-integrations/02-zoom.md)

```python
# app/integrations/zoom/client.py
import httpx
from app.core.config import settings

class ZoomClient:
    def __init__(self):
        self.account_id = settings.ZOOM_ACCOUNT_ID
        self.client_id = settings.ZOOM_CLIENT_ID
        self.client_secret = settings.ZOOM_CLIENT_SECRET
        self._token = None
    
    async def get_access_token(self) -> str:
        """Server-to-Server OAuth"""
        if self._token and not self._is_expired():
            return self._token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://zoom.us/oauth/token",
                data={
                    "grant_type": "account_credentials",
                    "account_id": self.account_id,
                },
                auth=(self.client_id, self.client_secret),
            )
            data = response.json()
            self._token = data["access_token"]
            return self._token
    
    async def create_meeting(
        self,
        topic: str,
        start_time: datetime,
        duration_minutes: int,
        host_email: str,
    ) -> dict:
        token = await self.get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.zoom.us/v2/users/{host_email}/meetings",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "topic": topic,
                    "type": 2,  # Scheduled
                    "start_time": start_time.isoformat(),
                    "duration": duration_minutes,
                    "settings": {
                        "host_video": True,
                        "participant_video": False,
                        "waiting_room": True,
                        "auto_recording": "cloud",
                        "mute_upon_entry": True,
                    },
                },
            )
            return response.json()
```

## Webhook handler

```python
# app/api/v1/webhooks.py
from fastapi import APIRouter, Request, BackgroundTasks
import hmac, hashlib

router = APIRouter()

@router.post("/zoom")
async def zoom_webhook(request: Request, background: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("x-zm-signature")
    timestamp = request.headers.get("x-zm-request-timestamp")
    
    # Imzoni tekshirish
    if not _verify_zoom_signature(body, signature, timestamp):
        raise HTTPException(401, "Invalid signature")
    
    payload = await request.json()
    event = payload.get("event")
    
    # Background'da qayta ishlash
    background.add_task(process_zoom_event, event, payload)
    
    return {"status": "ok"}

async def process_zoom_event(event: str, payload: dict):
    if event == "meeting.participant_joined":
        await handle_participant_joined(payload)
    elif event == "meeting.participant_left":
        await handle_participant_left(payload)
    elif event == "meeting.ended":
        await handle_meeting_ended(payload)
    elif event == "recording.completed":
        await handle_recording_completed(payload)
```

## Davomat hisoblash

```python
async def calculate_attendance(session_id: int):
    """75%+ vaqt qatnashgan talaba "qatnashgan" deb belgilanadi"""
    session = await get_session(session_id)
    duration = (session.actual_end - session.actual_start).total_seconds()
    min_required = duration * 0.75
    
    attendances = await get_session_attendances(session_id)
    
    for att in attendances:
        att.is_present = att.duration_seconds >= min_required
        await save(att)
```

## Frontend — Live dars sahifasi

```vue
<!-- views/live/LiveSessionView.vue -->
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useLiveStore } from '@/stores/live'

const route = useRoute()
const live = useLiveStore()
const sessionId = Number(route.params.id)

const session = ref(null)
const joinUrl = ref('')

onMounted(async () => {
  session.value = await live.fetchSession(sessionId)
  const joinInfo = await live.getJoinInfo(sessionId)
  joinUrl.value = joinInfo.join_url
  
  // Tracking: qo'shilganligini bildirish
  await live.markJoined(sessionId)
})

onUnmounted(async () => {
  await live.markLeft(sessionId)
})

function joinInNewTab() {
  window.open(joinUrl.value, '_blank')
}
</script>

<template>
  <div v-if="session" class="container mx-auto p-6">
    <h1 class="text-2xl font-bold">{{ session.title }}</h1>
    <p class="text-gray-600">{{ session.scheduled_start | format }}</p>
    
    <!-- Embedded yoki tashqi link -->
    <div class="mt-6">
      <Button @click="joinInNewTab" size="lg">
        Darsga qo'shilish
      </Button>
    </div>
  </div>
</template>
```

## Acceptance kriteriyalar

- [ ] Live sessiya yaratish
- [ ] Zoom integratsiyasi (Server-to-Server OAuth)
- [ ] BigBlueButton alternativi
- [ ] Avtomatik davomat
- [ ] Yozib olish va saqlash
- [ ] Webhook qayta ishlash
- [ ] Email/SMS/Push xabarnomalar
- [ ] Kalendar va iCal
- [ ] Frontend dars sahifasi
- [ ] O'qituvchi paneli (davomat statistikasi)
- [ ] Test coverage ≥ 75%
