# 09. Exams & Proctoring (Imtihonlar va Avtoproktoring) Moduli

## Maqsad

Talabalarni baholash uchun imtihonlar tashkil qilish va avtoproktoring orqali nazorat qilish. **VM 559-qaror Nizomning 10-bandiga muvofiq, avtoproktoring funksiyasi MAJBURIY.**

## Normativ asos
- **VM 559-qaror Nizom 10-band:** "LMS imtihonlarda autentifikatsiya va proktoring funksiyalariga ega bo'lishi kerak"
- **Nizom 21-band:** Yakuniy davlat attestatsiyasi (DAK) bevosita OTM'da, an'anaviy tarzda

## Funksional talablar

### 1. Imtihon turlari

| Tur | Tavsifi | Proktoring |
|-----|---------|-----------|
| **Joriy nazorat** | Hafta/oy oxirida | Light |
| **Oraliq nazorat** | Semestr o'rtasida | Standart |
| **Yakuniy nazorat** | Semestr oxiri | Strong |
| **Davlat attestatsiyasi (DAK)** | Bitiruvchilar | OTM'da, an'anaviy |
| **Adaptiv test** | Bilim darajasiga moslashadi | Standart |
| **Open-book** | Manbalar bilan | Yengil |

### 2. Savol turlari

