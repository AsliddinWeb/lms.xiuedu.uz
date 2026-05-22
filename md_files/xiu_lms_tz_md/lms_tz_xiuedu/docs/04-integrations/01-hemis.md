# 01. HEMIS Integratsiyasi

## Maqsad

HEMIS (Higher Education Management Information System) — O'zbekiston oliy ta'lim tizimini boshqaruvchi davlat axborot tizimi. Bizning LMS u bilan ikki tomonlama sinxronizatsiya qiladi.

## Normativ asos
- **VM 559-qaror Nizom 29-band:** OTJBAT/TSDIN bilan integratsiya majburiy
- HEMIS — talabalar, pedagoglar, ta'lim yo'nalishlarining yagona manbai

## Sinxronizatsiya yo'nalishi

### HEMISdan keladigan (Read)
- OTM tashkilot tuzilmasi
- Fakultet, kafedra
- Yo'nalish va mutaxassisliklar (DTS kodlari bilan)
- O'quv rejalari (curriculum)
- Pedagog ma'lumotlari
- Talabalar bazasi (an'anaviy)
- Akademik kalendar

### LMSdan Hemisga yuboriladigan (Write)
- Masofaviy ta'lim talabalari
- Imtihon natijalari (yakuniy baho)
- Davomat ma'lumotlari
- Sertifikatlar / diploma asosi
- Akademik holat o'zgarishlari (chetlashtirish, ta'tilga chiqish)

## Texnik tafsilotlar

### Authentifikatsiya
- API Key + secret pair (HEMIS administratoridan)
- HMAC-SHA256 imzo har request'da
- IP whitelist (HEMIS panelida)
- HTTPS majburiy

