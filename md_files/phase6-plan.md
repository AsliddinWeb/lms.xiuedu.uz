# Phase 6 — Imtihonlar + Avtoproctoring

> XIU LMS oltinchi fazasi: imtihonlar tizimi va avtoproctoring. 559-qaror 10-bandiga ko'ra avtoproctoring **majburiy**, DAK natijalari HEMIS'ga sinxron qilinishi shart.
>
> **Boshlanish:** 2026-05-14
> **Taxminiy yakun:** ~2-3 hafta (~15 ish kuni)
> **Wireframe:** `md_files/ui_wireframes/lms_ui/pages/09-exam-page.html` + `18-reports.html`

---

## 0. Hozirgi holat (oldingi fazalardan)

✅ Tayyor:
- LMS asosi (P0–P4): kurs, dars, kontent, topshiriq, baholash, peer review, apellyatsiya
- Live darslar (P5 + P5b): native WebRTC, lobby, recording, network bar, reactions, blur, mobile
- UI wireframe alignment (S0–S4): 4928 i18n tarjima, dark mode, wireframe 01–17 mos
- HEMIS integratsiyasi: `Organization.settings.hemis.base_url`, profile sync (`hemis_sync.fetch_student_profile`)

⏳ Phase 6 da yangi:
- Exam (`exam.exams`, `exam.questions`, `exam.attempts`, `exam.answers`, `exam.results`) modellari
- Auto-grading engine (single/multiple/text exact match)
- Proctoring engine (kamera/ekran/event/yuz tanish)
- HEMIS grade sync (`hemis_sync.send_exam_grades`)

---

## 1. Sub-fazalar (7 ta)

| ID | Mavzu | Kun | Asosiy chiqim |
|---|---|---|---|
| **6a** | Backend models + CRUD | 2 | Exam, Question, QuestionOption modellari, Alembic migration, REST endpoints |
| **6b** | ExamAttempt + auto-grading | 2 | Attempt model, vaqt limit, avto-submit, scoring engine |
| **6c** | Pedagog exam builder | 2 | Course Builder'ga "Imtihonlar" tab, savol konstruktori, drag-drop tartib |
| **6d** | Talaba exam lobby | 1.5 | Identity check, system check, monitoring rozilik |
| **6e** | Exam taking UI (WF 09) | 2.5 | Savol navigatsiyasi, timer, savol turlari, oraliq saqlash, fullscreen |
| **6f** | Proctoring engine | 3 | Kamera+ekran capture, event tracking, violation scoring, face-api.js |
| **6g** | Admin review + Reports + HEMIS sync | 2 | Flagged session review, reports module, hemis_sync.send_exam_grades() |

**Jami:** ~15 ish kuni

---

## 2. Sub-faza 6a — Backend: Exam + Question models

### 2.1 Database schema

**`exam.exams` jadval:**
```sql
id                     BIGINT PK
course_id              BIGINT FK → courses.id (NOT NULL)
lesson_id              BIGINT FK → lessons.id NULL (kurs-level yoki dars-level)
organization_id        BIGINT FK → organizations.id (single-tenant XIU)

title                  TEXT NOT NULL
description            TEXT
type                   ENUM('midterm', 'final', 'quiz', 'dak') NOT NULL
status                 ENUM('draft', 'published', 'archived') DEFAULT 'draft'

-- Settings
duration_minutes       INT NOT NULL  -- vaqt limiti
max_attempts           INT DEFAULT 1
passing_score          DECIMAL(5,2) DEFAULT 60.0  -- foiz (%)
shuffle_questions      BOOL DEFAULT TRUE
shuffle_options        BOOL DEFAULT TRUE
show_correct_answers   BOOL DEFAULT FALSE  -- exam tugagandan keyin
question_count         INT  -- agar < total savol bo'lsa, random tanlanadi

-- Proctoring
proctoring_enabled     BOOL DEFAULT TRUE  -- 559-qaror majburiy
require_face_id        BOOL DEFAULT TRUE
require_screen_share   BOOL DEFAULT TRUE
allow_tab_switch       BOOL DEFAULT FALSE  -- false bo'lsa violation
max_face_loss_seconds  INT DEFAULT 10  -- yuz yo'qolsa N sekund'dan keyin alert

-- Schedule
available_from         TIMESTAMP
available_until        TIMESTAMP
closed_at              TIMESTAMP NULL

created_by             BIGINT FK → users.id
created_at             TIMESTAMP
updated_at             TIMESTAMP
```

