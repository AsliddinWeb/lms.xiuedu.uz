# XIU LMS — Wireframe Alignment Plan

**Sana:** 2026-05-11  
**Maqsad:** Mavjud sahifalarning har birini `md_files/ui_wireframes/lms_ui/pages/` ichidagi wireframe'larga bir-biriga 1:1 mos qilib qaytadan ishlash. Phase 6 ga o'tish faqat shu plan to'liq bajarilgandan keyin.

---

## 0. Asosiy qoidalar (har sahifa uchun majburiy)

Wireframe'da aniq belgilangan dizayn tizimi (assets/styles.css):

### Rang palitrasi (shadcn-style, monoxrom)
```
--background: #ffffff   --foreground: #0a0a0a
--muted: #f4f4f5        --muted-foreground: #71717a
--border: #e4e4e7       --border-strong: #d4d4d8
--primary: #18181b      --primary-foreground: #fafafa
--destructive: #dc2626  --success: #16a34a
--warning: #ca8a04      --info: #2563eb
```

### Tipografika (3 ta shrift)
- **Geist** — asosiy UI matni (300–700)
- **Geist Mono** — barcha mono metadata: badge, breadcrumb, label, statlar, raqamlar
- **Instrument Serif** — faqat hero-style sarlavhalar (auth, marketing)

### Layout konstantalar
- **Sidebar:** 260px (sticky, full-height)
- **Topbar:** 12px 32px padding, sticky, search 400px max
- **Content:** 32px padding, max-width 1400px, mx-auto
- **Card:** 8px radius, 1px var(--border)
- **Stat grid:** 4 col, 16px gap
- **Auth pages:** 50/50 split (qora left, oq form right)

### Komponent qoidalari
- **`.nav-item`** — `padding: 8px 10px`, `border-radius: 6px`, active'da `background: var(--foreground); color: var(--background)` (qora fon, oq matn — INVERS, **shadcn'da default chiroyli active state**)
- **`.nav-badge`** — Geist Mono, 11px, mute background, active'da `rgba(255,255,255,0.15)`
- **`.stat-card`** — 20px padding, value 28px font-weight 600 + `font-feature-settings: 'tnum'`
- **`.btn-primary`** — qora fon, oq matn, hover `#27272a`
- **`.btn-outline`** — oq fon, border-strong, hover muted
- **`.badge`** — 11px Geist Mono, oval, ranglar bilan (success/warning/danger/info)
- **`.breadcrumb`** — Geist Mono 11px, UPPERCASE, mute
- **`.page-title`** — 28px font-weight 600, letter-spacing -0.025em

### Iconlar — barchasi SVG (16x16, stroke 1.5)
- Wireframe'da har sahifa uchun ANIQ icon nuqtalari berilgan
- Hozirgi kod `UiNavIcon.vue` ishlatadi — ammo wireframe stroke shaklini SVG'ga bir-biriga moslash kerak

---

## 1. Audit jadval — har sahifa wireframe vs kod

### **Auth (01–03)**

