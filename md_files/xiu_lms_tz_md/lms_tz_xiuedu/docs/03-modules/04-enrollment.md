# 04. Enrollment (Talabalarni Qabul Qilish) Moduli

## Maqsad

Masofaviy ta'limga talabalarni qabul qilish, kontingent boshqaruvi, ko'chirish, qayta tiklash va chetlashtirish jarayonlari.

## Normativ asos
- **VM 559-qaror, Nizom 12-band:** Qabul boshqa ta'lim shakllari uchun belgilangan tartibda
- **15-band:** Qabul parametrlari (bakalavriat — 300, magistratura — 30)
- **Nizom 21-band:** Talaba LMS'da ro'yxatdan o'tish uchun OTM'ga shaxsan tashrif buyurishi shart

## Funksional talablar

### 1. Onlayn ariza topshirish

**Bosqichlar:**
1. Ariza topshirish (formada barcha ma'lumotlar)
2. Hujjatlarni yuklash (pasport, attestat, sertifikatlar)
3. To'lov-kontrakt tasdiqlash
4. To'lov amalga oshirish (yoki qarz)
5. Akkaunt avtomatik yaratiladi
6. Talaba OTM'ga LMS'da ro'yxatdan o'tish uchun keladi

### 2. Qabul parametrlari (cheklovlari)

| Daraja | Maks. talaba |
|--------|--------------|
| Bakalavriat (1 yo'nalish) | 300 |
| Magistratura (1 mutaxassislik) | 30 |
| Xorijiy fuqarolar | hisobga olinmaydi |
| AKT yo'nalishlari | cheklov tatbiq etilmaydi |

Tizim avtomatik tekshiradi va parametr to'lganda yangi arizalarni qabul qilmaydi.

### 3. Talaba kontingent boshqaruvi

**Holatlar (status):**
- `applied` — ariza topshirilgan
- `accepted` — qabul qilingan
- `enrolled` — ro'yxatdan o'tgan
- `active` — faol o'qiyapti
- `on_leave` — akademik ta'tilda
- `transferred_in` — boshqa OTM'dan ko'chgan
- `transferred_out` — boshqa OTM'ga ko'chib ketgan
- `expelled` — chetlashtirilgan
- `graduated` — bitirgan
- `restored` — qayta tiklangan

### 4. Workflow'lar

#### Qabul flowi
```
Ariza → Tekshiruv → Kontrakt → To'lov → Akkaunt → OTM tashrifi → Faol
```

#### Ko'chirish (transfer)
- Boshqa OTMdan ko'chish
- Akademik farqlarni hisoblash
- Subject mapping
- Komissiya qarori

#### Qayta tiklash
- Akademik ta'tildan keyin
- Chetlashtirishdan keyin (5 yil ichida)

#### Chetlashtirish
- Akademik qarz (3+ fan)
- O'quvga kelmaslik (45 kun)
- Tartib buzish
- Shaxsiy iltimos

### 5. Buyruqlar (orders)

Har bir muhim harakat — buyruq sifatida shakllantiriladi:
- Qabul buyrug'i
- Ko'chirish buyrug'i
- Chetlashtirish buyrug'i
- Qayta tiklash buyrug'i
- Akademik ta'til buyrug'i

**Generatsiya:** PDF format, ERI bilan imzolanadi.

### 6. Guruhlar boshqaruvi

- Talabalarni guruhlarga avtomatik taqsimlash
- Guruh nomi (avtomatik): `<yo'nalish_kod>-<yil>-<son>` masalan: `5611200-26-01`
- Guruh chegarasi: 25 talaba (default)
- Pedagoglarni biriktirish

### 7. Akademik holat

- Joriy semestr
- O'qish yili
- Kreditlar (joriy semestr, jami)
- O'rtacha baho (GPA)
- Qarzlar

## API Endpoints

```
# Ariza
POST   /api/v1/enrollment/applications        # ariza topshirish
GET    /api/v1/enrollment/applications        # ro'yxat (filter)
GET    /api/v1/enrollment/applications/{id}
PATCH  /api/v1/enrollment/applications/{id}
POST   /api/v1/enrollment/applications/{id}/approve
POST   /api/v1/enrollment/applications/{id}/reject

# Hujjatlar
POST   /api/v1/enrollment/applications/{id}/documents
GET    /api/v1/enrollment/applications/{id}/documents
DELETE /api/v1/enrollment/documents/{id}

# Kontrakt
POST   /api/v1/enrollment/applications/{id}/contract  # generatsiya
GET    /api/v1/enrollment/applications/{id}/contract  # PDF olish
POST   /api/v1/enrollment/applications/{id}/sign       # ERI

# Talabalar
GET    /api/v1/students                       # ro'yxat (filter, search)
GET    /api/v1/students/{id}
PATCH  /api/v1/students/{id}/status
POST   /api/v1/students/{id}/transfer         # ko'chirish
POST   /api/v1/students/{id}/expel            # chetlashtirish
POST   /api/v1/students/{id}/restore          # qayta tiklash
POST   /api/v1/students/{id}/leave            # ta'tilga chiqarish

# Guruhlar
GET    /api/v1/groups
POST   /api/v1/groups
GET    /api/v1/groups/{id}
PATCH  /api/v1/groups/{id}
POST   /api/v1/groups/{id}/students           # talaba qo'shish
DELETE /api/v1/groups/{id}/students/{user_id}

# Buyruqlar
GET    /api/v1/orders
GET    /api/v1/orders/{id}
GET    /api/v1/orders/{id}/pdf

# Statistika
GET    /api/v1/enrollment/stats               # qabul statistikasi
GET    /api/v1/enrollment/quota-status        # qabul to'lganmi
```

## Database modellari

```sql
-- Talaba arizasi
CREATE TABLE enrollment_applications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    organization_id BIGINT REFERENCES organizations(id),
    specialty_id BIGINT REFERENCES specialties(id),
    academic_year VARCHAR(20) NOT NULL,
    application_number VARCHAR(50) UNIQUE,
    status VARCHAR(30) NOT NULL,
    
    -- Shaxsiy ma'lumotlar
    full_name VARCHAR(200) NOT NULL,
    pinfl VARCHAR(14),
    passport VARCHAR(20),
    birthdate DATE,
    is_foreign BOOLEAN DEFAULT FALSE,          -- xorijiy fuqaromi
    nationality VARCHAR(50),
    
    -- Ta'lim ma'lumotlari
    previous_education JSONB,                  -- attestat, diplom
    
    -- Kontakt
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT,
    
    -- Kontrakt
    contract_amount NUMERIC(12, 2),
    contract_url TEXT,
    contract_signed_at TIMESTAMP,
    
    -- Workflow
    submitted_at TIMESTAMP DEFAULT NOW(),
    reviewed_by BIGINT REFERENCES users(id),
    reviewed_at TIMESTAMP,
    rejection_reason TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Talaba (asosiy ma'lumotlar)
CREATE TABLE students (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(id),
    student_id_number VARCHAR(50) UNIQUE NOT NULL,  -- talaba ID
    organization_id BIGINT REFERENCES organizations(id),
    specialty_id BIGINT REFERENCES specialties(id),
    curriculum_id BIGINT REFERENCES curricula(id),
    group_id BIGINT REFERENCES groups(id),
    
    enrollment_year INT NOT NULL,
    expected_graduation_year INT,
    current_semester INT DEFAULT 1,
    
    education_form VARCHAR(20) DEFAULT 'distance',
    funding_type VARCHAR(20) DEFAULT 'contract',     -- 'contract', 'grant'
    
    status VARCHAR(30) NOT NULL,
    is_foreign BOOLEAN DEFAULT FALSE,
    
    enrolled_at DATE,
    graduated_at DATE,
    
    -- Akademik
    total_credits INT DEFAULT 0,
    completed_credits INT DEFAULT 0,
    gpa NUMERIC(4, 2),
    
    -- LMS registration (Nizom 21-band)
    lms_registered_at TIMESTAMP,                     -- OTM'da ro'yxatdan o'tgan vaqt
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_students_user ON students(user_id);
CREATE INDEX idx_students_group ON students(group_id);
CREATE INDEX idx_students_status ON students(status);
CREATE INDEX idx_students_specialty ON students(specialty_id);

-- Guruh
CREATE TABLE groups (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    specialty_id BIGINT REFERENCES specialties(id),
    enrollment_year INT NOT NULL,
    current_semester INT DEFAULT 1,
    max_students INT DEFAULT 25,
    advisor_id BIGINT REFERENCES users(id),         -- kurator
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Buyruq (Order)
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,                       -- 'enroll', 'transfer', 'expel', 'restore', 'leave'
    organization_id BIGINT REFERENCES organizations(id),
    student_id BIGINT REFERENCES students(id),
    issued_at DATE NOT NULL,
    issued_by BIGINT REFERENCES users(id),
    content JSONB,                                   -- buyruq matni
    pdf_url TEXT,
    signed_url TEXT,                                 -- ERI bilan imzolangan
    status VARCHAR(30) DEFAULT 'draft',              -- 'draft', 'signed', 'cancelled'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Akademik holat tarixi
CREATE TABLE student_status_history (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT REFERENCES students(id),
    old_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    reason TEXT,
    order_id BIGINT REFERENCES orders(id),
    changed_by BIGINT REFERENCES users(id),
    changed_at TIMESTAMP DEFAULT NOW()
);
```

## Quota validation

```python
# app/modules/enrollment/service.py
class EnrollmentService:
    async def validate_quota(self, specialty_id: int, academic_year: str) -> bool:
        """VM 559-qaror 15-band: bakalavriat — 300, magistratura — 30"""
        
        specialty = await self.repo.get_specialty(specialty_id)
        
        # AKT yo'nalishlariga cheklov tatbiq etilmaydi
        if specialty.is_ict_field:
            return True
        
        # Joriy talabalar (xorijiy hisobga olinmaydi)
        current_count = await self.repo.count_local_students(
            specialty_id, academic_year
        )
        
        max_allowed = 300 if specialty.level == 'bachelor' else 30
        
        if current_count >= max_allowed:
            raise QuotaExceededError(
                f"Quota to'lgan: {current_count}/{max_allowed}"
            )
        
        return True
```

## Frontend — Ariza formasi

```vue
<!-- views/enrollment/ApplicationView.vue -->
<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useEnrollmentStore } from '@/stores/enrollment'
import FileUpload from '@/components/ui/FileUpload.vue'
import StepWizard from '@/components/ui/StepWizard.vue'

const enrollment = useEnrollmentStore()
const currentStep = ref(0)

const form = reactive({
  // 1-bosqich: Shaxsiy ma'lumotlar
  full_name: '',
  pinfl: '',
  passport: '',
  birthdate: '',
  is_foreign: false,
  
  // 2-bosqich: Ta'lim
  specialty_id: null,
  previous_education: {},
  
  // 3-bosqich: Hujjatlar
  documents: [],
  
  // 4-bosqich: Kontrakt
  contract_accepted: false,
})

const steps = [
  'Shaxsiy ma\'lumotlar',
  'Ta\'lim yo\'nalishi',
  'Hujjatlar',
  'Kontrakt',
  'To\'lov',
]

async function submit() {
  const application = await enrollment.submitApplication(form)
  // To'lovga yo'naltirish
  window.location.href = application.payment_url
}
</script>
```

## Acceptance kriteriyalar

- [ ] Onlayn ariza forma (4 bosqich)
- [ ] Hujjatlarni yuklash
- [ ] Quota validatsiyasi (300/30)
- [ ] Xorijiy fuqarolar uchun maxsus oqim
- [ ] Kontrakt PDF generatsiya
- [ ] ERI bilan imzo
- [ ] Buyruq generatsiya
- [ ] Talabalar ro'yxati va filtri
- [ ] Ko'chirish, chetlashtirish, qayta tiklash
- [ ] Guruh boshqaruvi
- [ ] Hemis sync
- [ ] Test coverage ≥ 85%