**`exam.questions` jadval:**
```sql
id                     BIGINT PK
exam_id                BIGINT FK → exams.id (CASCADE)
order_index            INT NOT NULL

type                   ENUM('single_choice', 'multiple_choice', 'true_false', 
                           'short_text', 'essay', 'code', 'file_upload') NOT NULL
title                  TEXT NOT NULL  -- savol matni (Markdown)
explanation            TEXT  -- to'g'ri javob izohi (exam tugagandan keyin)

points                 DECIMAL(5,2) NOT NULL DEFAULT 1.0
required               BOOL DEFAULT TRUE

-- Type-specific
code_language          VARCHAR(20) NULL  -- code uchun (python/js/sql)
code_initial           TEXT NULL  -- code uchun boshlang'ich kod
max_file_size_mb       INT NULL  -- file_upload uchun
allowed_file_types     TEXT[] NULL  -- file_upload uchun

-- Auto-grading config
exact_match            BOOL DEFAULT TRUE  -- short_text uchun
case_sensitive         BOOL DEFAULT FALSE  -- short_text uchun
correct_text           TEXT NULL  -- short_text uchun (alternative answers JSON)

created_at             TIMESTAMP
```

**`exam.question_options` jadval (single/multiple/true_false):**
```sql
id                     BIGINT PK
question_id            BIGINT FK → questions.id (CASCADE)
order_index            INT
text                   TEXT NOT NULL
is_correct             BOOL DEFAULT FALSE
explanation            TEXT  -- nima uchun to'g'ri/noto'g'ri
```

### 2.2 Backend faylar

- `backend/app/modules/exams/models.py` — SQLAlchemy modellari
- `backend/app/modules/exams/schemas.py` — Pydantic schemalar (`ExamCreate`, `ExamRead`, `QuestionCreate`, `QuestionRead`)
- `backend/app/modules/exams/services.py` — biznes mantiq
- `backend/app/modules/exams/api/exams.py` — REST router
- `backend/app/modules/exams/api/questions.py` — savol CRUD
- `backend/alembic/versions/xxxx_exams_phase6a.py` — migration

### 2.3 REST API endpoints

```
GET    /exams                          ?course_id&status&type     # list
POST   /exams                                                     # create
GET    /exams/{id}
PATCH  /exams/{id}
DELETE /exams/{id}
POST   /exams/{id}/publish
POST   /exams/{id}/archive
POST   /exams/{id}/clone                                          # template

GET    /exams/{id}/questions                                      # nested list
POST   /exams/{id}/questions
GET    /questions/{id}
PATCH  /questions/{id}
DELETE /questions/{id}
POST   /exams/{id}/questions/reorder    [ids: number[]]
```

### 2.4 Permissions

