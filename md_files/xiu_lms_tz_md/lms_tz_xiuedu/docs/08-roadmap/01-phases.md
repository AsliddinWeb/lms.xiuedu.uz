# 08.01. Loyiha bosqichlari (Phases)

## Maqsad

Loyihani 4 ta yirik bosqichga bo'lib, har bir bosqichda aniq natija (deliverable) bilan yakunlash.

## Umumiy taymlayn

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  M1-M3      M4-M6       M7-M9        M10-M12      M13-M14           │
│  ┌────┐   ┌──────┐   ┌────────┐   ┌─────────┐   ┌──────────┐        │
│  │ P1 │──▶│  P2  │──▶│   P3   │──▶│   P4    │──▶│  Launch  │        │
│  │MVP │   │ Core │   │Advanced│   │Polish & │   │   Live   │        │
│  └────┘   └──────┘   └────────┘   │  Pilot  │   └──────────┘        │
│                                   └─────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Umumiy davomiylik:** 12-14 oy
**Komanda:** 8-12 kishi (1 PM, 1 Tech Lead, 3-4 Backend, 2-3 Frontend, 1 DevOps, 1 QA, 1 Designer)

## Phase 1: MVP (Oylar 1-3)

### Maqsad
Asosiy auth, foydalanuvchi boshqaruvi va kontent ko'rish funksionalligi bilan ishlovchi minimal versiya.

### Modullar

