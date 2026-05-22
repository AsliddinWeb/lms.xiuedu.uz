# 05. OTJBAT va TSDIN Integratsiyasi

## Maqsad

Davlat nazorat tizimlari bilan integratsiya:
- **OTJBAT** — Oliy Taʼlim Jarayonlarini Boshqarish Axborot Tizimi
- **TSDIN** — Taʼlim Sifatini nazorat qilish Davlat INspeksiyasi

## Normativ asos
- **VM 559-qaror Nizom 29-band:** "...OTJBAT va TSDIN bilan integratsiya majburiy"

## Integratsiyaning maqsadi

1. **Kontingent monitoringi** — talabalar soni, status
2. **Akademik faoliyat** — kurslar, baholar, davomat
3. **Pedagog yuklamasi** — 1:50 nisbati nazorati
4. **Imtihonlar** — yakuniy bahalar
5. **Hujjatlash** — sertifikatlar, diplomalar
6. **Audit** — barcha amallar logi

## OTJBAT bilan integratsiya

### Sinxronizatsiya

| Yo'nalish | Ma'lumot |
|-----------|----------|
| LMS → OTJBAT | Talabalar, baholar, davomat, sertifikatlar |
| OTJBAT → LMS | Akkreditatsiya holati, ruxsatlar |

### API endpoint'lar (taxminiy)

```
POST /otjbat/students         # talabalar push
POST /otjbat/grades           # baholar push
POST /otjbat/attendance       # davomat
POST /otjbat/certificates     # sertifikatlar
GET  /otjbat/accreditation    # OTM akkreditatsiya holati
```

### Implementatsiya

```python
# app/integrations/otjbat/client.py
import httpx
import hmac
import hashlib
import json
from datetime import datetime
from app.core.config import settings


class OtjbatClient:
    BASE_URL = settings.OTJBAT_BASE_URL
    
    def __init__(self, organization_id: int):
        creds = get_otjbat_credentials(organization_id)
        self.client_id = creds.client_id
        self.secret = creds.secret
    
    def _sign(self, payload: dict) -> str:
        message = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    async def push_students(self, students: list[dict]) -> dict:
        payload = {
            "client_id": self.client_id,
            "timestamp": int(datetime.utcnow().timestamp()),
            "data": students,
        }
        signature = self._sign(payload)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/api/v1/students",
                json=payload,
                headers={"X-Signature": signature},
            )
            return response.json()
    
    async def push_grades(self, grades: list[dict]) -> dict:
        # ... shunga o'xshash
        ...
```

## TSDIN bilan integratsiya

### Asosiy farq
TSDIN faqat **read-only** dostupga ega. Ya'ni biz TSDIN'ga ma'lumot **uzatib turamiz**, TSDIN faqat o'qiydi.

### Yetkaziladigan ma'lumotlar

| Kategoriya | Ma'lumot |
|------------|---------|
| **Kontingent** | Talabalar soni, statusi, demografiya |
| **Yo'nalishlar** | Mutaxassisliklar, kvotalar |
| **1:50 nisbati** | Pedagog/talaba nisbati real-time |
| **300/30 kvotalari** | Bakalavriat va magistratura |
| **Akademik o'zlashtirish** | O'rtacha baho, davomat |
| **Imtihonlar** | Statistik natija |
| **Hujjatlash to'liqligi** | EOʻMM, kontrakt, audit |

### TSDIN dashboard

TSDIN inspektoriga maxsus rol:
- Barcha OTMlarni ko'ra oladi (read-only)
- Hech qanday ma'lumotni o'zgartira olmaydi
- Audit logiga to'liq kira oladi
- Hisobotlarni eksport qila oladi

```python
# app/api/v1/tsdin.py
from app.core.deps import require_permission

router = APIRouter(prefix="/tsdin", tags=["tsdin"])

@router.get("/dashboard")
async def tsdin_dashboard(
    user: User = Depends(require_permission("monitoring.read.dashboard")),
):
    """TSDIN nazoratchi dashboard'i"""
    return {
        "total_organizations": await count_organizations(),
        "total_students": await count_students(),
        "violations": await get_violations(),
        "compliance_summary": await get_compliance_summary(),
    }


@router.get("/organizations/{org_id}/compliance")
async def org_compliance(
    org_id: int,
    user: User = Depends(require_permission("monitoring.read.compliance")),
):
    """OTM bo'yicha compliance hisoboti"""
    return {
        "teacher_ratio": await check_teacher_ratio(org_id),
        "student_quotas": await check_all_quotas(org_id),
        "exam_compliance": await check_exam_compliance(org_id),
        "documentation": await check_documentation(org_id),
    }


@router.get("/audit-logs")
async def tsdin_audit_logs(
    organization_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    user: User = Depends(require_permission("audit.read.all")),
):
    """Audit logini ko'rish"""
    return await get_audit_logs(
        organization_id=organization_id,
        from_date=from_date,
        to_date=to_date,
    )
```

