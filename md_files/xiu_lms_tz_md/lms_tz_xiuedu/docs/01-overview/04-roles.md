# 04. Foydalanuvchi Rollari va Ruxsatlar

## Rollar ierarxiyasi

```
Super Administrator (platform owner)
    │
    ├── OTM Administrator (har bir OTM uchun)
    │       │
    │       ├── Dekanat / O'quv bo'limi
    │       │       │
    │       │       └── Kafedra mudiri
    │       │               │
    │       │               └── Pedagog / O'qituvchi
    │       │                       │
    │       │                       └── Talabalar
    │       │
    │       └── Texnik qo'llab-quvvatlash
    │
    ├── Tashqi nazoratchi (TSDIN)
    └── Mehmon / Auditor
```

## Asosiy rollar va ruxsatlar

### 1. Super Administrator
**Maqsad:** Butun platformani boshqaradi (single-tenant'da — XIU darajasida)

**Ruxsatlar:**
- `platform.*` — barcha tizim ruxsatlari
- Universitet sozlamalari (XIU edit, HEMIS integratsiyasi)
- Global sozlamalar (1:50 normativi, qabul cheklovlari)
- Tizim monitoringi va loglar
- Foydalanuvchilar bo'yicha audit

> **Single-tenant eslatma:** Implementatsiyada `super_admin` va `otm_admin` rollari
> funksional teng (faqat bitta universitet bor). `otm_admin` demo akkaunt
> olib tashlandi, lekin schema'da rol saqlanadi.

### 2. OTM Administrator
**Maqsad:** Bitta OTM doirasidagi barcha jarayonlarni boshqaradi (single-tenant'da super_admin bilan teng)

**Ruxsatlar:**
- `org.{otm_id}.*` — OTM ichidagi barcha
- Foydalanuvchilarni boshqarish
- Akademik tuzilma (fakultet, kafedra)
- Toʻlov-kontrakt qiymatini belgilash
- Hisobotlar va analitika

### 3. Dekan / O'quv bo'limi
**Maqsad:** Fakultet darajasidagi ta'lim jarayoni

**Ruxsatlar:**
- `faculty.{id}.read`
- `faculty.{id}.students.manage`
- `faculty.{id}.curriculum.manage`
- `faculty.{id}.schedule.manage`
- `faculty.{id}.reports.view`

### 4. Kafedra mudiri
**Maqsad:** Kafedra darajasidagi pedagoglar va fanlar

**Ruxsatlar:**
- `department.{id}.read`
- `department.{id}.teachers.manage`
- `department.{id}.subjects.manage`
- `department.{id}.workload.assign`

### 5. Pedagog (Professor-o'qituvchi)
**Maqsad:** Kontent yaratish, dars o'tish, baholash

**Ruxsatlar:**
- `course.{id}.edit` — o'zining kurslari
- `course.{id}.content.create`
- `course.{id}.assignments.grade`
- `course.{id}.exams.create`
- `course.{id}.live.host`
- `student.grade.view` (o'z guruhi)

**Cheklov:** Bir vaqtning o'zida 50 dan ortiq talaba (1:50)

### 6. Talaba
**Maqsad:** Kursni o'rganish, vazifalarni topshirish

**Ruxsatlar:**
- `course.{id}.read` (yozilgan kurslar)
- `assignment.submit`
- `exam.attempt`
- `live.join`
- `profile.edit` (faqat o'zining)
- `payment.view` (o'z to'lovlari)

### 7. Xorijiy pedagog (Mehmon)
**Maqsad:** Masofadan dars o'tish

**Ruxsatlar:**
- `course.{id}.live.host` (kelishilgan kurslar)
- `course.{id}.content.view`
- Cheklov: an'anaviy talablar tatbiq etilmaydi

### 8. Tashqi nazoratchi (TSDIN)
**Maqsad:** Faqat o'qish — monitoring uchun

**Ruxsatlar:**
- `monitoring.read.*`
- `audit.read.*`
- `reports.read.*`
- **Hech qanday yozish ruxsati yo'q**

### 9. Texnik qo'llab-quvvatlash
**Maqsad:** Foydalanuvchilarga yordam

**Ruxsatlar:**
- `users.read` (PII'siz)
- `tickets.manage`
- `password.reset.request`
- Audit log: barcha harakatlari yoziladi

### 10. Mehmon (Auditor / Visitor)
**Maqsad:** Demo materiallarni ko'rish

**Ruxsatlar:**
- `public.courses.view`
- Hech qanday autentifikatsiyasiz

## Ruxsat formati (RBAC)

Format: `{resource}.{action}` yoki `{scope}.{resource}.{action}`

**Misollar:**
- `course.create`
- `course.{id}.edit`
- `student.grade.view`
- `org.{otm_id}.users.manage`
- `platform.*` (super admin)

## Permission matritsasi

| Resurs | Talaba | Pedagog | Kafedra | Dekan | OTM Admin | Super |
|--------|--------|---------|---------|-------|-----------|-------|
| Profil ko'rish | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Kurs yaratish | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Imtihon o'tkazish | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Live dars hosting | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Bahoni o'zgartirish | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Talabani qabul qilish | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| To'lov-kontrakt | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Sistem sozlamalari | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Audit log | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

## Ruxsat tekshirish (Backend)

```python
# FastAPI dependency
@router.post("/courses")
async def create_course(
    data: CourseCreate,
    user: User = Depends(require_permission("course.create"))
):
    ...
```

## Ruxsat tekshirish (Frontend)

```vue
<template>
  <button v-if="hasPermission('course.create')" @click="createCourse">
    Yangi kurs
  </button>
</template>

<script setup>
import { usePermissions } from '@/composables/usePermissions'
const { hasPermission } = usePermissions()
</script>
```

## Audit logi

Har bir ruxsatdan foydalanish quyidagi formatda log qilinadi:

```json
{
  "user_id": 123,
  "permission": "course.{id}.edit",
  "resource": "course:456",
  "action": "PUT /courses/456",
  "ip": "1.2.3.4",
  "user_agent": "...",
  "timestamp": "2026-04-30T10:00:00Z",
  "success": true
}
```
