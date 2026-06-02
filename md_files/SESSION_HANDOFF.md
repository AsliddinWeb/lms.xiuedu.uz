# XIU LMS — sessiya handoff (2026-06-02)

Bu fayl yangi Claude Code sessiyasida ishni kesinmasdan davom ettirish uchun
yozilgan. Pastdagi **prompt**'ni `claude` ga yuborib ishni davom ettiring.

---

## 1. Loyiha qisqacha

**Nomi:** XIU LMS — Xalqaro Innovatsiya Universiteti uchun yagona LMS platforma
**Ishlab beruvchi:** NEONSOFT MCHJ
**Buyurtmachi:** Xalqaro Innovatsiya Universiteti (XIU)

**Stack:**
- Backend: FastAPI 0.110+, Python 3.11, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- Frontend: Vue 3 (Composition + TypeScript), Vite, Pinia, vue-i18n, Tailwind CSS
- DB / cache / files: PostgreSQL 15, Redis (rate-limit + pub/sub), MinIO (S3-mos)
- Live: LiveKit WebRTC server
- Infra: Docker Compose v2 (dev + prod), nginx (tashqi), Let's Encrypt
- Integratsiyalar: HEMIS OAuth2, SMTP, SMS gateway, Telegram bot

**Production URL'lar:**
- `https://lms.xiuedu.uz` — talaba/o'qituvchi
- `https://lms-admin.xiuedu.uz` — admin
- `https://lms-api.xiuedu.uz` — backend API
- `https://lms-cdn.xiuedu.uz` — MinIO (presigned URL'lar)

**Lokal portlar:**
- 8200 backend · 8201 frontend-user · 8203 frontend-admin
- 7880-7882 LiveKit · 8212 MinIO S3 · 8213 MinIO console

---

## 2. Hozirgi rol va fokus

**Aktiv rol:** **Talaba (student)** — Phase 13'dan boshlab to'liq talaba UX
**Til:** O'zbek (uz-lat) — javoblar shu tilda

User feedback (eslab qoling):
- Ketma-ketlik bilan ish — 2-3 variant taklif qilmaslik
- Terse javoblar, ortiqcha mulohaza yo'q
- Har faza tugaganda commit qilish

---

## 3. Tugallangan fazalar

| Faza | Mavzu | Status |
|---|---|---|
| 1-12 | Auth, RBAC, akademik, kurslar, content, builder | ✅ |
| 13 | Talaba UX yaxshilash (29 sub-faza) | ✅ |
| 14 | Production deploy Ubuntu 22.04 | ✅ |
| 15 | HEMIS OAuth2 standart oqimi | ✅ |
| 16 | Talaba dashboard real data | ✅ |
| 17 | Professional sidebar + header | ✅ |
| 17.2 | Mening kurslarim (`/app/learning`) full | ✅ |
| 18 | Kurs detail (`/app/course/{id}`) full | ✅ |
| 19 | Kurs detail sharhlar + meta cards + dizayn | ✅ |

**Oxirgi 5 commit:**
```
98fdadb fix(student): kurs detail o'ng card — sana, yuklab olish, dizayn
02c6c3d feat(student): kurs detail Phase 19 — sharhlar tizimi + meta cards
09b4764 fix(i18n): kurs hero badge'lari har bir tilda tushunarli
080396c fix(student): kurs detail'da 403 students chaqiruvini gate qilish
49a1f9a feat(student): CourseDetail full versiya (Phase 18)
```

---

## 4. Phase 19 — sharhlar tizimi tafsilotlari

**Backend:**
- Model: `app/modules/courses/models.py` → `CourseReview` (course_id, user_id, rating 1-5, comment)
- Migration: `backend/alembic/versions/c3a07e9adcc9_course_reviews.py`
- Unique: `uq_review_course_user (course_id, user_id)`
- Endpointlar (`app/api/v1/courses.py`, oxirida):
  - `GET    /courses/{id}/reviews` — items + aggregate + my_review
  - `POST   /courses/{id}/reviews` — yangi sharh (faqat enrolled)
  - `PATCH  /courses/{id}/reviews/me` — o'z sharhini tahrir
  - `DELETE /courses/{id}/reviews/me` — o'chirish
- Permission: `course.read` (talabada bor)

**Frontend:**
- API: `frontend/src/shared/api/courses.ts` → `courseReviewsApi` + 4 type
- UI: `frontend/src/user/views/courses/CourseDetailView.vue` — "Sharhlar" tab
- Hero badge: rating ko'rsatkichi (⭐ 4.5 (23))
- i18n: 11 ta yangi kalit 4 tilga (uz-lat, uz-cyr, ru, en)

---

## 5. Kurs detail sahifa — qolgan ishlar

**Hech qanday muhim ish qolmadi.** Hammasi tugagan:
- ✅ Modules tab (eski)
- ✅ Syllabus tab
- ✅ Teacher tab
- ✅ Forum tab (oxirgi 3 mavzu preview + "Forumni ochish" link)
- ✅ Reviews tab (yangi, Phase 19)
- ✅ O'ng card (cover/gradient, progress, tugmalar, info)
- ✅ Materials sidebar
- ✅ Statistika sidebar
- ✅ Yaqinlashayotgan imtihonlar / live darslar widgetlari

**Mayda sayqal (ixtiyoriy):**
- Lesson page (`/app/learning/{id}/player`) UX audit — agar foydalanuvchi xohlasa
- Forum thread/post sahifalar dizayn audit

---

## 6. Keyingi mantiqiy fazalar (taklif)

User keyingisini tanlashi mumkin. Talaba uchun qolgan sahifalar:

| Phase | Sahifa | Holati |
|---|---|---|
| 20 | Jadval `/app/schedule` | Phase 6+ placeholder yoki yo'q |
| 21 | Topshiriqlar detail | Backend bor, UI to'liq emas |
| 22 | Imtihon detail / proktoring oqimi | Phase 6+ |
| 23 | Profil / Xavfsizlik sozlamalari | Asosiy bor, sayqal kerak |
| 24 | Sertifikatlar (`/app/certificates`) | Backend bor, UI mayda |
| 25 | Reyting / Belgilar (`/app/achievements`) | Backend bor |

User bittasini tanlasa, biz uni Phase 18/19 stilida sub-fazalarga bo'lib to'ldiramiz.

---

## 7. Server bilan ishlash

**Joylashuv:** `/home/ubuntu/xiu/lms.xiuedu.uz` (SSH: `ubuntu@containers`)

**Yangilanish:**
```bash
cd /home/ubuntu/xiu/lms.xiuedu.uz
git pull origin main
bash scripts/deploy/update.sh
```

Skript: build → `alembic upgrade head` → backend + frontend-user + frontend-admin
rolling restart → eski image'larni tozalash. Infra (postgres/redis/minio/livekit)
tegmaydi.

**Eslatma — LiveKit muammosi (hal qilinmagan):** Tashqi nginx (`lms-api.xiuedu.uz`
domeni qaysi proxy orqali kelishi noma'lum — server'da nginx config yo'q,
ehtimol Cloudflare Tunnel yoki tashqi proxy). LiveKit signal `/livekit/rtc/v1`
404 qaytaradi. Yechim: tashqi nginx config'iga quyidagi blokni qo'shish kerak:

```nginx
location /livekit/ {
    proxy_pass http://127.0.0.1:7880/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400s;
    proxy_buffering off;
}
```

UFW: `sudo ufw allow 7881/tcp && sudo ufw allow 7882/udp`

Bu hal qilinmaguncha live darslar ishlamaydi.

---

## 8. Hisob-faktura uchun loyiha tavsifi

`md_files/XIU_LMS_loyiha_tavsifi.md` va `.docx` — NEONSOFT MCHJ tomonidan XIU
universitetiga beriladigan hisob-faktura ilovasi sifatida tayyor.

---

## 9. Lokal dev — eslatmalar

- `RATE_LIMIT_ENABLED=false` lokal `.env`'da (sidebar 7 parallel API chaqirig'i
  120 RPM cheklovga urilmasligi uchun)