| Modul | Holati |
|-------|--------|
| Auth (login, register, JWT) | ✅ MVP |
| OneID integratsiyasi | ✅ MVP |
| RBAC (5 ta asosiy rol) | ✅ MVP |
| Akademik struktura (OTM, Fakultet, Kafedra) | ✅ MVP |
| Profil boshqaruvi | ✅ MVP |
| Kontent yuklash (video, PDF) | ✅ MVP |
| Kurs yaratish (oddiy) | ✅ MVP |
| Talaba enrollment (qo'lda) | ✅ MVP |
| Admin panel (asosiy) | ✅ MVP |

### Texnik vazifalar

- [ ] Loyiha skeleton (FastAPI + Vue 3)
- [ ] PostgreSQL schema (asosiy jadvallar)
- [ ] Docker compose setup
- [ ] CI/CD pipeline (basic)
- [ ] Sentry integratsiya
- [ ] Birlamchi unit testlar (60%+ coverage)

### Deliverables

- Ishlovchi auth tizimi
- Admin foydalanuvchilar yarata oladi
- O'qituvchi kontent yuklaydi
- Talaba kursni ko'ra oladi
- Demo muhit (staging)

### KPI

- 50 ta test foydalanuvchi
- Page load < 3s
- 0 ta critical bug

---

## Phase 2: Core LMS (Oylar 4-6)

### Maqsad
To'liq LMS funksionalligi: kurslar, topshiriqlar, baholash, video darslar.

### Modullar

| Modul | Holati |
|-------|--------|
| Kurslar (modul, dars, materiallar) | ✅ Core |
| SCORM 1.2 / 2004 qo'llab-quvvatlash | ✅ Core |
| xAPI (Tin Can) | ✅ Core |
| Topshiriqlar va baholash | ✅ Core |
| Antiplag.uz integratsiyasi | ✅ Core |
| Live darslar (Zoom S2S OAuth) | ✅ Core |
| Forum va chat | ✅ Core |
| Email/SMS bildirishnomalar | ✅ Core |
| Telegram bot | ✅ Core |
| HEMIS sinxronizatsiya (qisman) | ✅ Core |

### Texnik vazifalar

- [ ] Video transcoding pipeline (FFmpeg, HLS)
- [ ] MinIO/S3 integratsiyasi
- [ ] Celery task queue
- [ ] WebSocket (chat uchun)
- [ ] Zoom webhook handler
- [ ] Email service (SMTP)
- [ ] SMS gateway (Eskiz/PlayMobile)
- [ ] Test coverage 75%+

### Deliverables

- Talabalar kurslarni o'qiy oladi
- Topshiriqlarni topshira oladi
- O'qituvchi baholay oladi
- Live dars o'tkaziladi
- Yozuvlar saqlanadi
- HEMIS'dan talabalar import qilinadi

### KPI

- 500 ta faol talaba
- 50 ta kurs
- Video streaming 720p, < 5s buffer
- 99% uptime

---

## Phase 3: Advanced (Oylar 7-9)

### Maqsad
Imtihon avtoproctoring, to'lov tizimi, OTJBAT/TSDIN integratsiyasi va davlat talablariga to'liq mos kelish.

### Modullar

| Modul | Holati |
|-------|--------|
| Imtihonlar va testlar | ✅ Advanced |
| Avtoproctoring (face, voice, screen) | ⚡ Critical (559-qaror) |
| Click integratsiyasi | ✅ Advanced |
| Payme integratsiyasi | ✅ Advanced |
| Shartnoma generatsiyasi (PDF) | ✅ Advanced |
| Elektron imzo (E-IMZO) | ✅ Advanced |
| OTJBAT integratsiyasi | ⚡ Critical (559-qaror) |
| TSDIN integratsiyasi | ⚡ Critical (559-qaror) |
| Hisobotlar va analitika | ✅ Advanced |
| Sertifikat generatsiyasi | ✅ Advanced |
| Ariza/buyruq tizimi | ✅ Advanced |

### Texnik vazifalar

- [ ] AI proctoring (face detection, eye tracking)
- [ ] Webcam recording + storage
- [ ] Payment gateway secure flow
- [ ] PDF generation (WeasyPrint)
- [ ] E-IMZO browser plugin integratsiyasi
- [ ] BI dashboard (Metabase yoki Superset)
- [ ] Penetration test
- [ ] Test coverage 85%+

### Deliverables

- Imtihonlar avtoproctoring bilan o'tkaziladi
- Talabalar onlayn to'lov qilishi mumkin
- Shartnomalar avtomatik yaratiladi
- HEMIS, OTJBAT, TSDIN to'liq sinxron ishlaydi
- Hisobotlar real vaqtda

### KPI

- 2000 ta faol talaba
- 100 ta o'qituvchi
- Imtihon davomida xatolik < 1%
- To'lov muvaffaqiyat darajasi 99%+

---

## Phase 4: Polish & Pilot (Oylar 10-12)

### Maqsad
Tizimni mukammallashtirish, performance optimizatsiya, security audit, pilot OTM bilan sinov.

### Vazifalar

#### Performance optimizatsiya
- [ ] Database query optimization
- [ ] Redis caching strategy
- [ ] CDN sozlash (statik fayllar)
- [ ] Image optimization (WebP, lazy loading)
- [ ] Frontend bundle optimization
- [ ] Server-side rendering (kerak bo'lsa)

#### Security audit
- [ ] OWASP ZAP scan
- [ ] Pentest (uchinchi tomon)
- [ ] ISO 27001 audit tayyorgarligi
- [ ] Backup va disaster recovery test

#### UX polish
- [ ] Mobile responsive (barcha sahifalar)
- [ ] Accessibility (WCAG 2.1 AA)
- [ ] Multi-language (O'zbek, Rus, Ingliz)
- [ ] Dark mode
- [ ] Loading states va skeleton'lar
- [ ] Empty states

#### Documentation
- [ ] User documentation (talabalar uchun)
- [ ] Admin documentation
- [ ] O'qituvchi qo'llanmasi
- [ ] API dokumentatsiya (Swagger/Redoc)
- [ ] Video tutoriallar

#### Pilot
- [ ] 1-2 ta OTM bilan pilot
- [ ] User feedback yig'ish
- [ ] Bug'larni tuzatish
- [ ] Performance tuning

### Deliverables

- 100% test coverage critical modullarda
- WCAG 2.1 AA mos kelish
- Sertifikatlangan security audit
- Pilot OTM'larda muvaffaqiyatli ishlash

### KPI

- 5000+ talaba pilot OTM'larda
- Page load < 2s
- 99.9% uptime
- NPS > 40

---

## Phase 5: Launch & Scale (Oylar 13-14)

### Maqsad
Production'ga to'liq chiqish, mijozlarga tarqatish, monitoring va support.

### Vazifalar

- [ ] Production launch
- [ ] Load testing (10,000+ concurrent users)
- [ ] Marketing materiallari
- [ ] OTM'lar bilan shartnomalar
- [ ] Support team treningi
- [ ] 24/7 monitoring
- [ ] Incident response plan
- [ ] SLA hujjatlari

### KPI

- 10+ OTM
- 50,000+ foydalanuvchi
- Support response < 1 soat
- Uptime 99.9%+

---

## Risklar va ularni boshqarish

| Risk | Ehtimollik | Ta'sir | Boshqarish |
|------|------------|--------|------------|
| HEMIS API o'zgarishi | O'rta | Yuqori | Versioning, regular sync |
| Zoom narx oshishi | O'rta | O'rta | Jitsi/BBB alternativasi tayyor |
| Server muammolari | Past | Yuqori | Multi-region, backup, HA |
| Talab oshib ketish | Yuqori | O'rta | Kubernetes auto-scaling |
| Komanda almashishi | O'rta | Yuqori | Knowledge sharing, docs |
| 559-qaror o'zgarishi | Past | Yuqori | Modular arxitektura |

## Phase ko'rsatkichlari

```
Phase 1: ███░░░░░░░░░░░░░ 20% (MVP)
Phase 2: ███████░░░░░░░░░ 45% (Core LMS)
Phase 3: ████████████░░░░ 75% (Advanced)
Phase 4: ███████████████░ 95% (Polish)
Phase 5: ████████████████ 100% (Launch)
```
