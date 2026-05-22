# 12. Reports & Analytics (Hisobotlar) Moduli

## Maqsad

Real-time va tarixiy ma'lumotlar asosida hisobotlar, dashboardlar, eksport va custom hisobot konstruktor.

## Funksional talablar

### 1. Dashboardlar

#### Talaba dashboard
- Joriy progress (kurslar bo'yicha)
- Yaqinlashayotgan vazifalar
- Yaqinlashayotgan imtihonlar
- Live darslar
- O'rtacha baho (GPA)
- Davomat foizi
- Joriy balans (to'lov)

#### Pedagog dashboard
- Mening kurslarim
- Tekshirilmagan vazifalar
- Kelgusi live darslar
- Talabalar progressi (heatmap)
- Eng past o'zlashtiruvchilar
- Yangi savollar (forum)

#### Dekan dashboard
- Fakultet umumiy ko'rsatkichlar
- Talabalar soni (yo'nalish bo'yicha)
- O'zlashtirish ko'rsatkichlari
- Pedagoglar yuklamasi (1:50 nazorati)
- Akademik qarzdorlar

#### OTM Admin dashboard
- Umumiy talaba soni
- Faol foydalanuvchilar (DAU, MAU)
- Ko'rsatkichlar (ro'yxatdan o'tish, bitirish)
- To'lovlar dynamics
- Server holati
- API metrikalari

#### TSDIN nazoratchi dashboard
- Barcha OTMlar bo'yicha (read-only)
- Talabalar dinamikasi
- 1:50 nisbati monitoringi
- Imtihon natijalari
- Audit logi

### 2. Hisobotlar (built-in)

#### Akademik
- Talabalar ro'yxati va statusi
- O'zlashtirish (semestr/yil bo'yicha)
- Davomat
- Akademik qarzdorlar
- Bitiruvchilar
- Kursning effektivligi

#### Moliyaviy
- To'lovlar (sana bo'yicha)
- Qarzdorlar
- Refund tarixi
- Daromadlar (yo'nalish bo'yicha)
- Kontrakt holatlari

#### Operatsion
- Foydalanuvchilar aktivligi
- Sahifa yuklanish vaqti
- API errors
- Live darslar davomati
- Imtihon natijalari (statistik)

#### Komplaens (TSDIN/OTJBAT)
- 1:50 nisbati
- Talaba kontingenti
- Imtihon o'tkazilishi
- Hujjatlash to'liqligi

### 3. Custom hisobot konstruktor

- Drag & drop interface
- Manbalar tanlash (jadvallar)
- Filtrlar (sana, fakultet, status)
- Group by, aggregate (sum, avg, count)
- Visualizatsiya turi (jadval, chart, KPI)
- Saqlash va ulashish

### 4. Eksport formatlari

- **PDF** — bosma uchun
- **Excel (XLSX)** — tahrir uchun
- **CSV** — boshqa tizimlarga
- **JSON** — API integratsiyasi

### 5. Rejalashtirilgan hisobotlar

- Kunlik/haftalik/oylik
- Email orqali yuborish
- Sharers list

### 6. Real-time analytics

- WebSocket dashboard
- Live charts (Chart.js)
- Auto-refresh

## API Endpoints

```
# Dashboardlar
GET    /api/v1/dashboards/student/me
GET    /api/v1/dashboards/teacher/me
GET    /api/v1/dashboards/dean/{faculty_id}
GET    /api/v1/dashboards/admin/{org_id}
GET    /api/v1/dashboards/tsdin

# Akademik hisobotlar
GET    /api/v1/reports/academic/students
GET    /api/v1/reports/academic/grades
GET    /api/v1/reports/academic/attendance
GET    /api/v1/reports/academic/debtors
GET    /api/v1/reports/academic/graduates

# Moliyaviy hisobotlar
GET    /api/v1/reports/financial/payments
GET    /api/v1/reports/financial/debtors
GET    /api/v1/reports/financial/revenue

# Komplaens
GET    /api/v1/reports/compliance/teacher-ratio    # 1:50 tekshiruvi
GET    /api/v1/reports/compliance/student-quota    # 300/30 tekshiruvi

# Custom
GET    /api/v1/custom-reports
POST   /api/v1/custom-reports
GET    /api/v1/custom-reports/{id}
POST   /api/v1/custom-reports/{id}/run
GET    /api/v1/custom-reports/{id}/export?format=xlsx

# Rejalashtirilgan
POST   /api/v1/scheduled-reports
GET    /api/v1/scheduled-reports
DELETE /api/v1/scheduled-reports/{id}

# Real-time
WS     /ws/analytics                              # live metrics
```

