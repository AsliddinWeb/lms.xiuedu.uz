# XIU LMS — Single-tenant Arxitektura

**Versiya:** 2026-05-10
**Status:** Soft single-tenant migration (Phase 4 → Phase 5 oralig'ida amalga oshirildi).

XIU LMS faqat **Xalqaro Innovatsiya Universiteti** uchun mo'ljallangan. Boshqa
OTM lar tizimga qo'shilmaydi. Schema multi-tenant ko'rinishida qoldirilgan
(kelajakda kerak bo'lsa, ochib bo'ladi), lekin runtime butunlay XIU singleton
sifatida ishlaydi.

---

## 1. Tanlov: nima uchun "Soft" single-tenant?

| Variant | Tavsif | Tanlandi? |
|---|---|---|
| **A — Hard** | `Organization` jadvali olib tashlanadi, barcha FK'lar ham. | ❌ |
| **B — Soft** | Schema o'zgarmaydi. Runtime'da `organization_id` har joyda XIU bilan avto-to'ldiriladi. UI dan picker'lar olib tashlanadi. | ✅ |

**Sabab:** "Soft" yondashuv hech qanday migration risk yaratmaydi (Phase 4
yakunlangan, real foydalanuvchi data si bor), lekin UX butunlay
single-tenantga moslashtirilgan.

---

## 2. Backend o'zgarishlar

### 2.1 Constants — `app/core/config.py`

```python
# --- Single-tenant XIU only ---
TENANT_CODE: str = "XIU"
TENANT_NAME: str = "Xalqaro Innovatsiya Universiteti"
TENANT_DOMAIN: str = "xiuedu.uz"
```

### 2.2 Singleton helper — `app/core/tenant.py` (yangi)

| Funksiya | Maqsad |
|---|---|
| `ensure_xiu_org(db)` | Idempotent: agar XIU yo'q bo'lsa yaratadi (test fixture'lar uchun friendly). |
| `get_xiu_org(db)` | Faqat o'qish — yo'q bo'lsa `RuntimeError`. |
| `get_xiu_org_id(db) -> int` | Qulay shortcut, service'lar payload to'ldirish uchun. |
| `get_tenant_setting(db, key, default)` | `Organization.settings` JSONB dan dotted-path bo'yicha o'qish (masalan `hemis.base_url`). |

### 2.3 Service avto-fill

`organization_id` har create payload'da `None` bo'lsa, XIU bilan to'ldiriladi:

- `app/modules/academic/service.py` — `create_faculty`, `create_calendar`
- `app/modules/courses/service.py` — `create_course`
- `app/modules/assignments/service.py` — `create_rubric`

Pydantic schemalar `organization_id: int | None = None` bilan optional qilingan.

### 2.4 HEMIS konfiguratsiyasi

`hemis_login.py` endi env'dan emas, **adminkadan** sozlanadigan
`Organization.settings.hemis.base_url` JSONB key'idan o'qiydi (env fallback bilan):

```python
base_url = await get_tenant_setting(
    db, "hemis.base_url", default=app_settings.HEMIS_API_URL
)
async with HemisClient(base_url=base_url) as client:
    ...
```

### 2.5 Seed — `app/db/seed.py`

- `ensure_xiu_org()` chaqirig'i `main()` boshida.
- `tenant_id IS NULL` user'lar XIU ga backfill qilinadi.
- Demo akkauntlardan `otm-admin@xiuedu.uz` olib tashlandi (super_admin bilan teng).

### 2.6 Tests

161/161 test passing (`pytest -q`). Fixture'lar `Organization`'ni tozalasa
ham `ensure_xiu_org` auto-create qiladi, shuning uchun service avto-fill ishlaydi.

---

## 3. Frontend o'zgarishlar

### 3.1 Admin panel

| Sahifa / Komponent | O'zgarish |
|---|---|
| `views/academic/UniversitySettingsView.vue` (yangi) | XIU edit sahifasi: asosiy ma'lumotlar + HEMIS sozlash. `Organization.settings.hemis.base_url` ni saqlaydi. |
| `views/academic/OrganizationsView.vue` | **O'chirildi** (legacy multi-OTM list). |
| `components/academic/OrganizationDrawer.vue` | **O'chirildi**. |
| `router/index.ts` | `/organizations` → `/university` (`admin-university` route name, permission: `org.read`). |
| `layouts/AdminLayout.vue` | Sidebar nav: "OTM ro'yxati" → "Universitet sozlamalari". |
| `components/academic/FacultyDrawer.vue` | OTM picker olib tashlandi — backend avto-fill. |
| `components/academic/AcademicCalendarDrawer.vue` | OTM picker olib tashlandi. |
| `views/academic/FacultiesView.vue` | OTM filter va column olib tashlandi. |
| `views/academic/AcademicCalendarsView.vue` | OTM filter va header "code" badge olib tashlandi. |
| `views/courses/AdminCoursesView.vue` | OTM filter olib tashlandi (3-col). |
| `views/courses/AdminCourseDetailView.vue` | "Institution" stat card olib tashlandi (3-col). |
| `views/dashboard/AdminDashboardView.vue` | `kpi_orgs` o'rniga `kpi_faculties` (single-tenant'da OTM count = 1, manfaatsiz). |
| `stores/academic.ts` | `orgs`, `fetchOrgs`, `findOrg` olib tashlandi (faqat `faculties` qoldi). |

### 3.2 User panel

`views/auth/RegisterView.vue` da "OTM tomonidan" → "Universitet tomonidan"
matn almashtirildi. Boshqa user side komponentlar OTM picker'siz edi.

### 3.3 i18n (4 locale: uz-lat / uz-cyr / ru / en)

- `university` namespace qo'shildi (XIU edit sahifasi label'lari, HEMIS sozlash).
- `admin_nav.university` qo'shildi.
- `admin_dashboard.kpi_orgs` → `admin_dashboard.kpi_faculties`.

