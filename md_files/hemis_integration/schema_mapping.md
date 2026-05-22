# HEMIS → LMS schema mapping

Bu hujjat HEMIS OpenAPI schema'larining bizning DB modellariga qanday tushishini ko'rsatadi.
Phase 10b (Models refactor) ushbu jadval asosida bajariladi.

## 1. Student → User + Profile

| HEMIS field            | Python type     | Bizning field                          | Migration kerakmi  | Eslatma                                              |
|------------------------|-----------------|----------------------------------------|--------------------|------------------------------------------------------|
| `id`                   | `int`           | `users.hemis_id` (yangi)               | ✅ ADD NOT NULL+UQ | Primary HEMIS identifier                              |
| `student_id_number`    | `str?`          | `users.hemis_login` (yangi)            | ✅ ADD UNIQUE      | Auth uchun (`POST /v1/auth/login` login field)        |
| `passport_pin`         | `str?` (14ch)   | `users.pinfl` (yangi)                  | ✅ ADD UNIQUE      | Milliy ID                                             |
| `first_name`           | `str`           | `profiles.first_name`                  | —                  | Bor                                                   |
| `second_name`          | `str`           | `profiles.last_name`                   | —                  | HEMIS "second_name" = familiya                        |
| `third_name`           | `str`           | `profiles.middle_name`                 | —                  | Otasining ismi                                        |
| `full_name`            | `str`           | `users.full_name`                      | —                  | HEMIS hisoblangan, biz cache qilamiz                  |
| `short_name`           | `str`           | (skip)                                 | —                  | "First S.S." formatda — runtime'da hisoblanadi        |
| `birth_date`           | `int` (unix)    | `profiles.birth_date` (date)           | —                  | Konvertatsiya kerak                                   |
| `image`                | `url str`       | `users.avatar_url`                     | —                  | HEMIS rasmni saqlaymiz yoki proxy qilamiz             |
| `email`                | `str?`          | `users.email`                          | ✅ NULLABLE qilish | Optional + partial unique index                       |
| `university`           | `str`           | `users.organization_id` orqali         | —                  | XIU singleton bo'lgani uchun bizda fixed              |
| `universityOwnership`  | Classifier      | `organizations.ownership_type`         | —                  | Davlat/xususiy                                        |
| `address`              | `str?`          | `profiles.address`                     | —                  | Bor                                                   |
| `country`              | Classifier      | `profiles.country` (yangi)             | ⚠️                  | code+name                                             |
| `province`             | Classifier      | `profiles.region` (yangi)              | ⚠️                  | Viloyat                                               |
| `district`             | Classifier      | `profiles.district` (yangi)            | ⚠️                  | Tuman                                                 |
| `group`                | `Group`         | `users.group_id` → `academic_groups`   | ✅ YANGI table     | FK                                                    |
| `faculty`              | `Department`    | `users.faculty_id` → `faculties`       | —                  | HEMIS Department = bizning Faculty                    |
| `educationLang`        | Classifier      | `users.preferred_language` mapping     | ⚠️                  | code → `uz-lat`/`uz-cyr`/`ru`/`en`                    |
| `semester`             | `Semester`      | `users.current_semester_id`            | ✅ ADD             | HEMIS semester ID                                     |
| `specialty`            | Classifier      | `users.specialty_id` → `specialties`   | —                  | code orqali bog'lash                                  |
| `level`                | Classifier      | `users.level` (bakalavr/magistr/...)   | ⚠️                  | mapping kerak                                         |
| `educationForm`        | Classifier      | `users.education_form` (yangi)         | ✅                 | kunduzgi/sirtqi/kechki/masofaviy                      |
| `educationType`        | Classifier      | (skip — Specialty'da bor)              | —                  | "bachelor/master/doctorate"                           |
| `paymentForm`          | Classifier      | `users.payment_form` (yangi)           | ✅                 | kontrakt/grand/davlat                                 |
| `studentStatus`        | Classifier      | `users.student_status` (yangi)         | ✅                 | faol/akademik/oxir/...                                |
| `socialCategory`       | Classifier      | `profiles.social_category` (yangi)     | ✅                 | nogiron/yetim/...                                     |
| `povertyLevel`         | Classifier      | `profiles.poverty_level` (yangi)       | ✅                 | kam ta'minlangan oilalar                              |
| `accommodation`        | Classifier      | `profiles.accommodation` (yangi)       | ⚠️                  | yotoqxona/uy                                          |
| `validateUrl`          | `url`           | (skip)                                 | —                  | runtime use                                           |
| `hash`                 | `sha256`        | `users.hemis_data_hash`                | ✅                 | Drift detection                                       |

### Email/Identity strategiyasi

```python
# Login lookup order
1. by hemis_id (SSO/JWT decoded)
2. by hemis_login (HEMIS API login form)
3. by pinfl (HEMIS sync fallback)
4. by email (admin/staff fallback uchun)
```

Email partial unique index:

```sql
CREATE UNIQUE INDEX ux_users_email_notnull ON users(email) WHERE email IS NOT NULL;
```

## 2. Employee → User

HEMIS `Employee` minimal (`id`, `name`). To'liq ma'lumot `/v1/data/employee-list?type=employee`
orqali keladi.

| HEMIS field            | Bizning field                  | Eslatma                            |
|------------------------|--------------------------------|------------------------------------|
| `id`                   | `users.hemis_id`               | Bir xil kolonka student bilan      |
| `staffPosition.code`   | `users.staff_position`         | Rector/Dekan/Pedagog/...           |
| `employmentForm.code`  | `users.employment_form`        | Asosiy/qoshma/soatlik              |
| `employmentStaff.code` | `users.employment_staff`       | full/half/0.25                     |
| `department`           | `users.faculty_id`             | Department FK                      |
| `academicDegree`       | `profiles.academic_degree`     | (yangi) PhD/Doktor/...             |
| `academicTitle`        | `profiles.academic_title`      | (yangi) Professor/Dotsent/...      |
| `phone`                | `profiles.phone`               | Bor                                |
| `gender`               | `profiles.gender`              | M/F                                |

## 3. Department → Faculty

```sql
ALTER TABLE faculties ADD COLUMN hemis_id INTEGER UNIQUE;
ALTER TABLE faculties ADD COLUMN hemis_code VARCHAR(50);
ALTER TABLE faculties ADD COLUMN hemis_parent_id INTEGER;
ALTER TABLE faculties ADD COLUMN structure_type VARCHAR(20);
ALTER TABLE faculties ADD COLUMN locality_type VARCHAR(20);
```

## 4. Group → academic_groups (YANGI table)

```sql
CREATE TABLE academic_groups (
  id              BIGSERIAL PRIMARY KEY,
  hemis_id        INTEGER UNIQUE NOT NULL,
  name            VARCHAR(50) NOT NULL,            -- e.g. "ATM-21-1"
  education_lang  VARCHAR(20),
  faculty_id      BIGINT REFERENCES faculties(id) ON DELETE SET NULL,
  specialty_id    BIGINT REFERENCES specialties(id) ON DELETE SET NULL,
  semester_id     INTEGER,                          -- HEMIS semester id
  is_active       BOOLEAN DEFAULT TRUE,
  hemis_last_synced_at TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_academic_groups_faculty ON academic_groups(faculty_id);
CREATE INDEX ix_academic_groups_specialty ON academic_groups(specialty_id);
```

## 5. Specialty → specialties

```sql
ALTER TABLE specialties ADD COLUMN hemis_code VARCHAR(20) UNIQUE;
-- HEMIS "code" — DTS kodi, masalan "60710300"
```

## 6. Curriculum, CurriculumSubject

`/v1/data/curriculum-list` HEMIS bizning `curricula`-ga mos:

```sql
ALTER TABLE curricula ADD COLUMN hemis_id INTEGER UNIQUE;
ALTER TABLE curricula ADD COLUMN specialty_hemis_code VARCHAR(20);
```

`CurriculumSubject` (HEMIS) → bizning `curricula.subjects[]` JSONB array yoki yangi
`curriculum_subjects` jadval.

## 7. Semester (yangi entity)

```sql
CREATE TABLE academic_semesters (
  id              BIGSERIAL PRIMARY KEY,
  hemis_id        INTEGER UNIQUE NOT NULL,
  code            VARCHAR(20),
  name            VARCHAR(100),
  education_year_code  VARCHAR(20),
  education_year_name  VARCHAR(50),
  is_current      BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

## 8. Classifier — yagona registr

HEMIS'da `Classifier` har joyda ishlatiladi (`{code, name}`). Bizda:
- Kichik enum'lar bo'lsa Python enum'da saqlanadi
- Katta classifier'lar (masalan `country`/`socialCategory`) — yangi `classifiers` jadval:

```sql
CREATE TABLE hemis_classifiers (
  type   VARCHAR(50) NOT NULL,  -- 'social_category', 'education_form', ...
  code   VARCHAR(50) NOT NULL,
  name   VARCHAR(200) NOT NULL,
  active BOOLEAN DEFAULT TRUE,
  PRIMARY KEY (type, code)
);
```

## 9. Sync logikasi

`HemisSyncService.upsert_student(data: dict)`:

```python
async def upsert_student(db, data: dict) -> User:
    h = sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    user = await db.scalar(select(User).where(User.hemis_id == data['id']))
    if user is None:
        user = User(
            hemis_id=data['id'],
            hemis_login=data.get('student_id_number'),
            pinfl=data.get('passport_pin'),
            email=data.get('email'),  # nullable!
            full_name=data['full_name'],
            organization_id=settings.XIU_ORG_ID,
            ...
        )
        db.add(user)
    elif user.hemis_data_hash != h:
        # changed in HEMIS — re-sync
        user.hemis_login = data.get('student_id_number')
        user.full_name = data['full_name']
        ...
    user.hemis_data_hash = h
    user.hemis_last_synced_at = datetime.utcnow()
    await db.flush()
    return user
```

## 10. Faylda yo'q

- HEMIS'da `Course`, `Module`, `Lesson` schema yo'q (HEMIS o'quv reja darajasida ishlaydi,
  bizning LMS course'lari bunga additional layer).
- HEMIS'da `Enrollment` ham yo'q — talaba `group → curriculum → subject` orqali
  fanlarga avtomatik biriktirilgan.
- LMS course-enrollment sxemamiz HEMIS dan ustun va saqlanadi.
