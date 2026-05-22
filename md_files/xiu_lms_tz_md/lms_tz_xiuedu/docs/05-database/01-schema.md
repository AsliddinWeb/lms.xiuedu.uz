# 01. Database Schema (To'liq)

## Maqsad

Barcha modullar uchun PostgreSQL'da yagona schema. Bu fayl barcha jadvallarni bir joyda jamlaydi (modul fayllarida ham bor, lekin shu yerda ER xaritasi).

## ER xarita (yuqori darajadagi)

```
┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  organizations  │────<│   faculties     │────<│   departments   │
└────────┬────────┘      └──────────────────┘      └──────────────────┘
         │                                                  │
         │                                                  ↓
         │                                         ┌──────────────────┐
         │                                         │   specialties   │
         │                                         └────────┬────────┘
         │                                                  │
         ↓                                                  ↓
┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│     users       │────<│   user_roles    │────<│      roles       │
└────────┬────────┘      └──────────────────┘      └──────────────────┘
         │
         ├──────<┌──────────────────┐
         │       │    profiles      │
         │       └──────────────────┘
         │
         ├──────<┌──────────────────┐         ┌──────────────────┐
         │       │     students    │────────>│    curricula    │
         │       └────────┬────────┘         └──────────────────┘
         │                │
         │                ↓
         │       ┌──────────────────┐         ┌──────────────────┐
         │       │   enrollments   │────────>│     courses     │
         │       └──────────────────┘         └────────┬────────┘
         │                                             │
         │                                             ↓
         │                                    ┌──────────────────┐
         │                                    │     lessons     │
         │                                    └──────────────────┘
         │
         ├──────<┌──────────────────┐
         │       │   assignments   │
         │       └────────┬────────┘
         │                ↓
         │       ┌──────────────────┐
         │       │   submissions   │
         │       └──────────────────┘
         │
         ├──────<┌──────────────────┐
         │       │      exams      │
         │       └────────┬────────┘
         │                ↓
         │       ┌──────────────────┐
         │       │  exam_attempts  │────>┌────────────────────┐
         │       └──────────────────┘    │ proctoring_sessions│
         │                                └────────────────────┘
         │
         ├──────<┌──────────────────┐
         │       │   contracts     │
         │       └────────┬────────┘
         │                ↓
         │       ┌──────────────────┐
         │       │    payments     │
         │       └──────────────────┘
         │
         └──────<┌──────────────────┐
                 │  notifications  │
                 └──────────────────┘
```

## Schema yaratish tartibi

Migrationlar quyidagi tartibda bo'lishi kerak (foreign key dependency'ga qarab):

1. **Core** — organizations, users, roles, permissions
2. **Academic struktura** — faculties, departments, specialties, subjects, curricula
3. **Profile** — profiles, students, teachers
4. **Enrollment** — enrollment_orders, enrollments
5. **Content** — content_items, scorm_packages
6. **Courses** — courses, modules, lessons
7. **Assignments** — assignments, submissions, rubrics
8. **Exams** — question_banks, questions, exams, exam_attempts
9. **Proctoring** — proctoring_sessions, proctoring_events (partition)
10. **Live** — live_sessions, live_attendance
11. **Payments** — contracts, payments
12. **Communications** — chats, messages, notifications
13. **Audit** — audit_logs (partition)
14. **Integrations** — hemis_credentials, oneid_links

## Schema'ning to'liq matni

Quyidagi fayllarda har bir modul uchun SQL DDL keltirilgan:

| Modul | Fayl |
|-------|------|
| Auth | [03-modules/01-auth.md](../03-modules/01-auth.md) |
| Users & RBAC | [03-modules/02-users-rbac.md](../03-modules/02-users-rbac.md) |
| Academic | [03-modules/03-academic.md](../03-modules/03-academic.md) |
| Enrollment | [03-modules/04-enrollment.md](../03-modules/04-enrollment.md) |
| Content | [03-modules/05-content.md](../03-modules/05-content.md) |
| Courses | [03-modules/06-courses.md](../03-modules/06-courses.md) |
| Assignments | [03-modules/07-assignments.md](../03-modules/07-assignments.md) |
| Live Classes | [03-modules/08-live-classes.md](../03-modules/08-live-classes.md) |
| Exams & Proctoring | [03-modules/09-exams-proctoring.md](../03-modules/09-exams-proctoring.md) |
| Payments | [03-modules/10-payments.md](../03-modules/10-payments.md) |
| Communications | [03-modules/11-communications.md](../03-modules/11-communications.md) |

## Naming conventions