- `exam.create` — kurs muallifi (course.create permission'i bilan ekvivalent)
- `exam.publish` — kurs muallifi
- `exam.read` — kursga ro'yxatdan o'tgan talaba yoki muallif
- `exam.delete` — kurs muallifi yoki admin

### 2.5 Tests

- Test coverage: model creation, CRUD endpoints, permission gating, schema validation, single-tenant XIU enforcement

---

## 3. Sub-faza 6b — ExamAttempt + auto-grading

### 3.1 Database schema

**`exam.attempts` jadval:**
```sql
id                     BIGINT PK
exam_id                BIGINT FK → exams.id
user_id                BIGINT FK → users.id
attempt_number         INT NOT NULL  -- 1, 2, 3 (max_attempts gacha)

status                 ENUM('in_progress', 'submitted', 'auto_submitted', 
                           'graded', 'flagged', 'invalidated') NOT NULL
started_at             TIMESTAMP NOT NULL
submitted_at           TIMESTAMP
deadline_at            TIMESTAMP  -- started_at + duration_minutes
time_spent_seconds     INT DEFAULT 0

-- Scoring
auto_score             DECIMAL(5,2)  -- avto-baholangan ball
manual_score           DECIMAL(5,2)  -- qo'lda baholangan ball (essay)
total_score            DECIMAL(5,2)  -- yig'indisi
max_score              DECIMAL(5,2)  -- to'liq mumkin bo'lgan ball
percentage             DECIMAL(5,2)  -- foiz
passed                 BOOL  -- passing_score ga teng yoki yuqori

-- Randomization
question_order         JSONB  -- bu attempt uchun savol id'lari tartibi
option_order           JSONB  -- savol_id → option_id[] tartibi

-- Proctoring
proctoring_session_id  BIGINT FK → exam_proctoring.id NULL
violation_score        INT DEFAULT 0  -- 0-100 (0=toza, 100=qoidabuzar)
flagged                BOOL DEFAULT FALSE

UNIQUE(exam_id, user_id, attempt_number)
```

**`exam.answers` jadval:**
```sql
id                     BIGINT PK
attempt_id             BIGINT FK → attempts.id (CASCADE)
question_id            BIGINT FK → questions.id

-- Answer (savol turiga qarab)
selected_option_ids    BIGINT[]  -- single/multiple/true_false
text_answer            TEXT  -- short_text, essay
code_answer            TEXT  -- code
file_url               TEXT  -- file_upload
file_size_bytes        BIGINT

-- Scoring
auto_correct           BOOL  -- avto-baholangan natija (NULL = baholanmagan)
points_earned          DECIMAL(5,2) DEFAULT 0
points_max             DECIMAL(5,2)
graded_by              BIGINT FK → users.id NULL  -- manual grade kim
graded_at              TIMESTAMP
grader_comment         TEXT

created_at             TIMESTAMP
updated_at             TIMESTAMP

UNIQUE(attempt_id, question_id)
```

### 3.2 Auto-grading engine

`backend/app/modules/exams/grading.py`:

```python
def grade_attempt(attempt_id: int) -> AttemptResult:
    """
    Avtomatik baholash:
    - single_choice: tanlangan option correct == True bo'lsa, full points
    - multiple_choice: barcha correct optionlar tanlangan + noto'g'ri yo'q → full
                       qisman: (correct_selected / total_correct) * points
    - true_false: bool match → full
    - short_text: exact_match yoki regex (alternative answers JSON)
    - essay: manual grading kerak (auto_score = None)
    - code: regex test cases yoki manual (Phase 9'da kod runner)
    - file_upload: manual grading
    """
```

### 3.3 REST API endpoints

```
POST   /exams/{id}/start              # talaba imtihonni boshlaydi (attempt yaratadi)
GET    /exams/{id}/my-attempts        # talaba o'z urinishlari
GET    /attempts/{id}                  # attempt detail (savol javoblari)
POST   /attempts/{id}/answer          {question_id, selected_option_ids|text_answer|...}
POST   /attempts/{id}/submit          # talaba submit qiladi
GET    /attempts/{id}/result          # natija (faqat submitted bo'lganda)

GET    /exams/{id}/attempts           # pedagog uchun ro'yxat (barcha attemptlar)
POST   /attempts/{id}/grade           # pedagog manual grade (essay/code/file)
POST   /attempts/{id}/invalidate      # admin/pedagog rad etadi
```

### 3.4 Background task

Celery task: `auto_submit_expired_attempts()` — har 1 daqiqada ishlaydi, `status='in_progress'` va `deadline_at < now` bo'lgan attemptlarni avto-submit qilish + grade.

### 3.5 Tests

- Attempt creation + answer submission
- Auto-grading har savol turi uchun (boundary cases)
- Time limit + auto-submit
- Multiple attempts (best score)
- Permission gating (faqat o'zining attempt'i)

---

## 4. Sub-faza 6c — Pedagog Exam Builder UI

### 4.1 Sahifa

`CourseBuilderView.vue` ga yangi tab: **Imtihonlar** (assignments tabidan keyin).

Yoki alohida sahifa: `/app/courses/:id/exams/:examId` — `ExamBuilderView.vue`.

### 4.2 Layout

```
[Imtihon sarlavhasi] [Status badge] [Publish tugma]
─────────────────────────────────────────────────
Settings panel:
  Type / Duration / Max attempts / Passing score
  Shuffle questions / Shuffle options / Show correct
  Proctoring: enabled / face_id / screen_share / tab_switch
  Schedule: available_from / available_until
─────────────────────────────────────────────────
Savollar (drag-drop):
  [1] Single choice — "X nima?"           [+ Edit] [Delete]
  [2] Multiple choice — "Y / Z tanlang"   [+ Edit] [Delete]
  [3] Essay — "Esse yozing"
  ...
─────────────────────────────────────────────────
[+ Savol qo'shish] dropdown:
  Single choice / Multiple choice / True/False
  Short text / Essay / Code / File upload
```

### 4.3 Komponentlar

- `ExamSettingsDrawer.vue` — settings panel
- `QuestionListView.vue` — drag-drop ro'yxat
- `QuestionDrawer.vue` — savol yaratish/tahrirlash (savol turiga qarab forma o'zgaradi)
- `QuestionOptionsEditor.vue` — single/multiple uchun options editor
- `CodeQuestionEditor.vue` — code question uchun
- `QuestionBankPicker.vue` — boshqa exam'lardan savol nusxalash (kelajak)

### 4.4 i18n keylar (~50)

`exam.*` namespace: title, settings, savol turi nomlari, status, validation xato'lari

---

## 5. Sub-faza 6d — Talaba Exam Lobby

### 5.1 Wireframe 09 lobby qismi

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   [Exam ID + Foto preview]    │   Exam info   │
│   ┌─────────────────────┐     │               │
│   │  [user face]        │     │  Title        │
│   │                     │     │  Type: Final  │
│   │                     │     │  Duration: 60 │
│   └─────────────────────┘     │  Questions: 30│
│   [📸 ID rasm olish]          │  Passing: 60% │
│                                │               │
│   System check:                │  Allowed     │
│   ✅ Kamera                    │  attempts: 1 │
│   ✅ Mikrofon                  │               │
│   ✅ Ekran ulashish ruxsati    │  Proctoring  │
│   ✅ Internet                  │  ENABLED     │
│   ❌ Boshqa tab'lar yopiq      │               │
│                                │   [Start →]   │
│                                │               │
└─────────────────────────────────────────────────┘
```

### 5.2 Sahifa va flow

**Route:** `/app/exams/:id/lobby`

Komponentlar:
- `ExamLobbyView.vue`
- `SystemCheckPanel.vue` — kamera/mic/ekran tekshiruv (Lobby live'dan o'xshash)
- `IdPhotoCapture.vue` — talaba o'z ID rasmi olish
- `MonitoringConsent.vue` — proctoring shartlariga rozilik

### 5.3 Validation

"Start" tugmasi faqat barcha checklar yashil bo'lganda aktiv:
1. ✅ Kamera ruxsat berildi
2. ✅ Mikrofon ruxsat berildi (require_face_id bo'lsa)
3. ✅ Screen share ruxsat berildi (require_screen_share bo'lsa)
4. ✅ ID rasm olindi
5. ✅ Monitoring rozilik berildi
6. ✅ Boshqa exam tab'lar yopiq

---

## 6. Sub-faza 6e — Exam taking UI (wireframe 09)

### 6.1 Wireframe 09 main qismi

```
┌─[ Timer 45:23 ]─[ Q 12/30 ]──[ Submit ]──┐
│                                            │
│  ┌─────────────┬──────────────────────┐    │
│  │ Q list      │ Q12: Algoritm nima?  │    │
│  │ ●Q1 ✓      │                       │    │
│  │ ●Q2 ✓      │ ○ Aniq qadamlar       │    │
│  │ ●Q3 ✓      │ ○ Tartibsiz amallar  │    │
│  │ ...        │ ● Strukturalangan jar│    │
│  │ ●Q12 ←     │                       │    │
│  │ ○Q13       │ [← Oldingi] [Keyingi →]│   │
│  │ ○Q14       │                       │    │
│  └─────────────┴──────────────────────┘    │
│                                            │
│  Proctoring camera (kichik kvadrat o'ng)   │
└─[ Ekran kuzatilmoqda ●REC ]──────────────┘
```

### 6.2 Komponentlar

- `ExamTakingView.vue` — fullscreen shell
- `ExamSidebar.vue` — savol navigatsiyasi (✓ javob bor, ○ yo'q, ● aktiv)
- `ExamTimer.vue` — countdown (oxirgi 5 daqiqa qizil)
- `QuestionView.vue` — universal savol render (turiga qarab)
  - `SingleChoiceQuestion.vue`
  - `MultipleChoiceQuestion.vue`
  - `TrueFalseQuestion.vue`
  - `ShortTextQuestion.vue`
  - `EssayQuestion.vue` (rich text)
  - `CodeQuestion.vue` (Monaco Editor)
  - `FileUploadQuestion.vue`
- `ExamProctoringWidget.vue` — kichik kamera preview (o'ng pastda)

### 6.3 Anti-cheat mexanizmlar

- **Fullscreen lock:** `requestFullscreen()` exam boshlanganda; chiqilsa violation event
- **Tab visibility:** `document.visibilitychange` — boshqa tab'ga o'tilsa violation
- **Copy/paste block:** `addEventListener('copy', 'paste', e => e.preventDefault())`
- **Right-click block:** `contextmenu` event preventDefault
- **DevTools detection:** `window.outerWidth - window.innerWidth > 200` (heuristic)
- **Browser back/forward:** `popstate` event — ogohlantirish + violation
- **Auto-save:** har 30 sekundda joriy javoblar serverga yuboriladi (`POST /attempts/{id}/answer`)

### 6.4 Submit flow

1. Talaba "Submit" tugmasini bosadi
2. Modal: "Imtihonni topshirasizmi? {N} ta savol javobsiz qoldi. Bu amalni qaytarib bo'lmaydi."
3. Tasdiqlanganda: `POST /attempts/{id}/submit`
4. Backend auto-grade qiladi, proctoring scoring yakunlanadi
5. Talaba result view'ga yo'naltiriladi
6. Fullscreen + proctoring tracking to'xtatiladi

---

## 7. Sub-faza 6f — Proctoring engine

### 7.1 Capture mexanizmlari

**Kamera screenshot:**
- Har 30 sekundda `<video>` element'dan `<canvas>` ga frame chizib JPEG sifatida serverga yuboramiz
- `POST /attempts/{id}/proctoring/snapshot` (multipart/form-data)
- Backend MinIO'ga saqlaydi, `exam.proctoring_snapshots` table'iga yozadi

**Ekran recording:**
- `navigator.mediaDevices.getDisplayMedia()` orqali ekran stream
- MediaRecorder API bilan 1-daqiqalik chunklarga bo'lib yozish
- Har chunk MinIO'ga upload
- `exam.proctoring_screen_chunks` table

**Audio anomaly:**
- Mic stream'dan har 10 sekundda RMS hisoblash
- Threshold (e.g., RMS > 0.3) ortib ketsa "loud_audio" event

### 7.2 Event tracking

**`exam.proctoring_events` jadval:**
```sql
id              BIGINT PK
attempt_id      BIGINT FK → attempts.id
event_type      ENUM(
  'tab_switch', 'visibility_lost', 'visibility_returned',
  'fullscreen_exit', 'fullscreen_entered',
  'copy_attempt', 'paste_attempt', 'context_menu',
  'face_lost', 'face_found', 'multiple_faces',
  'loud_audio', 'voice_detected',
  'devtools_opened', 'browser_resized',
  'network_loss', 'network_restored',
  'manual_flag'
) NOT NULL
severity        ENUM('info', 'warning', 'critical') NOT NULL
metadata        JSONB  -- event-specific data
occurred_at     TIMESTAMP NOT NULL
```

### 7.3 Face detection

- `face-api.js` (TensorFlow.js + lokal model, ~5MB) browser'ga yuklanadi
- Har 5 sekundda kamera frame analiz qilinadi:
  - `detectAllFaces(video, TinyFaceDetectorOptions)`
  - 0 ta yuz → `face_lost` event (10s davom etsa critical)
  - 1 ta yuz → OK
  - 2+ ta yuz → `multiple_faces` critical event

### 7.4 Violation scoring

**`backend/app/modules/exams/proctoring.py`:**

```python
VIOLATION_WEIGHTS = {
  'tab_switch': 10,
  'visibility_lost': 8,
  'fullscreen_exit': 15,
  'face_lost': 5,           # 1 marta — kritik emas, lekin 5+ marta — kritik
  'multiple_faces': 50,     # darhol critical
  'paste_attempt': 20,
  'devtools_opened': 30,
  'loud_audio': 3,
}

def compute_violation_score(attempt_id: int) -> int:
  """0-100 score qaytaradi. 80+ avtomatik flag."""
```

### 7.5 Real-time alert

- Talaba ekraniga toast: "Ogohlantirish: boshqa tab'ga o'tdingiz. Yana 3 marta qoidabuzarlik exam'ni rad etadi."
- WebSocket / SSE orqali pedagogga real-time alert (faza 9 polish)

### 7.6 Komponentlar

- `ProctoringEngine.vue` — top-level controller (audio, face, events bir joyda)
- `useFaceDetection.ts` — composable (face-api.js wrapper)
- `useScreenCapture.ts` — composable (getDisplayMedia + MediaRecorder)
- `useAntiCheat.ts` — composable (event listeners: visibility, copy, paste)

---

## 8. Sub-faza 6g — Admin: Review + Reports + HEMIS sync

### 8.1 Pedagog/Admin proctoring review

**Sahifa:** `/app/exams/:id/attempts/:attemptId/review`

```
[Talaba ism] [Exam title] [Score 78/100]
[Violation score: 65]  [● Flagged]

Tabs:
  Javoblar | Yozuv | Hodisalar | Snapshotlar | Qaror
─────────────────────────────────────────────────
Hodisalar timeline:
  ▼ 10:05:32 tab_switch (warning)
  ▼ 10:12:08 face_lost (critical) — 18s davom etdi
  ▼ 10:14:55 multiple_faces (critical)
  ▼ 10:18:20 paste_attempt (warning)
─────────────────────────────────────────────────
Snapshotlar (grid):
  [10:00] [10:05] [10:10] [10:15] [10:20] ...
─────────────────────────────────────────────────
Ekran recording: [▶ Play]
─────────────────────────────────────────────────
Qaror:
  ○ Tasdiqlash (score qoldiramiz)
  ○ Bekor qilish (attempt invalidated)
  ○ Qayta urinish berish
  Izoh: [___________________]
  [Saqlash]
```

### 8.2 Reports module (wireframe 18)

`AdminReportsView.vue` — yangi sahifa:
- 4 stat card: Jami imtihonlar / Jami urinishlar / O'rtacha ball / Pass rate
- Filter: kurs / muddat / type
- Jadval: kurs, exam, urinishlar soni, o'rtacha ball, pass rate, flagged count
- Export: CSV / PDF (CSV birinchi, PDF Phase 9)

### 8.3 HEMIS sync

`backend/app/modules/hemis_sync/exam_grades.py`:

```python
async def send_exam_grades(exam_id: int) -> SyncResult:
  """
  Exam tugagandan keyin HEMIS'ga grade yuborish.
  POST {hemis_base_url}/api/v1/exam-grades
  body: { exam_id, student_pinfl, score, status, completed_at }
  
  Faqat type='dak' yoki settings'da hemis_sync=true bo'lgan exam'lar uchun.
  """
```

Trigger:
- Exam status `published` → `archived` bo'lganda
- Yoki manual: `POST /exams/{id}/sync-hemis`

### 8.4 Komponentlar

- `ProctoringReviewView.vue`
- `EventTimeline.vue`
- `SnapshotGrid.vue`
- `ScreenRecordingPlayer.vue`
- `AttemptDecisionPanel.vue`
- `AdminReportsView.vue`
- `ReportsExportButton.vue`

---

## 9. Out of scope (kelajak fazalar)

| Element | Faza |
|---|---|
| Cloud screen recording (LiveKit Egress, S3) | Phase 7 Deploy |
| Real-time AI proctoring (gaze tracking, head pose) | Phase 9 AI |
| Question bank import (Excel/CSV/Moodle XML) | Phase 9 |
| Plagiat AI (essay javoblari uchun) | Phase 9 |
| Code question runner (Docker sandbox) | Phase 9 |
| Sertifikat blockchain verify | Phase 10 |
| Mobile native exam app (telefon orqali) | Phase 11 |

---

## 10. Acceptance kriteriyalari

1. Pedagog kurs ichida imtihon yaratadi, savollar qo'shadi, sozlamalarni o'zgartiradi, publish qiladi
2. Talaba imtihon ro'yxatini ko'radi, lobby'da system check'dan o'tadi, "Start" bosib boshlaydi
3. Imtihon UI fullscreen, anti-cheat aktiv, timer ishlaydi, savollar navigatsiyasi to'g'ri
4. Proctoring kamera+ekran capture qiladi, hodisalarni qayd etadi, face-api.js yuz tanish ishlaydi
5. Submit'da auto-grading hisoblaydi, manual grade kerak savollar pending'da qoladi
6. Pedagog attempt review'da hodisalar timeline'ini ko'radi, qaror qabul qiladi
7. Admin reports module statistikani ko'radi, CSV eksport qiladi
8. HEMIS sync DAK exam'lari uchun ishlaydi (mock yoki real)
9. Tests: 50+ yangi test (model, grading, proctoring scoring, HEMIS sync)
10. Type-check exit 0, user+admin build exit 0
11. i18n 4 locale parity (~80 yangi kalit × 4 = 320 yangi tarjima)

---

## 11. Texnik tanlovlar (qaror)

| Element | Tanlov |
|---|---|
| Camera capture | Browser-side MediaRecorder + JPEG snapshots, MinIO storage |
| Face detection | `face-api.js` (TFLite, lokal, ~5MB) |
| Code editor | Monaco Editor (VSCode core, ~1MB chunk) |
| Rich text (essay) | TipTap (ProseMirror, ~200KB) |
| Drag-drop | `vuedraggable@next` (Sortable.js wrapper) |
| Reports export | `papaparse` (CSV); PDF — Phase 9 |
| HEMIS sync | Mevjud `hemis_sync.py` ga yangi method qo'shish |

---

## 12. Riskli joylar

1. **Proctoring real-time alert** — WebSocket'siz kechikadi. SSE alternativ.
2. **Screen capture browser support** — Safari iOS'da yo'q. Mobile uchun fallback (only camera, no screen).
3. **Face-api.js performance** — past quvvatli laptopda CPU 50%+ ishlatishi mumkin. Throttle 5s → 10s qilamiz.
4. **MinIO storage size** — har attempt'ning kamera+ekran ~50-200MB. Phase 7'da S3 retention policy (3 oydan keyin compress yoki delete).
5. **Auto-submit timer drift** — frontend timer client-side. Server-side deadline_at sinxron, har 1 daqiqada celery task tekshiradi.
6. **HEMIS rate limit** — bulk DAK exam tugagach 100+ request. Throttle 10 req/s.

---

## 13. Phase 6 yakunidan keyin

Phase 6 ✅ → **Phase 7 (Deploy)** ga o'tamiz:
- K8s manifests + Helm charts
- LiveKit Egress (avto-recording)
- MinIO S3 production retention
- Grafana + Prometheus + Sentry
- HEMIS real endpoint sync (mock'dan real'ga)
- Backup + restore strategy
- Load testing (k6 / Locust)

---

*Plan tasdiqlangach, **6a (Backend models)** dan boshlaymiz. Har sub-faza oxirida:*
- *Backend tests green*
- *Frontend type-check + build*
- *Smoke HTTP*
- *Foydalanuvchi tasdig'i*
- *MD docs yangilash*