| Tur | Tavsifi |
|-----|---------|
| **Single choice** | Bitta to'g'ri javob |
| **Multiple choice** | Bir nechta to'g'ri |
| **True/False** | Ha/yo'q |
| **Matching** | Solishtirish |
| **Fill in the blank** | Bo'sh joylarni to'ldirish |
| **Essay** | Erkin javob (qo'lda baholash) |
| **Numeric** | Raqamli javob (tolerance bilan) |
| **File upload** | Fayl yuklash |
| **Code** | Kod yozish |
| **Drag & drop** | Surib qo'yish |

### 3. Imtihon konstruktori

- Savollar bazasidan tanlash
- Yangi savol yaratish
- Random tartiblash (har talabaga boshqacha)
- Savollar bankidan random tanlash
- Vaqt cheklovi (umumiy yoki har savolga)
- Urinishlar soni
- Salbiy ball (-25%)

### 4. Avtoproktoring (CRITICAL)

#### 4.1. Imtihon oldidan
- **Foto identifikatsiya** — pasport va yuz
- **Xona ko'rsatish** — webcam orqali aylantirish
- **Tizim tekshiruvi** — kamera, mikrofon, ekran ulashish
- **Ko'rsatma o'qish va tasdiqlash**

#### 4.2. Imtihon davomida
- **Doimiy yuz tanish (face recognition)**
  - Talaba o'rnida bo'lishi shart
  - Boshqa odam ko'rinmasin
- **Ko'z harakatlari tahlili (eye tracking)**
  - Ekrandan tashqariga qarash
- **Audio tahlili**
  - Boshqa ovozlar (kim biror narsa aytayotgan bo'lsa)
  - Klaviatura tovushi
- **Ekran ulashish (screen sharing)**
  - Boshqa oynalar / browser tabs
- **Klaviatura va sichqoncha aktivligi**
- **Tab switch detection**
- **Ko'p monitor detection**

#### 4.3. Hodisalar (events) qayd etiladi
- Ko'p odam aniqlandi
- Talaba kadrdan chiqib ketdi
- Ekrandan tashqariga qaradi (5+ sekund)
- Boshqa ovozlar
- Tab almashtirish
- Tashqi qurilma (telefon)

#### 4.4. Risk score
- AI har 30 sekundda risk score'ni hisoblaydi (0-100)
- 70+ — yuqori xavf, sessiya bayroqlanadi
- 90+ — sessiya avtomatik to'xtatilishi mumkin

#### 4.5. Hisobot
- Imtihon tugagandan keyin hisobot
- Hodisalar ro'yxati (timestamp bilan)
- Video va audio yozuv
- Risk score grafigi
- O'qituvchi qaror qabul qiladi (qabul qilish / bekor qilish)

### 5. Proktoring rejimlari

| Rejim | Tavsifi |
|-------|---------|
| **None** | Proktoring yo'q |
| **Light** | Faqat yuz tanish |
| **Standard** | Yuz + ekran + audio |
| **Strong** | Hammasi + live human kuzatuvchi |
| **Live** | Faqat jonli kuzatuv (proctor) |

### 6. Imtihonni qayta topshirish

- Yo'qotilgan ulanish (internet uzilishi)
- Texnik nosozlik
- Avtomatik qayta tiklash (3 daqiqa ichida)
- Yangidan boshlash (admin ruxsati)

## API Endpoints

```
# Imtihonlar
GET    /api/v1/exams                          # ro'yxat
POST   /api/v1/exams                          # yaratish
GET    /api/v1/exams/{id}
PATCH  /api/v1/exams/{id}
DELETE /api/v1/exams/{id}
POST   /api/v1/exams/{id}/publish

# Savollar bankidan
GET    /api/v1/question-banks
POST   /api/v1/question-banks
GET    /api/v1/questions
POST   /api/v1/questions
PATCH  /api/v1/questions/{id}

# Talaba imtihonni topshirish
GET    /api/v1/exams/{id}/start               # boshlash (proktoring init)
POST   /api/v1/exams/{id}/proctoring/init     # kamera, foto, xona
POST   /api/v1/exam-attempts/{id}/answer      # javob saqlash
POST   /api/v1/exam-attempts/{id}/submit      # tugatish
GET    /api/v1/exam-attempts/{id}/timer       # vaqt qoldi

# Proktoring (real-time)
WS     /ws/proctoring/{attempt_id}            # WebSocket — frame yuborish
POST   /api/v1/proctoring/events              # hodisalar
GET    /api/v1/proctoring/{attempt_id}/events
GET    /api/v1/proctoring/{attempt_id}/report

# Baholash (essay savollar)
GET    /api/v1/exam-attempts/{id}/manual-grading
POST   /api/v1/exam-attempts/{id}/grade

# Hisobotlar
GET    /api/v1/exams/{id}/results             # natijalar
GET    /api/v1/exams/{id}/statistics
```

## Database modellari

```sql
-- Imtihon
CREATE TABLE exams (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT REFERENCES courses(id),
    
    title VARCHAR(500) NOT NULL,
    description TEXT,
    instructions TEXT,
    
    type VARCHAR(30) NOT NULL,                     -- 'mid', 'final', 'state', 'practice'
    
    -- Vaqt
    available_from TIMESTAMP NOT NULL,
    available_until TIMESTAMP NOT NULL,
    duration_minutes INT NOT NULL,                 -- imtihon davomiyligi
    
    -- Savollar
    question_selection JSONB,                      -- ['fixed' | 'random_from_bank']
    randomize_questions BOOLEAN DEFAULT TRUE,
    randomize_answers BOOLEAN DEFAULT TRUE,
    
    -- Baho
    max_score NUMERIC(6, 2) DEFAULT 100,
    pass_score NUMERIC(6, 2) DEFAULT 60,
    show_correct_after BOOLEAN DEFAULT FALSE,
    show_score_immediately BOOLEAN DEFAULT TRUE,
    
    -- Urinishlar
    max_attempts INT DEFAULT 1,
    
    -- Proktoring
    proctoring_mode VARCHAR(20) DEFAULT 'standard', -- 'none', 'light', 'standard', 'strong', 'live'
    require_camera BOOLEAN DEFAULT TRUE,
    require_microphone BOOLEAN DEFAULT TRUE,
    require_screen_share BOOLEAN DEFAULT FALSE,
    record_video BOOLEAN DEFAULT TRUE,
    
    -- Boshqa
    is_published BOOLEAN DEFAULT FALSE,
    
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Savol banki
CREATE TABLE question_banks (
    id BIGSERIAL PRIMARY KEY,
    subject_id BIGINT REFERENCES subjects(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Savol
CREATE TABLE questions (
    id BIGSERIAL PRIMARY KEY,
    bank_id BIGINT REFERENCES question_banks(id),
    
    text TEXT NOT NULL,                            -- savol matni
    type VARCHAR(30) NOT NULL,                     -- 'single', 'multiple', 'essay', etc.
    
    options JSONB,                                 -- variantlar
    correct_answer JSONB,                          -- to'g'ri javob(lar)
    explanation TEXT,                              -- izoh
    
    points NUMERIC(5, 2) DEFAULT 1,
    difficulty VARCHAR(20),                        -- 'easy', 'medium', 'hard'
    
    tags TEXT[],
    
    media JSONB,                                   -- rasm, video qo'shilgan
    
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Imtihondagi savollar (junction)
CREATE TABLE exam_questions (
    id BIGSERIAL PRIMARY KEY,
    exam_id BIGINT REFERENCES exams(id) ON DELETE CASCADE,
    question_id BIGINT REFERENCES questions(id),
    order_index INT,
    points_override NUMERIC(5, 2)
);

-- Talaba urinishi
CREATE TABLE exam_attempts (
    id BIGSERIAL PRIMARY KEY,
    exam_id BIGINT REFERENCES exams(id),
    user_id BIGINT REFERENCES users(id),
    
    attempt_number INT DEFAULT 1,
    
    started_at TIMESTAMP DEFAULT NOW(),
    submitted_at TIMESTAMP,
    auto_submitted BOOLEAN DEFAULT FALSE,           -- vaqt tugagani uchun
    
    -- Bahoga oid
    total_score NUMERIC(6, 2),
    max_possible_score NUMERIC(6, 2),
    percent NUMERIC(5, 2),
    grade_letter VARCHAR(5),
    is_passed BOOLEAN,
    
    -- Proktoring
    proctoring_session_id BIGINT REFERENCES proctoring_sessions(id),
    risk_score NUMERIC(5, 2),
    is_flagged BOOLEAN DEFAULT FALSE,
    flagged_reason TEXT,
    
    -- Baholash
    grading_status VARCHAR(20) DEFAULT 'pending',   -- 'pending', 'auto_graded', 'manually_graded'
    graded_by BIGINT REFERENCES users(id),
    graded_at TIMESTAMP,
    
    UNIQUE(exam_id, user_id, attempt_number)
);

-- Talabaning javoblari
CREATE TABLE exam_answers (
    id BIGSERIAL PRIMARY KEY,
    attempt_id BIGINT REFERENCES exam_attempts(id) ON DELETE CASCADE,
    question_id BIGINT REFERENCES questions(id),
    
    answer JSONB,                                  -- talaba javobi
    
    is_correct BOOLEAN,
    points_awarded NUMERIC(5, 2),
    
    answered_at TIMESTAMP,
    time_spent_seconds INT,
    
    -- Manual grading (essay)
    manual_score NUMERIC(5, 2),
    grader_feedback TEXT,
    graded_by BIGINT REFERENCES users(id),
    
    UNIQUE(attempt_id, question_id)
);

-- Proktoring sessiyasi
CREATE TABLE proctoring_sessions (
    id BIGSERIAL PRIMARY KEY,
    attempt_id BIGINT REFERENCES exam_attempts(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id),
    
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    
    mode VARCHAR(20) NOT NULL,                     -- 'light', 'standard', 'strong', 'live'
    
    -- Tekshiruv
    identity_photo_url TEXT,                       -- pasport rasmi
    selfie_url TEXT,                               -- yuz fotosi
    room_video_url TEXT,                           -- xona video
    identity_verified BOOLEAN DEFAULT FALSE,
    
    -- Yozuvlar
    video_url TEXT,                                -- ekran video
    webcam_url TEXT,                               -- webcam yozuv
    audio_url TEXT,                                -- audio yozuv
    
    -- Risk
    final_risk_score NUMERIC(5, 2),
    risk_breakdown JSONB,                          -- har xil omillar
    
    -- O'qituvchi qarori
    reviewed_by BIGINT REFERENCES users(id),
    review_decision VARCHAR(20),                   -- 'accepted', 'rejected', 'flagged'
    review_notes TEXT,
    reviewed_at TIMESTAMP
);

-- Proktoring hodisalari (partition by date)
CREATE TABLE proctoring_events (
    id BIGSERIAL,
    session_id BIGINT REFERENCES proctoring_sessions(id),
    timestamp TIMESTAMP NOT NULL,
    
    event_type VARCHAR(50) NOT NULL,               -- 'face_lost', 'multiple_faces', 'tab_switch', 'voice_detected'
    severity VARCHAR(20),                          -- 'low', 'medium', 'high'
    
    data JSONB,                                    -- qo'shimcha ma'lumotlar
    
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Misol partition (har oyga 1)
CREATE TABLE proctoring_events_2026_05 PARTITION OF proctoring_events
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

CREATE INDEX idx_proctoring_events_session ON proctoring_events(session_id, timestamp);
```

## Avtoproktoring AI implementatsiyasi

### 1. Frontend — frame yuborish

```typescript
// composables/useProctoring.ts
import { ref, onMounted, onUnmounted } from 'vue'

export function useProctoring(attemptId: number) {
  const ws = ref<WebSocket | null>(null)
  const stream = ref<MediaStream | null>(null)
  const videoRef = ref<HTMLVideoElement>()
  const canvasRef = ref<HTMLCanvasElement>()
  
  async function start() {
    // 1. WebSocket ulanish
    ws.value = new WebSocket(`wss://lms-api.xiuedu.uz/ws/proctoring/${attemptId}`)
    
    // 2. Kamera va mikrofon
    stream.value = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
      audio: true,
    })
    
    if (videoRef.value) {
      videoRef.value.srcObject = stream.value
    }
    
    // 3. Frame yuborish (har 5 sekundda)
    setInterval(captureFrame, 5000)
    
    // 4. Ekran ulashish (strong rejim uchun)
    if (mode === 'strong') {
      await captureScreen()
    }
  }
  
  async function captureFrame() {
    if (!videoRef.value || !canvasRef.value || !ws.value) return
    
    const ctx = canvasRef.value.getContext('2d')!
    ctx.drawImage(videoRef.value, 0, 0, 640, 480)
    
    const blob = await new Promise<Blob>((resolve) => {
      canvasRef.value!.toBlob((b) => resolve(b!), 'image/jpeg', 0.7)
    })
    
    // WebSocket orqali yuborish
    ws.value.send(blob)
  }
  
  async function captureScreen() {
    const screenStream = await navigator.mediaDevices.getDisplayMedia({
      video: { displaySurface: 'monitor' },
    })
    // ... record to MediaRecorder
  }
  
  function stop() {
    stream.value?.getTracks().forEach(t => t.stop())
    ws.value?.close()
  }
  
  onMounted(start)
  onUnmounted(stop)
  
  return { videoRef, canvasRef, start, stop }
}
```

### 2. Backend — frame qabul qilish

```python
# app/websockets/live_proctoring.py
from fastapi import WebSocket, WebSocketDisconnect
import cv2
import numpy as np
from PIL import Image
import io

