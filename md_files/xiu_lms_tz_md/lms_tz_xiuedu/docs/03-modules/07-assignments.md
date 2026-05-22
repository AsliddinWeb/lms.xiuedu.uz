# 07. Assignments (Vazifalar) Moduli

## Maqsad

Talabalarga vazifalar berish, yig'ish, tekshirish, baholash va plagiatga qarshi nazorat.

## Funksional talablar

### 1. Vazifa turlari

| Tur | Tavsifi |
|-----|---------|
| **Essay / Insho** | Matnli javob (TipTap editor) |
| **Fayl yuklash** | PDF, DOCX, ZIP (har xil format) |
| **Kod (programlash)** | Kod yuklash + avtotest |
| **Quiz / Test** | Ko'p variantli savollar |
| **Peer review** | O'zaro talabalar baholashi |
| **Group / Guruh** | Guruh ishi |
| **Presentation** | Slayd yuklash + video |
| **Practical / Laboratoriya** | Maxsus shablon bilan |

### 2. Vazifa parametrlari

- Sarlavha, tavsif, ko'rsatmalar (rich text)
- Topshirish muddati (deadline)
- Kechiktirish jazo (% kunlik)
- Maksimum bal
- Topshirish urinishlari soni
- Plagiat tekshiruvi (yoqish/o'chirish)
- Rubric (mezonlar bo'yicha baholash)
- Faylni qo'shimcha qilish (qo'llanma, namuna)

### 3. Topshirish jarayoni (talaba)

- Vazifa sahifasini ochadi
- Javobni yozadi yoki fayl yuklaydi
- Pre-submission tekshirish
- Topshiradi (submit)
- Status: Topshirildi → Tekshirilmoqda → Baholandi
- Bahoni ko'radi va o'qituvchi izohini

### 4. Tekshirish (o'qituvchi)

- Vazifalar ro'yxati (filter: status, sana)
- Javobni ko'rish (inline preview)
- Plagiat hisoboti
- Rubric bo'yicha baholash
- Inline annotatsiya (PDF/DOCX uchun)
- Audio izoh qoldirish
- Video izoh
- Bahoni saqlash → talaba ko'radi

### 5. Avtomatik baholash

- **Quiz** — avtomatik (to'g'ri javob bilan)
- **Kod** — sandboxed test runner (Docker)
- **Auto-grading rubric** — kalit so'zlar bo'yicha (AI yordamida)

### 6. Plagiat tekshiruvi

- **Antiplag.uz** integratsiyasi (asosiy)
- **Turnitin** (xalqaro, ixtiyoriy)
- Tekshiruv natijasi: % o'xshashlik, manbalar
- Avtomatik bayroq qo'yish (>30%)

### 7. Peer review

- Anonim baholash
- Har talaba 3 ta boshqa talabani baholaydi
- Yakuniy baho — o'qituvchi va peer baholarning kombinatsiyasi
- Baholash mezoniga muvofiq (rubric)

### 8. Bahoga qarshi shikoyat

- Talaba bahoni qabul qilmasa — apellyatsiya yozish mumkin
- O'qituvchi yoki kafedra mudiri ko'rib chiqadi
- Yangi baho qo'yish yoki saqlab qolish

## API Endpoints

```
# Vazifa
GET    /api/v1/assignments                    # ro'yxat
POST   /api/v1/assignments                    # yaratish
GET    /api/v1/assignments/{id}
PATCH  /api/v1/assignments/{id}
DELETE /api/v1/assignments/{id}
POST   /api/v1/assignments/{id}/duplicate

# Topshirish
POST   /api/v1/assignments/{id}/submissions   # topshirish
GET    /api/v1/assignments/{id}/submissions   # ro'yxat (o'qituvchi)
GET    /api/v1/submissions/{id}               # bitta topshiriq
PATCH  /api/v1/submissions/{id}               # qayta topshirish
GET    /api/v1/submissions/{id}/files
DELETE /api/v1/submissions/{id}

# Baholash
POST   /api/v1/submissions/{id}/grade         # baho qo'yish
PATCH  /api/v1/submissions/{id}/grade
POST   /api/v1/submissions/{id}/feedback      # izoh
POST   /api/v1/submissions/{id}/annotations   # inline izoh

# Plagiat
POST   /api/v1/submissions/{id}/check-plagiarism
GET    /api/v1/submissions/{id}/plagiarism-report

# Rubric
GET    /api/v1/rubrics
POST   /api/v1/rubrics
GET    /api/v1/rubrics/{id}
PATCH  /api/v1/rubrics/{id}

# Peer review
POST   /api/v1/assignments/{id}/peer-review/start
GET    /api/v1/peer-reviews/my                # mening baholashim
POST   /api/v1/peer-reviews/{id}/submit

# Apellyatsiya
POST   /api/v1/submissions/{id}/appeal
GET    /api/v1/appeals
POST   /api/v1/appeals/{id}/respond
```

## Database modellari

```sql
-- Vazifa
CREATE TABLE assignments (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT REFERENCES courses(id) ON DELETE CASCADE,
    lesson_id BIGINT REFERENCES lessons(id) ON DELETE SET NULL,
    
    title VARCHAR(500) NOT NULL,
    description TEXT,                              -- rich text
    instructions TEXT,
    
    type VARCHAR(30) NOT NULL,                     -- 'essay', 'file', 'code', 'quiz', 'peer_review'
    
    -- Sanalari
    available_from TIMESTAMP,
    due_date TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,                           -- bundan keyin qabul qilinmaydi
    
    -- Baho
    max_score NUMERIC(5, 2) NOT NULL DEFAULT 100,
    pass_score NUMERIC(5, 2) DEFAULT 60,
    weight_percent NUMERIC(5, 2),                  -- yakuniy bahodagi ulushi
    
    -- Konfiguratsiya
    max_attempts INT DEFAULT 1,
    late_submission_allowed BOOLEAN DEFAULT TRUE,
    late_penalty_per_day NUMERIC(5, 2) DEFAULT 10, -- % kunlik
    
    -- Plagiat
    plagiarism_check_enabled BOOLEAN DEFAULT FALSE,
    plagiarism_threshold NUMERIC(5, 2) DEFAULT 30,
    
    -- Rubric
    rubric_id BIGINT REFERENCES rubrics(id),
    
    -- Fayl cheklovlari
    allowed_file_types TEXT[],                     -- ['pdf', 'docx', 'zip']
    max_file_size_mb INT DEFAULT 50,
    
    -- Peer review
    peer_review_enabled BOOLEAN DEFAULT FALSE,
    peer_reviews_per_submission INT DEFAULT 3,
    
    -- Status
    is_published BOOLEAN DEFAULT FALSE,
    
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Topshiriq
CREATE TABLE submissions (
    id BIGSERIAL PRIMARY KEY,
    assignment_id BIGINT REFERENCES assignments(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id),
    
    attempt_number INT DEFAULT 1,
    
    content TEXT,                                  -- essay matni
    files JSONB,                                   -- [{name, url, size}]
    
    submitted_at TIMESTAMP DEFAULT NOW(),
    is_late BOOLEAN DEFAULT FALSE,
    
    status VARCHAR(20) DEFAULT 'submitted',        -- 'draft', 'submitted', 'grading', 'graded', 'returned'
    
    -- Baho
    score NUMERIC(5, 2),
    grade_letter VARCHAR(5),                       -- A, B, C, D, F
    final_score NUMERIC(5, 2),                     -- after late penalty
    
    -- Izoh
    feedback TEXT,
    annotations JSONB,                             -- inline izohlar
    
    graded_by BIGINT REFERENCES users(id),
    graded_at TIMESTAMP,
    
    -- Plagiat
    plagiarism_score NUMERIC(5, 2),
    plagiarism_report_url TEXT,
    
    UNIQUE(assignment_id, user_id, attempt_number)
);

CREATE INDEX idx_submissions_assignment ON submissions(assignment_id);
CREATE INDEX idx_submissions_user ON submissions(user_id);
CREATE INDEX idx_submissions_status ON submissions(status);

-- Rubric (baholash mezoni)
CREATE TABLE rubrics (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    total_points NUMERIC(5, 2),
    criteria JSONB NOT NULL,                       -- [{name, max_points, levels: [...]}]
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Peer review
CREATE TABLE peer_reviews (
    id BIGSERIAL PRIMARY KEY,
    submission_id BIGINT REFERENCES submissions(id),
    reviewer_id BIGINT REFERENCES users(id),
    
    score NUMERIC(5, 2),
    feedback TEXT,
    rubric_scores JSONB,
    
    submitted_at TIMESTAMP,
    
    UNIQUE(submission_id, reviewer_id)
);

-- Apellyatsiya
CREATE TABLE grade_appeals (
    id BIGSERIAL PRIMARY KEY,
    submission_id BIGINT REFERENCES submissions(id),
    student_id BIGINT REFERENCES users(id),
    
    reason TEXT NOT NULL,
    
    status VARCHAR(20) DEFAULT 'pending',          -- 'pending', 'approved', 'rejected'
    
    new_score NUMERIC(5, 2),
    response TEXT,
    
    reviewed_by BIGINT REFERENCES users(id),
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Plagiat tekshiruvi (Celery task)

```python
# app/workers/plagiarism.py

@celery_app.task
def check_plagiarism(submission_id: int):
    submission = get_submission(submission_id)
    
    # Kontent tayyorlash (matn)
    text = extract_text(submission)
    
    # Antiplag.uz API'ga yuborish
    from app.integrations.antiplag.client import AntiplagClient
    client = AntiplagClient()
    
    result = client.check(text=text, lang=submission.language)
    
    # Natijani saqlash
    submission.plagiarism_score = result.similarity_percent
    submission.plagiarism_report_url = result.report_url
    save(submission)
    
    # Bayroq qo'yish (high similarity)
    if result.similarity_percent > submission.assignment.plagiarism_threshold:
        notify_teacher(
            submission_id,
            f"Plagiat ehtimoli: {result.similarity_percent}%"
        )
```

## Acceptance kriteriyalar

- [ ] Barcha vazifa turlari (essay, fayl, kod, quiz)
- [ ] Topshirish va baholash flowi
- [ ] Plagiat tekshiruvi (Antiplag)
- [ ] Rubric bo'yicha baholash
- [ ] Inline annotatsiya (PDF)
- [ ] Peer review
- [ ] Avtomatik kod testlash
- [ ] Late submission jazo
- [ ] Apellyatsiya
- [ ] Test coverage ≥ 80%