> **Eslatma:** Vite locale cache. Locale JSON o'zgarishidan keyin majburiy:
> `docker compose restart frontend-admin frontend-user`.

---

## 4. Schema haqida qaror

`Organization` model va FK'lar (`User.tenant_id`, `Faculty.organization_id`,
`Course.organization_id`, `AcademicCalendar.organization_id`,
`AssignmentRubric.organization_id`) **saqlanadi**:

- Real database migration bermaydi (Alembic version o'zgarmadi).
- Kelajakda agar talab qilinsa, multi-tenant'ga qaytish trivial bo'ladi.
- Test fixture'lar va service code minimal o'zgarish bilan ishlaydi.

---

## 5. HEMIS sozlash (admin yo'l-yo'riq)

1. Login: `admin@xiuedu.uz` / `ChangeMe!2026` → `http://localhost:8203/login`
2. Sidebar: **Boshqaruv → Universitet sozlamalari**
3. Pastki section: **HEMIS integratsiyasi**
4. `hemis_base_url` ni kiriting (default: `https://student.xiuedu.uz`).
5. **Saqlash**.

Backend'ning HEMIS login endpoint'i (`/auth/login/hemis`) keyingi so'rovdan
boshlab shu URL'dan foydalanadi. Env fallback (`HEMIS_API_URL`) saqlanadi —
agar `Organization.settings.hemis.base_url` o'rnatilmagan bo'lsa, env'dan o'qiladi.

---

## 6. Demo akkauntlar (post-migration)

| Email | Parol | Rol |
|---|---|---|
| `admin@xiuedu.uz` | `ChangeMe!2026` | super_admin |
| `dean@xiuedu.uz` | `Dean!2026` | dean |
| `teacher@xiuedu.uz` | `Teacher!2026` | teacher |
| `student@xiuedu.uz` | `Student!2026` | student |

`otm-admin@xiuedu.uz` **olib tashlandi**. Eski seed bo'lsa, qo'lda
`DELETE FROM users WHERE email = 'otm-admin@xiuedu.uz';` yoki seed'ni qayta
ishga tushiring (`make seed`).

---

## 7. Verification checklist (smoke)

Kelgusi sessiyada test qilish kerak:

- [ ] Backend tests: `cd backend && pytest -q` → 161/161 passing.
- [ ] Login `admin@xiuedu.uz` → Universitet sozlamalari sahifasi ochiladi.
- [ ] HEMIS base_url ni o'zgartirib saqlash → DB'da `Organization.settings.hemis.base_url` ko'rinadi.
- [ ] Yangi fakultet yaratish — payload'da `organization_id` yo'q, lekin DB'da XIU id bilan saqlanadi.
- [ ] Yangi kurs yaratish — xuddi shunday.
- [ ] Yangi akademik kalendar yaratish — xuddi shunday.
- [ ] HEMIS login (PINFL+parol) ishlaydi (yangi base_url bilan).

---

## 8. Phase 5 ga o'tishdan oldin

Migration tugadi. Phase 5 (Live darslar — WebRTC) ishini boshlash uchun barcha
Single-tenant ishlari yopildi:

✅ Backend service auto-fill
✅ HEMIS adminkadan sozlanadigan
✅ Frontend OTM picker'lar olib tashlandi
✅ Demo akkaunt `otm-admin` olib tashlandi
✅ MD docs yangilandi

Foydalanuvchi tasdiqlagandan keyin: **Phase 5 sub-phase'lariga o'tish**
(`md_files/phase5-plan.md` keyingi sessiyada yaratiladi).

---

## UI sahifalar wireframe'ga mos kelishi (2026-05-12)

Single-tenant migration tugagandan keyin **wireframe-alignment sprint** (S0–S4) bajarildi. Endi har UI sahifa `md_files/ui_wireframes/lms_ui/pages/01-18.html` wireframelarga 1:1 mos keladi.

**Asosiy qoidalar (kelajakda yangi sahifa qo'shilganda saqlanishi shart):**
- Har yangi UI sahifa avval wireframe (01–18) dan birortasiga assignment olishi kerak.
- `md_files/design-system.md` style spec'ga rioya qilish (Geist Sans/Mono + Instrument Serif, shadcn monoxrom palette, 260px sidebar + topbar + content).
- Shared komponentlar kutubxonasidan foydalanish: `UiSidebar`, `UiTopbar`, `UiBreadcrumb`, `UiTabs`, `UiStatCard`, `UiCourseCard`, `UiCheck`, `UiChartBar`, `UiProgressBar`, `UiImagePlaceholder`, `UiVideoPlaceholder` (S0 da yaratilgan).
- Dark mode `:root` light + `.dark` CSS variables orqali avtomatik — har element `bg-background` / `text-foreground` patterndan foydalanishi kerak.
- i18n majburiy 4 ta locale (`uz-lat`, `uz-cyr`, `ru`, `en`) — hardcoded string taqiqlanadi, parity har sprint oxirida tekshiriladi.
- To'liq checklist: [ui-alignment-checklist.md](ui-alignment-checklist.md).