- Vite HMR ba'zan eski JSON cache'idan i18n kalitini olmaydi — `docker compose
  restart frontend-user` yordam beradi
- TS strict: `pnpm run type-check` har commitdan oldin
- Backend reload: `WatchFiles` avtomatik

---

## 10. Memory (har sessiyada avtomatik yuklanadi)

- User va loyiha haqida memory `/Users/a1234/.claude/projects/.../memory/`
- Hozir saqlangan: server-project-path (`/home/ubuntu/xiu/lms.xiuedu.uz`)

---

# 🤖 Davom etish uchun prompt

Quyidagi matnni yangi sessiyada `claude` ga yuboring:

```
Salom! XIU LMS loyihasini davom ettiramiz. Bu loyiha NEONSOFT MCHJ tomonidan
Xalqaro Innovatsiya Universiteti uchun ishlab chiqilayotgan masofaviy ta'lim
platformasi.

Avvalgi sessiyada to'xtagan joyimiz:
- Phase 19 (kurs detail sharhlar tizimi + dizayn yaxshilanishi) to'liq tugadi
- Oxirgi commit: 98fdadb (kurs detail o'ng card sana + yuklab olish + dizayn)
- Hozir biz talaba rolida ishlayapmiz (uz-lat tilida muloqot)

Loyiha haqida to'liq holatni `md_files/SESSION_HANDOFF.md` faylda yozib qoldirdim
— iltimos avval shu faylni o'qib chiq, keyin biz nimani davom ettirishimiz haqida
gaplashamiz.

Project root: /Users/a1234/Desktop/Live/qabul_xiuedu_fastapi/lms_xiuedu
Server: /home/ubuntu/xiu/lms.xiuedu.uz (ubuntu@containers)

Eslatma: men ketma-ket bitta variantni qabul qilaman, bir nechta taklif
bermang. Javoblar qisqa va aniq bo'lsin. Har faza tugashi bilan commit qiling.
```
