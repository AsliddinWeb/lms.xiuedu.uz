# 06. Courses (Kurslar) Moduli

## Maqsad

Kurslarni yaratish, modul/dars tuzilmasini boshqarish, talabalarga taqdim etish.

## Funksional talablar

### 1. Kurs strukturasi

```
Course (Kurs)
  └── Module (Modul / Bo'lim)
        └── Lesson (Dars)
              ├── Content (kontent)
              ├── Activities (vazifalar, testlar)
              └── Live Sessions (sinxron)
```

### 2. Kurs turlari

- **Akademik kurs** — Curriculum'dagi fanga bog'liq
- **Open kurs** — Hech qaysi yo'nalishga bog'lanmagan (ochiq)
- **Microlearning** — Kichik, fokuslangan
- **Specialization** — Ko'p kursdan iborat (path)

### 3. Kursni yaratish

- Mavzu, tavsif, maqsadlar
- Davomiyligi (haftalar)
- Tegishli fan
- Mualliflar
- Til
- Banner / cover image
- Trailer video (ixtiyoriy)
- Pre-rekvizitlar

### 4. Modul va dars

**Modul:**
- Nom, tavsif, tartib raqami
- Boshlanish va tugash sanalari (ixtiyoriy)
- Dars ro'yxati

**Dars (Lesson):**
- Nom, qisqacha tavsif
- Kontent (video, matn, SCORM)
- O'rganish vaqti (taxminiy)
- Vazifalar
- Testlar
- Live sessiyalar
- Qulflash logikasi (avvalgi tugagandan keyin ochiladi)

### 5. Kursga yozilish (enrollment)