### Real-time TSDIN feed

WebSocket orqali TSDIN'ga real-time hodisalarni yuborish:

```python
# app/integrations/tsdin/feed.py

@celery_app.task
def push_tsdin_event(event_type: str, data: dict):
    """Muhim hodisalarni TSDIN'ga real-time yuborish"""
    
    # Push faqat muhim hodisalar uchun
    important_events = [
        "student.expelled",
        "student.enrolled",
        "exam.completed",
        "compliance.violation",
    ]
    
    if event_type not in important_events:
        return
    
    client = TsdinClient()
    client.push_event({
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
    })
```

## Audit log (TSDIN uchun)

Bizning tizimda har bir muhim harakat audit log'da yoziladi va TSDIN ko'ra oladi:

```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    
    -- Kim
    user_id BIGINT REFERENCES users(id),
    user_role VARCHAR(50),
    user_ip INET,
    user_agent TEXT,
    
    -- Nima
    action VARCHAR(100) NOT NULL,             -- 'login', 'grade_changed', 'student_expelled'
    resource_type VARCHAR(50),
    resource_id BIGINT,
    
    -- Kontekst
    organization_id BIGINT REFERENCES organizations(id),
    
    -- Eski va yangi qiymatlar
    old_values JSONB,
    new_values JSONB,
    
    -- Metadata
    metadata JSONB,
    
    -- Vaqt
    created_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Har oyga partition
CREATE TABLE audit_logs_2026_05 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_org ON audit_logs(organization_id, created_at DESC);
```

### Audit middleware

```python
# app/core/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Faqat write operatsiyalar
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            user = getattr(request.state, "user", None)
            if user:
                # Background task'ga
                from app.workers.audit import log_action
                log_action.delay(
                    user_id=user.id,
                    action=f"{request.method} {request.url.path}",
                    ip=request.client.host,
                    user_agent=request.headers.get("user-agent"),
                    organization_id=user.tenant_id,
                )
        
        return response
```

## Kompliyans hisoboti

```python
# app/modules/compliance/service.py

async def generate_compliance_report(organization_id: int) -> dict:
    """OTM bo'yicha to'liq compliance hisoboti"""
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "organization_id": organization_id,
        
        # 1:50 nisbat
        "teacher_ratio": await check_teacher_ratio(organization_id),
        
        # Kvotalar
        "specialty_quotas": await check_all_specialty_quotas(organization_id),
        
        # Imtihonlar
        "exam_compliance": {
            "with_proctoring": await count_exams_with_proctoring(organization_id),
            "without_proctoring": await count_exams_without_proctoring(organization_id),
            "compliance_percent": await calc_proctoring_percent(organization_id),
        },
        
        # EOʻMM
        "course_documentation": {
            "total_courses": await count_courses(organization_id),
            "with_eomm": await count_courses_with_eomm(organization_id),
            "ozdst_compliant": await count_courses_ozdst_compliant(organization_id),
        },
        
        # Server muvofiqligi
        "infrastructure": {
            "server_in_country": True,           # konfiguratsiyadan
            "data_residency": "Uzbekistan",
        },
        
        # Auditing
        "audit": {
            "logs_retention_days": 365 * 5,      # 5 yil
            "logs_count": await count_audit_logs(organization_id),
        },
    }
```

## Acceptance kriteriyalar

- [ ] OTJBAT API client
- [ ] OTJBAT'ga talabalar push
- [ ] OTJBAT'ga baholar push
- [ ] TSDIN nazoratchi roli
- [ ] TSDIN dashboard
- [ ] Compliance hisobot
- [ ] Audit logi (5 yil saqlash)
- [ ] Real-time event feed
- [ ] WebSocket TSDIN ko'rinishi
- [ ] Imzo tekshiruvi
- [ ] Test coverage ≥ 75%