## Database modellari

```sql
-- Custom hisobot
CREATE TABLE custom_reports (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    config JSONB NOT NULL,                         -- query, filters, columns, viz
    
    owner_id BIGINT REFERENCES users(id),
    is_public BOOLEAN DEFAULT FALSE,
    shared_with BIGINT[],                          -- user IDs
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Rejalashtirilgan hisobot
CREATE TABLE scheduled_reports (
    id BIGSERIAL PRIMARY KEY,
    report_id BIGINT REFERENCES custom_reports(id),
    
    schedule VARCHAR(50) NOT NULL,                 -- 'daily', 'weekly', 'monthly'
    day_of_week INT,                               -- 0-6 (haftalik uchun)
    day_of_month INT,                              -- 1-31 (oylik uchun)
    time_of_day TIME DEFAULT '08:00',
    
    recipients TEXT[],                             -- email addresses
    format VARCHAR(20) DEFAULT 'pdf',
    
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Materialized views (yuk kamaytirish uchun)
CREATE MATERIALIZED VIEW mv_student_progress AS
SELECT
    s.id as student_id,
    s.specialty_id,
    sp.name as specialty_name,
    s.current_semester,
    COUNT(DISTINCT e.course_id) as total_courses,
    COUNT(DISTINCT CASE WHEN e.completion_status = 'completed' THEN e.course_id END) as completed_courses,
    AVG(e.final_grade) as avg_grade,
    s.gpa
FROM students s
LEFT JOIN enrollments e ON e.user_id = s.user_id
LEFT JOIN specialties sp ON s.specialty_id = sp.id
GROUP BY s.id, s.specialty_id, sp.name, s.current_semester, s.gpa;

CREATE INDEX idx_mv_student_progress_specialty ON mv_student_progress(specialty_id);

-- Refresh: har soat (Celery)
```

## Komplaens hisobotlar (CRITICAL)

### 1:50 nisbati tekshiruvi (VM 559-qaror Nizom 26-band)

```python
# app/modules/reports/compliance.py

async def check_teacher_ratio(organization_id: int) -> dict:
    """
    VM 559-qaror Nizom 26-bandi: 
    1 pedagog faqat 50 talabaga dars o'tishi mumkin
    """
    # Pedagoglar va ularning yuklamalari
    teachers = await db.execute("""
        SELECT 
            u.id, u.full_name,
            COUNT(DISTINCT e.user_id) as student_count
        FROM users u
        JOIN courses c ON c.primary_author_id = u.id
        JOIN enrollments e ON e.course_id = c.id
        WHERE u.id IN (
            SELECT user_id FROM user_roles ur 
            JOIN roles r ON r.id = ur.role_id 
            WHERE r.code = 'teacher'
        )
        AND c.organization_id = :org_id
        AND e.completion_status = 'in_progress'
        GROUP BY u.id, u.full_name
    """, {"org_id": organization_id})
    
    violations = []
    for teacher in teachers:
        if teacher.student_count > 50:
            violations.append({
                "teacher_id": teacher.id,
                "teacher_name": teacher.full_name,
                "student_count": teacher.student_count,
                "exceeds_by": teacher.student_count - 50,
            })
    
    return {
        "total_teachers": len(teachers),
        "compliant": len(teachers) - len(violations),
        "violations": violations,
        "compliance_percent": ((len(teachers) - len(violations)) / len(teachers) * 100) if teachers else 100,
    }


async def check_student_quota(specialty_id: int, academic_year: str) -> dict:
    """
    VM 559-qaror Nizom 15-bandi:
    Bakalavriat - 300, Magistratura - 30 (mahalliy)
    """
    specialty = await get_specialty(specialty_id)
    
    # Mahalliy talabalar (xorijiy hisobga olinmaydi)
    count = await db.execute("""
        SELECT COUNT(*) as cnt
        FROM students
        WHERE specialty_id = :sid
        AND enrollment_year = :year
        AND is_foreign = FALSE
        AND status IN ('active', 'enrolled')
    """, {"sid": specialty_id, "year": academic_year})
    
    max_allowed = 300 if specialty.level == "bachelor" else 30
    
    return {
        "specialty_id": specialty_id,
        "specialty_name": specialty.name,
        "level": specialty.level,
        "current_count": count,
        "max_allowed": max_allowed,
        "is_compliant": count <= max_allowed,
        "available_slots": max(0, max_allowed - count),
    }
```