- **Jadval nomlari:** ko'plik shaklda, snake_case (`users`, `course_lessons`)
- **Junction (M2M) jadvallari:** alfabit tartib (`user_courses`, `course_tags`)
- **Foreign key:** `{table_singular}_id` (`user_id`, `course_id`)
- **Boolean:** `is_*` yoki `has_*` (`is_active`, `has_proctoring`)
- **Timestamp:** `*_at` (`created_at`, `published_at`)
- **Status enum:** matn (`'active'`, `'inactive'`) — string, enum emas
- **Indexlar:** `idx_{table}_{column(s)}`
- **Unique constraint:** `uq_{table}_{column}`

## Common columns (har bir asosiy jadvalda)

```sql
-- Audit columns
created_at TIMESTAMP NOT NULL DEFAULT NOW(),
updated_at TIMESTAMP,
created_by BIGINT REFERENCES users(id),
updated_by BIGINT REFERENCES users(id),

-- Soft delete (kerak bo'lganda)
deleted_at TIMESTAMP,

-- Versioning (optimistic locking, kerak bo'lganda)
version INT DEFAULT 1
```

## Multi-tenancy

Har bir asosiy jadval `organization_id` ga ega:

```sql
-- RLS policy misoli
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON courses
    USING (organization_id = current_setting('app.current_organization_id')::bigint);
```

Backend connection oching'da `SET LOCAL app.current_organization_id = ...` qo'yiladi.

## Performance optimizations

### Indexlar

Har bir jadvalda quyidagi tipdagi indekslar bo'lishi kerak:

```sql
-- Foreign key indexlari (avtomatik EMAS)
CREATE INDEX idx_courses_organization ON courses(organization_id);

-- Filter columns
CREATE INDEX idx_courses_status ON courses(status) WHERE status = 'published';

-- Composite (eng tez-tez ishlatiladigan kombinatsiyalar)
CREATE INDEX idx_enrollments_user_status ON enrollments(user_id, completion_status);

-- Search (full-text)
CREATE INDEX idx_courses_search ON courses USING gin(to_tsvector('uzbek', title || ' ' || description));

-- JSON queries
CREATE INDEX idx_courses_metadata ON courses USING gin(metadata jsonb_path_ops);
```

### Partitioning

Katta jadvallar (yiliga 100M+ row):

```sql
-- audit_logs (sana bo'yicha, oylik)
CREATE TABLE audit_logs (...) PARTITION BY RANGE (created_at);

-- proctoring_events (sana bo'yicha, oylik)
CREATE TABLE proctoring_events (...) PARTITION BY RANGE (timestamp);

-- xAPI statements (sana bo'yicha, oylik)
CREATE TABLE xapi_statements (...) PARTITION BY RANGE (stored);

-- Avtomatik partition yaratish (pg_partman)
CREATE EXTENSION pg_partman;
SELECT partman.create_parent('public.audit_logs', 'created_at', 'native', 'monthly');
```

### Materialized views

```sql
-- Talaba progress
CREATE MATERIALIZED VIEW mv_student_progress AS ...;

-- Kurs statistikasi
CREATE MATERIALIZED VIEW mv_course_stats AS ...;

-- Refresh: har soat (Celery)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_student_progress;
```

## Backup va recovery

### WAL archiving
```bash
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://bucket/wal/%f'
```

### pg_dump kunlik
```bash
pg_dump -Fc -Z9 lms_db > backup_$(date +%Y%m%d).dump
aws s3 cp backup_*.dump s3://bucket/backups/
```

### PITR (Point-in-Time Recovery)
WAL archive + base backup orqali har qanday vaqtga qaytarish mumkin.

## Encryption

### Sensitive columns (column-level)
```sql
-- pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- PINFL — shifrlangan saqlash
ALTER TABLE profiles ADD COLUMN pinfl_encrypted BYTEA;

-- Yozish
UPDATE profiles SET pinfl_encrypted = pgp_sym_encrypt(pinfl, 'secret_key');

-- O'qish
SELECT pgp_sym_decrypt(pinfl_encrypted, 'secret_key') FROM profiles;
```

### TLS
- Connection: `sslmode=require` minimum, `verify-full` production'da

## Acceptance kriteriyalar

- [ ] Schema barcha modullar uchun yaratilgan
- [ ] Indexlar barcha kerakli ustunlarda
- [ ] Partitioning sozlangan
- [ ] Materialized views (statistika uchun)
- [ ] Foreign keys cascade bilan
- [ ] Multi-tenancy RLS yoki schema-per-tenant
- [ ] Backup va PITR
- [ ] Sensitive ma'lumotlar shifrlangan