### API endpoint
- Base URL: `https://student.hemis.uz/rest/v1` (yoki shunga o'xshash, har OTM uchun)
- Format: JSON
- Pagination: cursor-based

## Sync strategiyasi

### Full sync
- Har kuni soat 02:00'da
- Barcha ma'lumotlar yangilanadi
- Celery beat schedule

### Incremental sync
- Har 15 daqiqada
- Faqat o'zgargan yozuvlar (`updated_since` parametri)
- Webhook qabul qilish (HEMIS o'zgarsa, bizga xabar yuboradi)

### Real-time hodisalar
- Talaba qo'shilganda → bizga webhook
- Talaba chetlashtirilsa → biz Hemisga xabar yuboramiz

## Implementatsiya

### Hemis client

```python
# app/integrations/hemis/client.py
import httpx
import hashlib
import hmac
import time
from app.core.config import settings

class HemisClient:
    def __init__(self, otm_id: int):
        self.otm_id = otm_id
        creds = self._get_credentials(otm_id)
        self.api_key = creds.api_key
        self.secret = creds.secret
        self.base_url = creds.base_url
    
    def _sign_request(self, method: str, path: str, body: str = "") -> dict:
        timestamp = str(int(time.time()))
        message = f"{method}{path}{timestamp}{body}"
        signature = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "X-API-Key": self.api_key,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }
    
    async def get_students(
        self, 
        page: int = 1, 
        per_page: int = 100,
        updated_since: str | None = None,
    ) -> dict:
        path = f"/students?page={page}&per_page={per_page}"
        if updated_since:
            path += f"&updated_since={updated_since}"
        
        headers = self._sign_request("GET", path)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{path}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_organization(self) -> dict:
        path = "/organization"
        headers = self._sign_request("GET", path)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{path}",
                headers=headers,
            )
            return response.json()
    
    async def get_specialties(self) -> list[dict]:
        path = "/specialties"
        headers = self._sign_request("GET", path)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{path}",
                headers=headers,
            )
            return response.json()["data"]
    
    async def get_curricula(self, specialty_id: int) -> list[dict]:
        path = f"/specialties/{specialty_id}/curricula"
        headers = self._sign_request("GET", path)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{path}",
                headers=headers,
            )
            return response.json()["data"]
    
    async def push_exam_results(
        self, 
        student_id: str, 
        results: list[dict]
    ) -> dict:
        """Imtihon natijalarini Hemisga yuborish"""
        path = f"/students/{student_id}/exam-results"
        body = json.dumps(results)
        headers = {
            **self._sign_request("POST", path, body),
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{path}",
                content=body,
                headers=headers,
            )
            return response.json()
```

### Sync workers

```python
# app/workers/hemis_sync.py
from celery import Task
from app.integrations.hemis.client import HemisClient

@celery_app.task(bind=True, max_retries=3)
def sync_organization(self, otm_id: int):
    """OTM tashkilot ma'lumotlarini sync qilish"""
    try:
        client = HemisClient(otm_id)
        data = await client.get_organization()
        
        await update_organization_from_hemis(otm_id, data)
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def sync_students(self, otm_id: int, full: bool = False):
    """Talabalar ro'yxatini sync"""
    client = HemisClient(otm_id)
    
    last_sync = await get_last_sync(otm_id, "students")
    updated_since = None if full else last_sync.isoformat()
    
    page = 1
    while True:
        data = await client.get_students(page=page, updated_since=updated_since)
        
        for student_data in data["data"]:
            await sync_student(student_data, otm_id)
        
        if not data.get("has_next"):
            break
        page += 1
    
    await save_last_sync(otm_id, "students")


async def sync_student(data: dict, otm_id: int):
    """Bitta talaba ma'lumotini sync qilish"""
    # Hemis ID orqali topish
    student = await find_student_by_hemis_id(data["hemis_id"])
    
    if student:
        # Update
        student.full_name = data["full_name"]
        student.status = map_status(data["status"])
        student.current_semester = data["semester"]
        # ... boshqalar
        await save(student)
    else:
        # Create (an'anaviy talabalarni ham qo'shamiz, lekin "external" bayrog'i bilan)
        await create_student(
            hemis_id=data["hemis_id"],
            full_name=data["full_name"],
            organization_id=otm_id,
            specialty_id=await map_specialty(data["specialty_hemis_id"]),
            is_distance=data.get("is_distance", False),
            is_external=not data.get("is_distance", False),  # an'anaviy
        )


@celery_app.task
def push_exam_results_to_hemis(exam_attempt_id: int):
    """Imtihon natijasini Hemisga yuborish"""
    attempt = await get_exam_attempt(exam_attempt_id)
    
    if not attempt.user.student.hemis_id:
        return  # Hemisda yo'q (mahalliy talaba)
    
    client = HemisClient(attempt.user.student.organization_id)
    
    await client.push_exam_results(
        student_id=attempt.user.student.hemis_id,
        results=[{
            "subject_hemis_id": attempt.exam.course.subject.hemis_id,
            "score": float(attempt.total_score),
            "grade": attempt.grade_letter,
            "exam_date": attempt.submitted_at.isoformat(),
            "exam_type": attempt.exam.type,
        }],
    )
```

### Celery beat schedule

```python
# app/core/celery_app.py
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'hemis-full-sync-daily': {
        'task': 'app.workers.hemis_sync.full_sync_all_otms',
        'schedule': crontab(hour=2, minute=0),  # Har kuni 02:00
    },
    'hemis-incremental-sync': {
        'task': 'app.workers.hemis_sync.incremental_sync_all_otms',
        'schedule': crontab(minute='*/15'),  # Har 15 daqiqada
    },
}
```

## Webhook qabul qilish

Hemis bizga muhim hodisalar bo'lganda xabar yuborishi mumkin:

```python
# app/api/v1/webhooks.py

@router.post("/hemis")
async def hemis_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hemis-Signature")
    
    # Imzo tekshiruvi
    expected = hmac.new(
        settings.HEMIS_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(401, "Invalid signature")
    
    payload = await request.json()
    event = payload.get("event")
    
    # Background'da qayta ishlash
    if event == "student.created":
        await handle_student_created(payload["data"])
    elif event == "student.updated":
        await handle_student_updated(payload["data"])
    elif event == "specialty.updated":
        await handle_specialty_updated(payload["data"])
    
    return {"status": "ok"}
```

## Mapping (Hemis ↔ LMS)

### Status mapping
```python
HEMIS_STATUS_MAP = {
    "active": "active",
    "academic_leave": "on_leave",
    "expelled": "expelled",
    "graduated": "graduated",
    "transferred": "transferred_out",
}
```

### Education form mapping
```python
EDUCATION_FORM_MAP = {
    "1": "fulltime",     # Kunduzgi
    "2": "evening",      # Kechki
    "3": "parttime",     # Sirtqi
    "4": "distance",     # Masofaviy ← bizning fokus
}
```

## Conflict resolution

Agar Hemis va bizdagi ma'lumot mos kelmasa:

1. **Hemis-only fields** (PINFL, pasport, akademik yo'nalish) — Hemis g'olib
2. **LMS-only fields** (avtoproktoring, content progress) — LMS g'olib
3. **Conflicting fields** (status) — Hemis g'olib + audit log
4. **Yangi yozuv** — har ikkala tomonda yaratish

## Database o'zgarishlari

```sql
-- Hemis ID'lar (har OTM uchun creds)
CREATE TABLE hemis_credentials (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT UNIQUE REFERENCES organizations(id),
    base_url TEXT NOT NULL,
    api_key VARCHAR(255) NOT NULL,
    secret VARCHAR(255) NOT NULL,                  -- shifrlangan
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sync history
CREATE TABLE hemis_sync_log (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT REFERENCES organizations(id),
    sync_type VARCHAR(50),                         -- 'full', 'incremental'
    entity_type VARCHAR(50),                       -- 'students', 'specialties'
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status VARCHAR(20),                            -- 'success', 'failed', 'partial'
    records_synced INT DEFAULT 0,
    errors JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Foydalanuvchilarga Hemis ID qo'shish
ALTER TABLE students ADD COLUMN hemis_id VARCHAR(50);
ALTER TABLE users ADD COLUMN hemis_id VARCHAR(50);
ALTER TABLE specialties ADD COLUMN hemis_id VARCHAR(50);
ALTER TABLE subjects ADD COLUMN hemis_id VARCHAR(50);
ALTER TABLE curricula ADD COLUMN hemis_id VARCHAR(50);

CREATE INDEX idx_students_hemis ON students(hemis_id);
CREATE INDEX idx_specialties_hemis ON specialties(hemis_id);
```

## Acceptance kriteriyalar

- [ ] HemisClient implementatsiya
- [ ] Full sync (kunlik)
- [ ] Incremental sync (15 daqiqa)
- [ ] Webhook qabul qilish
- [ ] Imzo (HMAC) tekshiruvi
- [ ] Conflict resolution logikasi
- [ ] Imtihon natijalarini push qilish
- [ ] Status o'zgarishlarini bidirectional sync
- [ ] Sync log
- [ ] Retry mexanizmi (xatolar)
- [ ] Monitoring va alertlar
- [ ] Test coverage ≥ 80%