## Excel eksport (openpyxl)

```python
# app/utils/excel.py
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

async def export_students_xlsx(filters: dict) -> bytes:
    students = await get_students(filters)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Talabalar"
    
    # Header
    headers = ["ID", "F.I.Sh.", "Yo'nalish", "Kurs", "GPA", "Status"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4F46E5")
        cell.alignment = Alignment(horizontal="center")
    
    # Data
    for row, student in enumerate(students, 2):
        ws.cell(row=row, column=1, value=student.student_id_number)
        ws.cell(row=row, column=2, value=student.full_name)
        ws.cell(row=row, column=3, value=student.specialty.name)
        ws.cell(row=row, column=4, value=student.current_semester)
        ws.cell(row=row, column=5, value=float(student.gpa or 0))
        ws.cell(row=row, column=6, value=student.status)
    
    # Auto-width
    for col in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_length + 2
    
    # Save to bytes
    from io import BytesIO
    output = BytesIO()
    wb.save(output)
    return output.getvalue()
```

## Frontend dashboard (Vue + Chart.js)

```vue
<!-- views/dashboard/StudentDashboard.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Bar, Line, Doughnut } from 'vue-chartjs'
import { useDashboardApi } from '@/api/dashboard'

const dashboard = ref(null)
const api = useDashboardApi()

onMounted(async () => {
  dashboard.value = await api.getStudentDashboard()
})
</script>

<template>
  <div v-if="dashboard" class="container mx-auto p-6">
    <!-- KPI cards -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <KpiCard
        title="O'rtacha baho (GPA)"
        :value="dashboard.gpa.toFixed(2)"
        icon="academic-cap"
        color="blue"
      />
      <KpiCard
        title="Davomat"
        :value="`${dashboard.attendance}%`"
        icon="calendar"
        color="green"
      />
      <KpiCard
        title="Tugatilgan kurslar"
        :value="`${dashboard.completed}/${dashboard.total}`"
        icon="check-circle"
        color="purple"
      />
      <KpiCard
        title="Joriy balans"
        :value="formatMoney(dashboard.balance)"
        icon="cash"
        color="orange"
      />
    </div>
    
    <!-- Charts -->
    <div class="grid grid-cols-2 gap-6">
      <Card title="Kurslar progressi">
        <Bar :data="coursesProgressData" />
      </Card>
      <Card title="Baholar dinamikasi">
        <Line :data="gradesTimelineData" />
      </Card>
    </div>
    
    <!-- Yaqinlashayotgan deadlines -->
    <Card title="Yaqinlashayotgan vazifalar" class="mt-6">
      <DeadlineList :items="dashboard.upcoming" />
    </Card>
  </div>
</template>
```

## Acceptance kriteriyalar

- [ ] 5 ta dashboard (talaba, pedagog, dekan, admin, TSDIN)
- [ ] 15+ built-in hisobot
- [ ] Custom hisobot konstruktor
- [ ] PDF / Excel / CSV eksport
- [ ] Rejalashtirilgan hisobotlar
- [ ] Real-time WebSocket dashboard
- [ ] **1:50 nisbati monitoring** (VM 559)
- [ ] **Talaba kvota tekshiruvi** (300/30)
- [ ] Materialized views (performance)
- [ ] Test coverage ≥ 70%