@app.websocket("/ws/proctoring/{attempt_id}")
async def proctoring_ws(websocket: WebSocket, attempt_id: int):
    await websocket.accept()
    
    session = await create_proctoring_session(attempt_id)
    
    try:
        while True:
            # Frame qabul qilish
            data = await websocket.receive_bytes()
            
            # Image'ga aylantirish
            img = np.array(Image.open(io.BytesIO(data)))
            
            # AI tahlil (Celery'ga yuborish — async)
            from app.workers.proctoring import analyze_frame
            analyze_frame.delay(session.id, data, timestamp=datetime.utcnow().isoformat())
            
    except WebSocketDisconnect:
        await end_proctoring_session(session.id)
```

### 3. AI tahlil (Celery)

```python
# app/workers/proctoring.py
import face_recognition
import cv2
import numpy as np

@celery_app.task
def analyze_frame(session_id: int, frame_bytes: bytes, timestamp: str):
    img = np.array(Image.open(io.BytesIO(frame_bytes)))
    
    events = []
    
    # 1. Face detection
    face_locations = face_recognition.face_locations(img)
    
    if len(face_locations) == 0:
        events.append({
            "type": "face_lost",
            "severity": "high",
            "timestamp": timestamp,
        })
    elif len(face_locations) > 1:
        events.append({
            "type": "multiple_faces",
            "severity": "high",
            "data": {"count": len(face_locations)},
            "timestamp": timestamp,
        })
    else:
        # 2. Identity verification
        face_encoding = face_recognition.face_encodings(img, face_locations)[0]
        registered_encoding = get_registered_encoding(session_id)
        
        match = face_recognition.compare_faces(
            [registered_encoding], face_encoding, tolerance=0.6
        )[0]
        
        if not match:
            events.append({
                "type": "identity_mismatch",
                "severity": "high",
                "timestamp": timestamp,
            })
    
    # 3. Eye tracking (mediapipe)
    gaze_direction = detect_gaze(img)
    if gaze_direction in ["far_left", "far_right", "below_screen"]:
        events.append({
            "type": "gaze_off_screen",
            "severity": "medium",
            "data": {"direction": gaze_direction},
            "timestamp": timestamp,
        })
    
    # 4. Eventlarni saqlash
    for event in events:
        save_proctoring_event(session_id, event)
    
    # 5. Risk score yangilash
    update_risk_score(session_id)
```

## Risk score hisoblash

```python
def calculate_risk_score(session_id: int) -> float:
    """Risk score 0-100"""
    events = get_session_events(session_id)
    
    weights = {
        "face_lost": 5,
        "multiple_faces": 10,
        "identity_mismatch": 30,
        "gaze_off_screen": 2,
        "voice_detected": 3,
        "tab_switch": 5,
        "second_monitor": 8,
    }
    
    raw_score = sum(weights.get(e.event_type, 1) for e in events)
    
    # Cap at 100
    return min(raw_score, 100)
```

## Acceptance kriteriyalar

- [ ] Imtihon konstruktor (10 ta savol turi)
- [ ] Savollar banki
- [ ] Random tartiblash
- [ ] Vaqt cheklovi va auto-submit
- [ ] Avtomatik baholash (auto types)
- [ ] Manual baholash (essay)
- [ ] **Avtoproktoring (face, gaze, audio, screen)** — VM 559-qaror
- [ ] **Risk score hisoblash**
- [ ] Hodisalar logi
- [ ] Hisobot generatsiyasi
- [ ] O'qituvchi review paneli
- [ ] Adaptiv test
- [ ] Connection lost — qayta tiklash
- [ ] Test coverage ≥ 80%
