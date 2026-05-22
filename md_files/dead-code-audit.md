# Dead Code Audit — 2026-05-14

> Loyiha kod bazasidagi ishlatilmayotgan kod (orphan) auditi.

---

## 1. Frontend — Tozalandi ✅

### Olib tashlangan API methodlari (17 ta)

| Fayl | Method | Sabab |
|---|---|---|
| `shared/api/auth.ts` | `authApi.refresh` | `client.ts` axios interceptor'ida raw `axios.post('/auth/refresh', ...)` ishlatadi — duplikat |
| `shared/api/auth.ts` | `authApi.regenerateBackupCodes` | UI yaratilmagan (2FA backup regen) |
| `shared/api/courses.ts` | `coursesApi.getBySlug` | Slug-routing reja edi, id-routing qoldi |
| `shared/api/courses.ts` | `lessonsApi.get` | Player `lessonsApi.list(moduleId)` ishlatadi |
| `shared/api/courses.ts` | `progressApi.save` | Partial progress hozir kerakmas (faqat start+complete) |
| `shared/api/academic.ts` | `orgsApi.get` | Single-tenant — bitta XIU, list+update yetadi |
| `shared/api/academic.ts` | `orgsApi.create` | Single-tenant — yangi OTM yaratish UI yo'q |
| `shared/api/academic.ts` | `facultiesApi.get` | UI faqat list/create/update/remove ishlatadi |
| `shared/api/academic.ts` | `departmentsApi.get` | xuddi yuqoridagidek |
| `shared/api/academic.ts` | `specialtiesApi.get` | xuddi yuqoridagidek |
| `shared/api/academic.ts` | `subjectsApi.get` | xuddi yuqoridagidek |
| `shared/api/academic.ts` | `curriculaApi.get` | xuddi yuqoridagidek |
| `shared/api/content.ts` | `contentApi.update` | UI'da CRUD yo'q (faqat list + transition) |
| `shared/api/content.ts` | `contentApi.remove` | xuddi yuqoridagidek |
| `shared/api/content.ts` | `contentApi.upload` | File upload UI yo'q (logically tied to create, but no file-upload flow) |
| `shared/api/assignments.ts` | `assignmentsApi.listSubmissions` | `assignmentsApi.inbox` ishlatiladi (boshqa endpoint) |
| `shared/api/assignments.ts` | `peerReviewsApi.start` | Backend mavjud, lekin frontend trigger UI yo'q |

### Olib tashlangan typelar (1 ta)

| Type | Sabab |
|---|---|
| `shared/types/assignments.ts → PeerReviewStartResponse` | Faqat `peerReviewsApi.start`'da ishlatilardi |

---

## 2. Frontend — Audit toza ✅

### View'lar (45 ta)
**100% router'da** — orphan view yo'q. Har bir `.vue` view `lazy import()` orqali `router/index.ts`'da chaqirilgan.

### Komponentlar (50+ ta)
**Hammasi ishlatilgan** — `shared/components/ui/*`, `shared/components/layout/*`, `shared/components/live/*`, `user/components/**`, `admin/components/**` — har biri kamida bitta joyda import qilingan.

### Composables (2 ta)
- `useDueCountdown` — AssignmentDetailView'da ishlatiladi ✓
- `usePermissions` — bir nechta joyda ✓

### Stores (5 ta)
- `auth`, `locale`, `theme`, `academic`, `users` — hammasi faol ✓

---

## 3. Backend — Audit hisoboti (o'chirilmagan)

### Orphan endpoint'lar (6 ta)

Frontend tomonidan chaqirilmaydi, lekin **backend testlarida ishlatiladi** yoki **tashqi integratsiya uchun zarur**, shuning uchun **o'chirilmagan**:

| Method | Path | Fayl | Sabab |
|---|---|---|---|
| POST | `/auth/logout-all` | `auth.py:179` | "Barcha qurilmalardan chiqish" — UI hali yaratilmagan, kelajakda kerak bo'ladi |
| GET | `/auth/sessions` | `auth.py:214` | Faol session'lar ro'yxati — kelajak feature |
| POST | `/auth/2fa/backup-codes/regenerate` | `auth.py:375` | Frontend method o'chirilgan, 2FA backup regen UI yo'q. Backend qoldirildi. |
| POST | `/assignments/{id}/peer-review/start` | `assignments.py:730` | **Test coverage bor** (`test_plagiarism_peer_appeals.py`). Frontend trigger UI yo'q. |
| GET | `/courses/by-slug/{slug}` | `courses.py:124` | Slug-routing imkoni saqlanadi, lekin frontend id-routing'da. |
| POST | `/lessons/{id}/progress` | `courses.py:578` | Partial progress — kelajak feature uchun. |

### Sog'lom (KEEP)

| Method | Path | Sabab |
|---|---|---|
| GET | `/health` | K8s liveness probe, monitoring |
| GET | `/health/ready` | K8s readiness probe |
| GET | `/live-calendar.ics` | iCal feed — external calendar apps (Google/Apple Cal) consume |

---

## 4. Tavsiyalar

1. **Frontend orphan API o'chirildi** — kod bazasi 17 ta method va 1 ta type kichikrok.
2. **Backend orphan endpoint'lar saqlandi** — testlar ishlaydi, kelajak UI yaratilganda darhol foydalansa bo'ladi.
3. **Yangi feature qo'shganda** — avval orphan list'ni tekshiring, kerakli endpoint allaqachon mavjud bo'lishi mumkin.
4. **Kelajakda backend cleanup** — Phase 9 (yoki keyinroq) testlar bilan birga "haqiqatdan ortiqcha" endpoint'larni olib tashlash.

---

*Audit tools: `grep -rE` + custom Python script. Re-run uchun: `md_files/dead-code-audit.md` ichidagi method nomlarini har bir release'da qayta tekshiring.*