| # | Wireframe | Hozirgi sahifa | Gap | Reja |
|---|---|---|---|---|
| 01 | `01-login.html`: 50/50 split, qora left side branding bilan (120K+, 85+ OTM, 99.9%), OneID + HEMIS tugmalar + email/parol form, footer 559-qaror eslatma | `auth/LoginView.vue` | Branding side bo'shroq, OneID/HEMIS tugmalar yo'q, 559-qaror eslatma yo'q | Branding side'ni wireframe matniga moslash, OneID button (faqat UI — kelajak phase), HEMIS button bor (link `/login/hemis`), footer matnini qo'shish |
| 02 | `02-register.html`: shu split + JSHSHIR/PINFL field + parol kuch ko'rsatkichi | `auth/RegisterView.vue` | Tekshirish kerak | Wireframe bilan diff olib, fieldlarni mos qilish (full_name, email/PINFL, parol + tasdiq, terms checkbox) |
| 03 | `03-forgot-password.html`: split + minimal email form + "Email yuborildi" success state | `auth/ForgotPasswordView.vue` | Tekshirish kerak | Split layout, success state |
| — | (wireframe yo'q) | `auth/HemisLoginView.vue` | TZ'da `04-integrations/01-hemis.md` ga muvofiq | Wireframe yo'q — Login'ning HEMIS variant bilan birga style qilish |
| — | (wireframe yo'q) | `auth/ResetPasswordView.vue` | Forgot password follow-up | Login splitining minimal versiyasi |
| — | (wireframe yo'q) | `auth/VerifyEmailView.vue` | — | Login splitining minimal versiyasi |

### **User (talaba) — 04–11**

| # | Wireframe | Hozirgi sahifa | Gap | Reja |
|---|---|---|---|---|
| 04 | `04-student-dashboard.html`: sidebar (Dashboard/Kurslar/Topshiriqlar/Jadval/Baholar + To'lovlar/Sertifikatlar/Forum/Xabarlar + Yordam/Sozlamalar pastda), 4 stat card, "Bugungi reja" timeline, "Mening kurslarim" cards, Vazifalar list, "Eski faollik" ko'p o'lchamli, Cheklov banner 1:50 normativ haqida | `dashboard/DashboardView.vue` | Stat grid bor, lekin wireframe yangi cards (Bugungi reja timeline, 1:50 normativ banner) yo'q | Stat grid'ni 4-ga sozlash, kurslar grid + jadval timeline + 1:50 banner qo'shish, sidebar nav iconlar bo'yicha moslash |
| 05 | `05-courses-list.html`: filter sidebar 240px + grid 3-col course cards (cover, kategoriya tag, title, stats, progress bar) | `courses/CourseCatalogView.vue` + `courses/MyLearningView.vue` | Mavjud — moslashtirish kerak | Filter sidebar + course-card komponentini wireframe'ga moslash (cover image-placeholder, kategoriya `font-mono uppercase`, stats, progress) |
| 06 | `06-course-detail.html`: hero (cover, breadcrumb, title, instructor avatar), 2-col layout (modules accordion + sidebar "Sotib olish" yoki "O'qish" CTA + stats) | (mavjud emas — kerak) | Sahifa yo'q | Yangi `courses/CourseDetailView.vue` yaratish |
| 07 | `07-lesson-player.html`: 320px lesson sidebar (modules + progress) + video player area (1000px max, controls bar 36px play tugma, 1080p label, CC, 1.0x), pastda materials/izoh/savol-javob tablar | `courses/CoursePlayerView.vue` | Hozir minimal — wireframe ancha boyitilgan | Lesson sidebar full design (check radio dots, MODUL bo'limlar, MUDDATI lockout), player area dark mode, video controls, materials/izoh/savol-javob tabs |
| 08 | `08-assignments.html`: filter tabs (Hammasi/Bajarilmagan/Yakunlangan/Kechiktirilgan) + assignments cards (kurs tag, title, due date countdown, type badge) | `assignments/MyAssignmentsView.vue` | Mavjud — moslashtirish kerak | Cards layout, tabs, countdown `Geist Mono`, type badge |
| 09 | `09-exam-page.html`: Proctoring overlay (kamera preview corner), savol katta markazda, timer top-right (qizil), navigation footer (oldingi/keyingi/yakunlash), pastida savollar carosel | (mavjud emas — Phase 6) | Phase 6 ish — wireframe'dan dizayn olamiz | **Phase 6'da yaratiladi** — hozir reja sifatida saqlanadi |
| 10 | `10-grades.html`: O'rtacha ball big card + reyting position + 5 ta semester table (predmet/ball/kreditt/baho) | (mavjud emas) | Sahifa yo'q | Yangi `grades/GradesView.vue` yaratish — backend endpoint kerak (gradebook Phase 6'da) |
| 11 | `11-payments.html`: Hozirgi shartnoma card + pul kelishlar history + Click/Payme tugmalar | (mavjud emas — Phase 8) | Phase 8 ish | **Phase 8'da yaratiladi** |
| — | (wireframe yo'q, lekin kerak) | `assignments/AssignmentDetailView.vue` | — | Wireframe 08'ning detail variant — assignment description + submit form + previous attempts |
| — | (wireframe yo'q) | `peer_review/PeerReviewListView.vue` | — | Assignments 08 stilida — peer review feed |
| — | (wireframe yo'q) | `peer_review/PeerReviewSubmitView.vue` | — | Submission detail + rubric form |
| — | (wireframe yo'q) | `profile/ProfileView.vue` | — | Avatar, full_name, email, til, notification preferences |
| — | (wireframe yo'q) | `profile/SecurityView.vue` | — | 2FA, parol o'zgartirish, sessions list |

### **Teacher (12–15)**

| # | Wireframe | Hozirgi sahifa | Gap | Reja |
|---|---|---|---|---|
| 12 | `12-teacher-dashboard.html`: sidebar (Dashboard/Kurslarim/Konstruktor/Topshiriqlar/Live/Talabalar + Statistika/Hisobotlar), 4 stat (Faol kurslar, Talabalar, Baholash kutmoqda **yellow card**, O'rtacha ball), "Bugungi jadval" widget, "Kursdagi faollik" chart, "So'nggi baholangan" list | `dashboard/DashboardView.vue` (single dashboard for both) | Hozirgi DashboardView role-aware lekin wireframe darajasida tahliliyot yo'q | Dashboard'ni role-aware qilib, teacher uchun: "Baholash kutmoqda" yellow stat card, "Bugungi live darslar" widget, "Faollik chart" (rasm placeholder), "So'nggi baholanganlar" |
| 13 | `13-course-builder.html`: 3-col (Modules sidebar / Lesson editor markazda / Settings drawer o'ng), drag-drop list, lesson form fields | `courses/CourseBuilderView.vue` | Mavjud — kengaytirish kerak | Wireframe layoutga moslash: modul sidebar, lesson editor (turi: video/scorm/quiz/loyiha), settings paneli |
| 14 | `14-grade-submissions.html`: 2-col (submission detail + plagiat report ko'rsatish / baholash form rubric bilan), pdf annotation tools | `grading/SubmissionGradeView.vue` | Mavjud — wireframe boy | Detail panel (talaba info, kurs, plagiat % barcha kabilarda), rubric grading sidebar, annotations tool |
| 15 | `15-live-class.html`: full-screen dark, header LIVE pill + timer + title + Davomat/Yozib olish/Yakunlash, video grid 3fr+1fr thumbnails 6-col, side panel 320px (Chat/Ishtirokchilar/Q&A), bottom controls 44px circular | `live/LiveRoomView.vue` ✅ | Native room komponent qilingan | **Asosiy struktura tayyor, fine-tune kerak:** thumbnail row 6-col aniq, side panel `Chat (24)` count, "Yozib olish" tugmasi pastki bar'ga emas header'ga, control sep `width: 1px height: 28px`, info paneli 📡 ▰▰▰▰ + HD 1080p + YAXSHI 28ms |
| — | (wireframe yo'q) | `grading/TeacherInboxView.vue` | — | Grade-submissions 14'ning ro'yxat variant — submission cards |
| — | (wireframe yo'q) | `grading/AppealsInboxView.vue` | — | Wireframe 14 stilida — apellyatsiyalar feed |
| — | (wireframe yo'q) | `courses/MyCoursesView.vue` | — | Wireframe 05 stilida — pedagog kurslari grid |
| — | (wireframe yo'q) | `rubrics/RubricsListView.vue` | — | Standard table + drawer |
| — | (wireframe yo'q) | `live/MyLiveSessionsView.vue` | — | Wireframe 12 stilida list, "Live darslar" jadvali |
| — | (wireframe yo'q) | `live/StudentLiveListView.vue` | — | Talaba uchun yaqin/o'tgan live darslar feed |

### **Admin (16–18)**

| # | Wireframe | Hozirgi sahifa | Gap | Reja |
|---|---|---|---|---|
| 16 | `16-admin-dashboard.html`: sidebar (Admin: Dashboard/Foydalanuvchilar/Kurslar/To'lovlar/Hisobotlar + Tizim: Integratsiyalar/Audit/Sozlamalar), red avatar SUPER ADMIN, 4 stat (12.4K/487/348/2.8K), "Tizim faolligi 30 kun" chart 2/3 width + "Hisobotlar" 1/3, "Faollik xaritasi", "Eng faol fakultetlar" table | `admin/dashboard/AdminDashboardView.vue` | Hozirgi minimal — KPI lar bor lekin chart/table'lar yo'q | Wireframe asosida: 4 KPI stat, faollik chart placeholder (rasm/SVG), "Eng faol fakultetlar" table, system status grid 2-col, top-bar "HAR DOIMLAR HOLATI ●" badge |
| 17 | `17-users-management.html`: filter bar (rol/holat/qidiruv) + table (avatar+ism / email / rol badge / OTM / oxirgi kirish / actions ⋯), bulk select | `admin/users/UsersListView.vue` | Mavjud — moslashtirish kerak | Wireframe table styling, filter chips, role badge ranglarini moslash |
| 18 | `18-reports.html`: 4 ta tab (HEMIS/OTJBAT/TSDIN/Eksport), har biri sinxronlanish holati (oxirgi vaqt, yangilangan/eskirgan, error counts), manual sync tugma, raqamli stats | (mavjud emas — Phase 7-9) | Phase 9 ish | **Phase 9'da yaratiladi** |
| — | (wireframe yo'q, kerak) | `admin/users/RolesListView.vue` | — | Wireframe 17 stilida — 10 ta rol jadval ko'rinishida |
| — | (wireframe yo'q) | `admin/academic/UniversitySettingsView.vue` (XIU edit) | — | Standart form layout, HEMIS sozlama bo'limi |
| — | (wireframe yo'q) | `admin/academic/FacultiesView.vue` + Departments/Specialties/Subjects/Curricula | — | Wireframe 17 stilida list+drawer pattern |
| — | (wireframe yo'q) | `admin/academic/AcademicCalendarsView.vue` | — | Wireframe 17 stilida card grid |
| — | (wireframe yo'q) | `admin/courses/AdminCoursesView.vue` + `AdminCourseDetailView.vue` | — | Wireframe 05/06 stilida (admin view) |
| — | (wireframe yo'q) | `admin/content/AdminContentView.vue` | — | Wireframe 17 stilida list+filter |
| — | (wireframe yo'q) | `admin/live/AdminLiveSessionsView.vue` | — | Wireframe 17 stilida audit table |

---

## 2. Sidebar — wireframe icon va nav itemlar bo'yicha aniq xarita

### Talaba sidebar (wireframe 04)
```
ASOSIY
  ▢ Dashboard       (4-square icon: rect 2,2,5,5 + rect 9,2,5,5 + rect 2,9,5,5 + rect 9,9,5,5)
  ☰ Kurslar [12]    (3-line icon: M2 4h12 M2 8h12 M2 12h8)
  ▤ Topshiriqlar [3] (rect 3,2,10,12 + 3 lines)
  ◷ Jadval          (circle 8,8,6 + clock hands)
  ⊢ Baholar         (bar chart: M2 14V2 M2 14h12 + 3 vertical bars)

BOSHQA
  □ To'lovlar       (rect 2,4,12,9 rx1 + path M2 7h12)
  ▦ Sertifikatlar   (M3 3h10v10H3z + inner M6 6h4v4H6z)
  ☰ Forum           (3 lines varying)
  ✉ Xabarlar [5]    (M2 4l6 5 6-5 + envelope)

(pastda, border-top bilan)
  ⓘ Yordam          (circle + ! icon)
  ⚙ Sozlamalar      (gear icon)
```

### Pedagog sidebar (wireframe 12)
```
O'QITUVCHI
  ▢ Dashboard
  ☰ Mening kurslarim [5]
  ✚ Kurs konstruktori
  ▤ Topshiriqlar [42]
  ◉ Live darslar
  ⊙ Talabalar [142]

TAHLIL
  ⊢ Statistika
  ▦ Hisobotlar
```

### Admin sidebar (wireframe 16)
```
ADMIN
  ▢ Dashboard
  ⊙ Foydalanuvchilar [12.4K]
  ☰ Kurslar [348]
  □ To'lovlar
  ⊢ Hisobotlar

TIZIM
  ⊕ Integratsiyalar
  ▤ Audit log
  ⚙ Sozlamalar
```

**Action item:** Hozirgi [`AppLayout.vue`](frontend/src/user/layouts/AppLayout.vue), [`AdminLayout.vue`](frontend/src/admin/layouts/AdminLayout.vue), [`UiNavIcon.vue`](frontend/src/shared/components/ui/UiNavIcon.vue) wireframe'dagi aniq SVG'larga 1:1 moslanishi kerak. Hozir `UiNavIcon` o'z nomlash tizimi bilan ishlaydi — wireframe SVG'lariga kompozitsiya qilish kerak.

---

## 3. Yo'qotilgan sahifalar (wireframe bor — kod yo'q)

Quyidagilarni yangidan yaratish kerak:
1. **`courses/CourseDetailView.vue`** — wireframe 06 (kurs sahifasi modul ro'yxati + CTA)
2. **`grades/GradesView.vue`** — wireframe 10 (talaba transcript) — backend `gradebook` endpoint Phase 6+
3. **`payments/PaymentsView.vue`** — wireframe 11 — Phase 8 deferred

Plus admin uchun:
4. **`admin/reports/ReportsView.vue`** — wireframe 18 — Phase 9 deferred

---

## 4. Yangi yaratilgan sahifalar (wireframe yo'q — kerak)

Quyidagilarning dizayni `wireframe pattern'larga moslashtirilishi shart`:

**Pedagog:**
- `grading/TeacherInboxView.vue` → 14 stilida list
- `grading/SubmissionGradeView.vue` → 14 detail panel
- `grading/AppealsInboxView.vue` → 14 stilida feed
- `courses/MyCoursesView.vue` → 05 stilida
- `courses/CourseBuilderView.vue` → 13 stilida
- `rubrics/RubricsListView.vue` → standart table + drawer
- `live/MyLiveSessionsView.vue` → 12 stilida list
- `live/StudentLiveListView.vue` → 04 stilida cards feed

**Talaba:**
- `assignments/MyAssignmentsView.vue` → 08 stilida
- `assignments/AssignmentDetailView.vue` → 08 detail
- `peer_review/PeerReviewListView.vue` → 08 stilida
- `peer_review/PeerReviewSubmitView.vue` → 14 stilida submission view
- `profile/ProfileView.vue` → standart form layout
- `profile/SecurityView.vue` → standart form layout

**Admin:**
- `admin/users/RolesListView.vue` → 17 stilida read-only table
- `admin/academic/*View.vue` (6 ta) → 17 stilida list + drawer
- `admin/courses/AdminCoursesView.vue` + detail → 05/06 stilida
- `admin/content/AdminContentView.vue` → 17 stilida
- `admin/live/AdminLiveSessionsView.vue` → 17 stilida audit

---

## 5. Komponentlar (sahifalar oldidan tayyorlash)

Wireframe asosida quyidagi shared komponentlar kerak:

1. **`UiStatCard.vue`** ✅ — bor, lekin wireframe `stat-trend up/down` (rangli dot bilan) bo'lishi kerak
2. **`UiTabs.vue`** — wireframe `.tabs` + `.tab.active` border-bottom — yangi komponent
3. **`UiSidebar.vue`** — `_sidebar_student.html` reusable struktura (hozirgi AppLayout ichida hardcoded) — alohida komponentga ajratish
4. **`UiTopbar.vue`** — `.topbar` + search + actions + avatar pattern — yangi (hozir layout ichida)
5. **`UiBreadcrumb.vue`** — `.breadcrumb` Geist Mono UPPERCASE — yangi
6. **`UiPagePlaceholder.vue`** — `.placeholder` diagonal stripe pattern — wireframe specific
7. **`UiImagePlaceholder.vue`** — `.image-placeholder` 45deg lines — wireframe
8. **`UiVideoPlaceholder.vue`** — `.video-placeholder` dark + play overlay — wireframe
9. **`UiChartBar.vue`** — `.chart-bar` 200px height columns — yangi
10. **`UiCourseCard.vue`** — wireframe `.course-card` (cover + meta + stats + progress) — yangi
11. **`UiProgressBar.vue`** ✅ — `UiProgressRing` bor, lekin oddiy bar yo'q — qo'shish
12. **`UiCheck.vue`** — lesson-player `.check` circle (gray empty / green ✓ / lock) — yangi

---

## 6. CSS / Tailwind alignment

Hozirgi kod Tailwind ishlatadi. Wireframe `styles.css` to'g'ridan-to'g'ri CSS. Tailwind config'ga shu o'zgaruvchilarni qo'shish:

- **Tailwind config** (`frontend/tailwind.config.ts`):
  - `colors` blokiga shadcn palette aniq qiymatlarda
  - `fontFamily.serif: ['Instrument Serif']` qo'shish
  - `fontFamily.mono: ['Geist Mono']` ekanligini tasdiqlash
  - `fontFamily.sans: ['Geist']`

- **`shared/i18n`/locale fontlarini** — Cyrillic uchun Geist alternatives tekshirish

- **CSS globals** (`frontend/src/shared/styles/globals.css`):
  - Wireframe `font-feature-settings: 'cv11', 'ss01'` (body) + `'tnum'` (statlar) qo'shish

---

## 7. MD fayllar yangilash

Quyidagi md_files yangilanishi shart:

| MD fayl | Yangilanish kerak |
|---|---|
| **`md_files/role-access-matrix.md`** | Yangi yaratiladigan sahifalar (CourseDetail, Grades, Payments, Reports) ro'yxatga qo'shish. Sidebar wireframe item'lariga 1:1 mos qilish. |
| **`md_files/phase4-gaps-tracker.md`** | Wireframe-mosligi bo'limi qo'shish. "Sahifa: holati: status (✅/⏳/❌)" jadvali. |
| **`md_files/single-tenant-architecture.md`** | "UI sahifalar wireframe'ga mos" bayonot qo'shish. |
| **YANGI: `md_files/ui-alignment-checklist.md`** | Har sahifa uchun "Wireframe #/Kod fayl/Holat (✅⏳❌)/Quirks" checklist — bu hujjat ichida saqlanadigan ish jadvalini. |
| **YANGI: `md_files/design-system.md`** | Rang/font/spacing/komponent qoidalari, wireframe assets/styles.css'dan ko'chirilgan. Kelajakda yangi sahifa qo'shganda manba. |
| **`README.md`** | "UI dizayn manbasi" bo'limi qo'shish: wireframe'lar va alignment plan'ga link. |
| **TZ docs** (`md_files/xiu_lms_tz_md/lms_tz_xiuedu/docs/06-frontend/`) | Wireframe link'lari + dizayn qaror izohlari yangilash. |
| **Memory `project_xiu_lms.md`** | Single-tenant + design-system bo'lim qo'shish ("UI har sahifa wireframe'ga 1:1 mos kelishi shart"). |
| **Memory `feedback_xiu_lms_design.md`** | "Wireframe'siz sahifa yaratmaslik — har yangi sahifa avval wireframe 1–18 dan birortasiga assign qilingan dizayn pattern'iga moslashtirilishi shart" qoidasi qo'shish. |

---

## 8. Ish bosqichlari (sprint xaritasi)

To'liq kelajak ishi 4 sprintga taqsimlanadi. **Phase 6 ga o'tish faqat S0–S3 bajarilgandan keyin.**

### **S0 — Foundation (1–2 kun)**

- [ ] `design-system.md` yozish (style spec + komponent qoidalari)
- [ ] Tailwind config + globals.css wireframe'ga moslash
- [ ] Yangi shared komponentlar: `UiTabs`, `UiBreadcrumb`, `UiCheck`, `UiChartBar`, `UiCourseCard`, `UiProgressBar`, `UiImagePlaceholder`, `UiVideoPlaceholder`, `UiPagePlaceholder`
- [ ] `UiSidebar` + `UiTopbar` ni AppLayout/AdminLayout dan ajratib alohida komponentga
- [ ] `UiNavIcon` ichidagi har icon'ni wireframe SVG nuqtalariga moslash (talaba/pedagog/admin nav uchun 25+ icon)
- [ ] **Acceptance:** har 3 layout (User/AuthAdmin/AppShell) wireframe `app-shell` (260px sidebar + main) ga 1:1 mos keladi

### **S1 — Auth + Public (1 kun)**

- [ ] **01 Login** — split 50/50, branding text wireframe so'zlari bilan, OneID button (UI only), HEMIS button, footer 559-qaror + maxfiylik link
- [ ] **02 Register** — split + JSHSHIR/PINFL field + parol kuch indicator
- [ ] **03 Forgot Password** — split + email form + success state
- [ ] HemisLogin/ResetPassword/VerifyEmail — Login splitining minimal variantlari
- [ ] **Acceptance:** Login sahifasini wireframe HTML bilan side-by-side qilib taqqoslash → bir-biriga 100% mos

### **S2 — Talaba sahifalar (2–3 kun)**

- [ ] **Sidebar (talaba)** wireframe 04 bo'yicha — ASOSIY + BOSHQA + pastda Yordam/Sozlamalar (border-top)
- [ ] **Topbar** wireframe pattern — search 400px max + actions (notifications dot + messages + avatar+role)
- [ ] **04 Dashboard** — 4 stat + Bugungi reja timeline + Mening kurslarim cards + Vazifalar + 1:50 banner
- [ ] **05 Courses List** — filter sidebar 240px + 3-col grid + course-card (cover/category/title/stats/progress)
- [ ] **06 Course Detail** (YANGI sahifa) — hero + modules accordion + sidebar CTA
- [ ] **07 Lesson Player** — 320px lesson sidebar + dark player area + materials/izoh/savol-javob tabs
- [ ] **08 Assignments** — tabs (Hammasi/Bajarilmagan/Yakunlangan/Kechiktirilgan) + cards
- [ ] **10 Grades** (YANGI sahifa) — O'rtacha card + reyting position + semester tables (backend gradebook endpoint Phase 6+ — hozir mock UI)
- [ ] Profile/Security — standart form layout
- [ ] Peer Review pages — 08/14 stilida
- [ ] **Acceptance:** har sahifa screenshot wireframe HTML rendered screenshot bilan side-by-side 95%+ mos

### **S3 — Pedagog + Admin sahifalar (2–3 kun)**

- [ ] **Sidebar (pedagog)** wireframe 12 bo'yicha
- [ ] **12 Teacher Dashboard** — 4 stat (yellow "Baholash kutmoqda") + Bugungi jadval widget + Faollik chart + So'nggi baholangan
- [ ] **13 Course Builder** — 3-col layout (modules sidebar / editor / settings)
- [ ] **14 Grade Submissions** — 2-col (submission detail + rubric grading)
- [ ] **15 Live Class** — fine-tune (thumbnails 6-col aniq, chat count, header tugmalar, status info)
- [ ] TeacherInbox/AppealsInbox/MyCourses/Rubrics — 05/14 stilida derivation
- [ ] MyLiveSessions/StudentLiveList — list pattern
- [ ] **Sidebar (admin)** wireframe 16 bo'yicha
- [ ] **16 Admin Dashboard** — 4 KPI + Faollik chart 2/3 + Hisobotlar 1/3 + Top fakultetlar table + System status grid
- [ ] **17 Users Management** — filter bar + table + role badges + bulk select
- [ ] Roles list / Academic CRUD (6 ta) / Admin courses / Admin content / Admin live — 17 stilida derivation
- [ ] **Acceptance:** wireframe screenshot ↔ real sahifa side-by-side 95%+ mos

### **S4 — Polish + MD yangilash (1 kun)**

- [ ] Barcha **403/404/empty state**'larini standart wireframe placeholder bilan
- [ ] **Dark mode** — har sahifada tekshirish (live class allaqachon dark, qolganlari light + dark variant)
- [ ] **i18n** — barcha yangi string'lar 4 ta locale'da
- [ ] MD fayllarni yangilash (yuqorida 7-bo'limda ro'yxatlangan)
- [ ] **`ui-alignment-checklist.md`** ichidagi har itemni ✅ ga aylantirish
- [ ] Memory'ga "design wireframe-first" qoidasini qo'shish

---

## 9. Phase 5 ning qolgan ishlari

Phase 5 (Live darslar) backend to'liq tugatilgan (LiveKit + JWT + recording + iCal + summary).
Frontend (LiveRoomView) **asosiy strukturasi mavjud** va S3 sprintida basic fine-tune (breadcrumb, sidebar, i18n) qilingan.

**Professional UX uchun alohida bosqich qo'shildi:** [`phase5b-live-pro-plan.md`](phase5b-live-pro-plan.md) — Phase 6 dan **oldin** bajariladi.

Phase 5b skopi (qisqacha):
- Pre-join lobby (mic/cam preview + device selector)
- Audio level meter
- Recording controls (REC tugmasi header'da)
- Network quality bar (`📡 ▰▰▰▰ HD 1080p YAXSHI 28ms`)
- Reactions + hand raise
- Background blur
- Mobile responsive
- Permission denied UX flow

To'liq jadval va acceptance kriteriyalari `phase5b-live-pro-plan.md` da.

---

## 10. Acceptance kriteriyalari (Phase 6 ga o'tish sharti)

✅ **Phase 6 ga o'tish faqat:**
1. Har wireframe (01–18) → kod fayli mavjud va wireframe HTML rendered screenshot bilan **95%+ mos** (side-by-side check)
2. Sidebar (3 ta rol) wireframe icon va nav-item nomlari bilan **1:1 mos**
3. Auth pages (Login/Register/Forgot/HemisLogin/Reset/Verify) split layout + branding side aniq matn bilan
4. MD fayllar yangilanibgan:
   - `design-system.md` (yangi)
   - `ui-alignment-checklist.md` (yangi)
   - `role-access-matrix.md` (yangi sahifalar bilan)
   - `phase4-gaps-tracker.md` (wireframe-mosligi bo'limi)
   - Auto-memory: `project_xiu_lms.md` + yangi `feedback_xiu_lms_design.md` qoidasi
5. Barcha sahifalar **light + dark + 4 locale**'da ishlaydi
6. **Tests** (existing 193 backend + frontend smoke) green

---

## 11. Hozirgi suhbat oxiri

Bu plan tasdiqlangach, **S0**'dan boshlab navbatma-navbat ishlab boramiz. Har sprint oxirida side-by-side screenshot taqqoslash + sizning tasdiqlashingiz bilan keyingi sprintga o'tamiz.

**Savol:**
- Bu plan to'liqmi yoki qo'shimcha narsalar bormi?
- S0'dan boshlaymiz (foundation + 25 ta icon + yangi shared komponentlar)? Yoki avval auth (S1) — chunki u eng oddiy va dizayn validatsiyasi tezroq?
- Phase 6 (Imtihonlar + Proctoring) qachon? Faqat S0–S4 dan keyin → ehtimoliy timeline 6–8 ish kuni.
