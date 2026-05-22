# 03. Akademik Boshqaruv Moduli

## Maqsad

OTM ning akademik tuzilmasini boshqarish: fakultet, kafedra, ta'lim yo'nalishlari, mutaxassisliklar, o'quv rejalari va dasturlar.

## Funksional talablar

### 1. Tashkilot (OTM) tuzilmasi

```
Organization (OTM)
  └── Faculty (Fakultet)
        └── Department (Kafedra)
              └── Specialty (Yo'nalish/Mutaxassislik)
                    └── Curriculum (O'quv reja)
                          └── Subjects (Fanlar)
```

### 2. Boshqarish imkoniyatlari

#### OTM (Organization)
- Asosiy ma'lumotlar: nom, qisqartma, logo, manzil
- Rektor, prorektor ma'lumotlari
- Kontakt ma'lumotlari
- Domen, brending (white-label)
- Litsenziya raqami

#### Fakultet
- Nom, dekan, kafedralari
- Qabul rejasi (har yil uchun)

#### Kafedra
- Nom, mudir, pedagoglari, fanlari
- Kafedraning yo'nalishlari

#### Ta'lim yo'nalishlari va mutaxassisliklari
- **Bakalavriat:** kod, nom, davomiyligi (4 yil)
- **Magistratura:** kod, nom, davomiyligi (2 yil)
- Ta'lim shakli: kunduzgi, sirtqi, kechki, **masofaviy**
- Til: o'zbek, rus, ingliz
- Masofaviy ta'limga ruxsat berilganmi (VM 559-qaror 14-band)

### 3. O'quv rejalari (Curriculum)

- Yo'nalish/mutaxassislikka biriktirilgan
- Yil va semestr bo'yicha taqsimlash
- Fanlar va kreditlari (DTS asosida)
- Versiyalash (har yil yangilanishi mumkin)
- DTS yoki kasbiy standart asoslari

### 4. Akademik kalendar
- O'quv yili (1 sentyabr — 30 iyun)
- Semestrlar (kuzgi, bahorgi)
- Oraliq nazoratlar
- Ta'tillar (qish, yoz, bayram)
- Imtihon davrlari
- Bayramlar