- Avtomatik (curriculum'ga muvofiq)
- Qo'lda (admin/o'qituvchi qo'shadi)
- Self-enrollment (Open kurslarda)
- Cohort-based (guruh asosida)

### 6. O'qish jarayoni

- Talaba kontentni o'rganadi
- Progress avtomatik saqlanadi
- Vazifalarni topshiradi
- Testlardan o'tadi
- Live darslarda ishtirok etadi
- Kurs oxirida sertifikat oladi

### 7. O'qituvchi ko'rinishi

- Talabalar ro'yxati va progresslar
- Vazifalarni baholash
- Imtihonlar
- Forum / Q&A
- Statistika
- Live dars rejalashtirish

## API Endpoints

```
# Kurslar
GET    /api/v1/courses                        # ro'yxat (filter)
POST   /api/v1/courses                        # yaratish
GET    /api/v1/courses/{id}
PATCH  /api/v1/courses/{id}
DELETE /api/v1/courses/{id}
POST   /api/v1/courses/{id}/publish
POST   /api/v1/courses/{id}/unpublish
POST   /api/v1/courses/{id}/duplicate

# Modullar
GET    /api/v1/courses/{id}/modules
POST   /api/v1/courses/{id}/modules
PATCH  /api/v1/modules/{id}
DELETE /api/v1/modules/{id}
POST   /api/v1/courses/{id}/modules/reorder

# Darslar
GET    /api/v1/modules/{id}/lessons
POST   /api/v1/modules/{id}/lessons
GET    /api/v1/lessons/{id}
PATCH  /api/v1/lessons/{id}
DELETE /api/v1/lessons/{id}
POST   /api/v1/modules/{id}/lessons/reorder

# Kursga yozilish
POST   /api/v1/courses/{id}/enroll            # ro'yxatdan o'tish
DELETE /api/v1/courses/{id}/enroll            # bekor qilish
GET    /api/v1/courses/{id}/students          # talabalar (o'qituvchi uchun)
POST   /api/v1/courses/{id}/students          # talaba qo'shish
DELETE /api/v1/courses/{id}/students/{user_id}

# Bulk enroll
POST   /api/v1/courses/{id}/bulk-enroll       # guruh / curriculum bo'yicha

# Talaba progresslari
GET    /api/v1/courses/{id}/my-progress       # o'zining
GET    /api/v1/courses/{id}/students/{user_id}/progress  # o'qituvchi uchun

# Lesson progress
POST   /api/v1/lessons/{id}/start
POST   /api/v1/lessons/{id}/complete
POST   /api/v1/lessons/{id}/progress          # vaqti-vaqti bilan saqlash

# Forum (kurs ichida)
GET    /api/v1/courses/{id}/forum
POST   /api/v1/courses/{id}/forum/topics
GET    /api/v1/forum/topics/{id}/posts
POST   /api/v1/forum/topics/{id}/posts

# Sertifikat
GET    /api/v1/courses/{id}/my-certificate
POST   /api/v1/courses/{id}/issue-certificate # o'qituvchi
```

## Database modellari

```sql
-- Kurs
CREATE TABLE courses (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50),
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    
    subject_id BIGINT REFERENCES subjects(id),    -- fanga bog'lash
    organization_id BIGINT REFERENCES organizations(id),
    
    type VARCHAR(20) NOT NULL,                     -- 'academic', 'open', 'micro'
    level VARCHAR(20),                             -- 'beginner', 'intermediate', 'advanced'
    language VARCHAR(10) DEFAULT 'uz-lat',
    
    cover_image_url TEXT,
    trailer_video_url TEXT,
    
    duration_weeks INT,
    estimated_hours INT,
    
    -- Pre-rekvizitlar
    prerequisites_text TEXT,
    prerequisite_courses BIGINT[],
    
    -- Maqsadlar va o'rganadigan narsalar
    objectives JSONB,                              -- ['maqsad 1', ...]
    skills_gained JSONB,
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft',            -- 'draft', 'published', 'archived'
    published_at TIMESTAMP,
    
    -- Yozilish parametrlari
    enrollment_type VARCHAR(20) DEFAULT 'auto',    -- 'auto', 'manual', 'open'
    max_students INT,
    
    -- Sertifikat
    certificate_template_id BIGINT,
    
    -- Mualliflar
    primary_author_id BIGINT REFERENCES users(id),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_courses_subject ON courses(subject_id);
CREATE INDEX idx_courses_org ON courses(organization_id);
CREATE INDEX idx_courses_status ON courses(status);

-- Kurs mualliflari (many-to-many)
CREATE TABLE course_authors (
    course_id BIGINT REFERENCES courses(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id),
    role VARCHAR(20) DEFAULT 'co_author',          -- 'primary', 'co_author', 'reviewer'
    PRIMARY KEY (course_id, user_id)
);

-- Modul
CREATE TABLE modules (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    order_index INT NOT NULL,
    available_from TIMESTAMP,
    available_until TIMESTAMP,
    is_locked BOOLEAN DEFAULT FALSE,
    unlock_after_module_id BIGINT REFERENCES modules(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Dars
CREATE TABLE lessons (
    id BIGSERIAL PRIMARY KEY,
    module_id BIGINT REFERENCES modules(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    order_index INT NOT NULL,
    
    -- Asosiy kontent
    primary_content_id BIGINT REFERENCES content_items(id),
    
    -- Qo'shimcha
    additional_contents BIGINT[],                  -- content IDlari
    
    estimated_minutes INT,
    is_locked BOOLEAN DEFAULT FALSE,
    unlock_after_lesson_id BIGINT REFERENCES lessons(id),
    
    is_required_for_completion BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Kursga yozilish
CREATE TABLE enrollments (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT REFERENCES courses(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP DEFAULT NOW(),
    enrollment_method VARCHAR(20),                 -- 'auto', 'manual', 'self'
    enrolled_by BIGINT REFERENCES users(id),
    
    completion_status VARCHAR(20) DEFAULT 'in_progress',  -- 'in_progress', 'completed', 'failed', 'dropped'
    completed_at TIMESTAMP,
    
    final_grade NUMERIC(5, 2),
    certificate_issued BOOLEAN DEFAULT FALSE,
    certificate_url TEXT,
    
    UNIQUE(course_id, user_id)
);

CREATE INDEX idx_enrollments_user ON enrollments(user_id);
CREATE INDEX idx_enrollments_course ON enrollments(course_id);

-- Talaba progresslari (lesson)
CREATE TABLE lesson_progress (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    lesson_id BIGINT REFERENCES lessons(id) ON DELETE CASCADE,
    
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    progress_percent NUMERIC(5, 2) DEFAULT 0,      -- 0-100
    time_spent_seconds INT DEFAULT 0,
    
    last_position JSONB,                           -- video position, scroll, etc.
    
    UNIQUE(user_id, lesson_id)
);

-- Sertifikatlar
CREATE TABLE certificates (
    id BIGSERIAL PRIMARY KEY,
    course_id BIGINT REFERENCES courses(id),
    user_id BIGINT REFERENCES users(id),
    certificate_number VARCHAR(50) UNIQUE NOT NULL,
    issued_at TIMESTAMP DEFAULT NOW(),
    pdf_url TEXT,
    qr_code_url TEXT,
    verification_code VARCHAR(100) UNIQUE,        -- onlayn tekshirish uchun
    final_grade NUMERIC(5, 2),
    completion_date DATE
);
```

## Course progress hisoblash

```python
# app/modules/courses/progress_service.py

class ProgressService:
    async def calculate_course_progress(
        self, user_id: int, course_id: int
    ) -> CourseProgress:
        # Kursdagi barcha required darslar
        lessons = await self.repo.get_required_lessons(course_id)
        total = len(lessons)
        
        if total == 0:
            return CourseProgress(percent=0, completed=0, total=0)
        
        # Talabaning tugatgan darslari
        completed = await self.repo.count_completed_lessons(
            user_id=user_id,
            lesson_ids=[l.id for l in lessons],
        )
        
        percent = round((completed / total) * 100, 2)
        
        # Agar 100% bo'lsa — kursni tugatgan deb belgilash
        if percent == 100:
            await self._mark_course_completed(user_id, course_id)
        
        return CourseProgress(
            percent=percent,
            completed=completed,
            total=total,
        )
    
    async def _mark_course_completed(self, user_id: int, course_id: int):
        enrollment = await self.repo.get_enrollment(user_id, course_id)
        if enrollment.completion_status != 'completed':
            enrollment.completion_status = 'completed'
            enrollment.completed_at = datetime.utcnow()
            await self.repo.save(enrollment)
            
            # Sertifikat yaratish (Celery task)
            from app.workers.certificate import generate_certificate
            generate_certificate.delay(user_id, course_id)
```

## Frontend — Kurs sahifasi

```vue
<!-- views/courses/CourseView.vue -->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCourseStore } from '@/stores/courses'

const route = useRoute()
const courses = useCourseStore()
const courseId = Number(route.params.id)

onMounted(async () => {
  await courses.fetchCourse(courseId)
  await courses.fetchProgress(courseId)
})

const course = computed(() => courses.current)
const progress = computed(() => courses.progress)
</script>

<template>
  <div v-if="course" class="container mx-auto px-4 py-6">
    <!-- Header -->
    <div class="flex justify-between items-start mb-8">
      <div>
        <h1 class="text-3xl font-bold">{{ course.title }}</h1>
        <p class="text-gray-600 mt-2">{{ course.description }}</p>
      </div>
      <div class="text-right">
        <ProgressRing :percent="progress?.percent || 0" />
        <p class="text-sm mt-2">{{ progress?.completed }} / {{ progress?.total }}</p>
      </div>
    </div>
    
    <!-- Modules accordion -->
    <div class="space-y-4">
      <ModuleAccordion
        v-for="module in course.modules"
        :key="module.id"
        :module="module"
      />
    </div>
  </div>
</template>
```

## Acceptance kriteriyalar

- [ ] Kurs CRUD
- [ ] Modul va dars boshqaruvi
- [ ] Drag & drop tartiblash
- [ ] Lessoniada turli content turlari
- [ ] Yozilish (auto, manual, self)
- [ ] Bulk enroll (guruh)
- [ ] Progress kuzatuvi
- [ ] Sertifikat avtomatik yaratish
- [ ] Forum / Q&A
- [ ] Statistika va analitika
- [ ] Kurs sahifasi (talaba ko'rinishi)
- [ ] O'qituvchi paneli
- [ ] Test coverage ≥ 80%