### 5. Fanlar bazasi
- Kod, nom, qisqacha tavsif
- Kreditlar va soatlar (ma'ruza, amaliyot, mustaqil ish)
- Pre-rekvizitlar (avval o'tilishi kerak)
- Co-rekvizitlar
- Til
- Tegishli kafedra

## API Endpoints

```
# OTM
GET    /api/v1/organizations
POST   /api/v1/organizations                  # super admin
GET    /api/v1/organizations/{id}
PATCH  /api/v1/organizations/{id}

# Fakultetlar
GET    /api/v1/faculties
POST   /api/v1/faculties
GET    /api/v1/faculties/{id}
PATCH  /api/v1/faculties/{id}
DELETE /api/v1/faculties/{id}

# Kafedralar
GET    /api/v1/departments
POST   /api/v1/departments
GET    /api/v1/departments/{id}
PATCH  /api/v1/departments/{id}
DELETE /api/v1/departments/{id}
GET    /api/v1/departments/{id}/teachers
GET    /api/v1/departments/{id}/subjects

# Yo'nalish/Mutaxassisliklar
GET    /api/v1/specialties
POST   /api/v1/specialties
GET    /api/v1/specialties/{id}
PATCH  /api/v1/specialties/{id}
DELETE /api/v1/specialties/{id}
POST   /api/v1/specialties/{id}/enable-distance  # masofaviyga ruxsat

# O'quv rejalari
GET    /api/v1/curricula
POST   /api/v1/curricula
GET    /api/v1/curricula/{id}
PATCH  /api/v1/curricula/{id}
POST   /api/v1/curricula/{id}/clone           # yangi versiya
GET    /api/v1/curricula/{id}/subjects

# Fanlar
GET    /api/v1/subjects
POST   /api/v1/subjects
GET    /api/v1/subjects/{id}
PATCH  /api/v1/subjects/{id}
DELETE /api/v1/subjects/{id}

# Akademik kalendar
GET    /api/v1/academic-calendars
POST   /api/v1/academic-calendars
GET    /api/v1/academic-calendars/{id}
PATCH  /api/v1/academic-calendars/{id}
GET    /api/v1/academic-calendars/current
```

## Database modellari

```sql
-- OTM
CREATE TABLE organizations (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,         -- 'TUIT', 'NUUz'
    name VARCHAR(300) NOT NULL,
    short_name VARCHAR(50),
    type VARCHAR(50),                          -- 'state', 'private'
    license_number VARCHAR(100),
    rector_id BIGINT REFERENCES users(id),
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),
    website VARCHAR(255),
    domain VARCHAR(100) UNIQUE,                -- white-label uchun
    logo_url TEXT,
    branding JSONB DEFAULT '{}',               -- ranglar, fontlar
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Fakultet
CREATE TABLE faculties (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    short_name VARCHAR(50),
    dean_id BIGINT REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, code)
);

-- Kafedra
CREATE TABLE departments (
    id BIGSERIAL PRIMARY KEY,
    faculty_id BIGINT REFERENCES faculties(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    head_id BIGINT REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(faculty_id, code)
);

-- Yo'nalish/Mutaxassislik
CREATE TABLE specialties (
    id BIGSERIAL PRIMARY KEY,
    department_id BIGINT REFERENCES departments(id),
    code VARCHAR(50) UNIQUE NOT NULL,         -- '60611100' (DTS kodi)
    name VARCHAR(300) NOT NULL,
    level VARCHAR(20) NOT NULL,                -- 'bachelor', 'master', 'phd'
    duration_years INT NOT NULL,               -- 4, 2
    education_form VARCHAR(20) NOT NULL,       -- 'fulltime', 'parttime', 'evening', 'distance'
    language VARCHAR(10) NOT NULL,
    distance_enabled BOOLEAN DEFAULT FALSE,    -- VM 559-qaror 14-band
    annual_quota INT,                          -- Bakalavriat: max 300, Master: max 30
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- O'quv reja
CREATE TABLE curricula (
    id BIGSERIAL PRIMARY KEY,
    specialty_id BIGINT REFERENCES specialties(id),
    name VARCHAR(200) NOT NULL,
    version VARCHAR(20),                       -- '2024-v1'
    valid_from DATE NOT NULL,
    valid_until DATE,
    based_on VARCHAR(50),                      -- 'DTS', 'professional_standard'
    standard_code VARCHAR(50),
    total_credits INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    approved_by BIGINT REFERENCES users(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Fanlar
CREATE TABLE subjects (
    id BIGSERIAL PRIMARY KEY,
    department_id BIGINT REFERENCES departments(id),
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    short_name VARCHAR(50),
    description TEXT,
    credits INT NOT NULL,
    lecture_hours INT DEFAULT 0,
    practice_hours INT DEFAULT 0,
    seminar_hours INT DEFAULT 0,
    self_study_hours INT DEFAULT 0,
    language VARCHAR(10) DEFAULT 'uz-lat',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- O'quv rejadagi fanlar (junction)
CREATE TABLE curriculum_subjects (
    id BIGSERIAL PRIMARY KEY,
    curriculum_id BIGINT REFERENCES curricula(id) ON DELETE CASCADE,
    subject_id BIGINT REFERENCES subjects(id),
    semester INT NOT NULL,                     -- 1, 2, 3...
    is_required BOOLEAN DEFAULT TRUE,
    UNIQUE(curriculum_id, subject_id, semester)
);

-- Pre-requisites
CREATE TABLE subject_prerequisites (
    subject_id BIGINT REFERENCES subjects(id) ON DELETE CASCADE,
    prerequisite_id BIGINT REFERENCES subjects(id),
    PRIMARY KEY (subject_id, prerequisite_id)
);

-- Akademik kalendar
CREATE TABLE academic_calendars (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT REFERENCES organizations(id),
    academic_year VARCHAR(20) NOT NULL,        -- '2026-2027'
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    semesters JSONB,                           -- semestr ma'lumotlari
    holidays JSONB,                            -- bayramlar
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Hemis bilan sinxronizatsiya

Bu modulning katta qismi Hemis bilan sinxronlanadi. Tafsilotlar: [04-integrations/01-hemis.md](../04-integrations/01-hemis.md)

**Hemisdan keladigan:**
- OTM tuzilmasi (har kuni full sync)
- Yo'nalish va mutaxassisliklar
- O'quv rejalari (DTS asosida)
- Pedagog yuklamalari

**Bizdan Hemisga:**
- Faqat masofaviy ta'lim ma'lumotlari (alohida belgilangan)

## Acceptance kriteriyalar

- [ ] OTM, fakultet, kafedra CRUD
- [ ] Yo'nalish/mutaxassislik bilan masofaviy ta'lim flag
- [ ] O'quv reja konstruktor
- [ ] Versiyalash
- [ ] Akademik kalendar
- [ ] Fanlar bazasi
- [ ] Pre-rekvizitlar
- [ ] Hemis sync
- [ ] Frontend admin paneli
- [ ] Test coverage ≥ 80%
