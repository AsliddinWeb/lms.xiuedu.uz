# 08.02. Sprint rejasi

## Maqsad

Loyihani 2 haftalik sprintlar bo'yicha rejalashtirish va aniq vazifalarga ajratish.

## Sprint formati

- **Davomiyligi:** 2 hafta (10 ish kuni)
- **Sprint Planning:** Dushanba (1-haftaning boshi)
- **Daily Standup:** Har kuni 09:30 (15 daqiqa)
- **Sprint Review:** Juma (2-haftaning oxiri)
- **Retrospective:** Juma (Review'dan keyin)

## Story Points (Fibonacci)

- 1 — Juda kichik vazifa (1-2 soat)
- 2 — Kichik vazifa (yarim kun)
- 3 — O'rtacha (1 kun)
- 5 — Katta (2-3 kun)
- 8 — Juda katta (1 hafta)
- 13 — Epik (sprintga sig'maydi, bo'lish kerak)

## Phase 1 — MVP (6 sprint)

### Sprint 1: Project Setup
- Repository setup (monorepo)
- Docker compose (postgres, redis, minio)
- FastAPI skeleton
- Vue 3 + Tailwind skeleton
- CI/CD pipeline (basic)
- Sentry setup
- **Total:** 21 SP

### Sprint 2: Authentication
- User model + migrations
- Register endpoint
- Login + JWT
- Refresh token
- Password reset
- Login UI
- Register UI
- **Total:** 26 SP

### Sprint 3: RBAC + OneID
- Roles, Permissions models
- RBAC decorators
- OneID OAuth flow
- 2FA (TOTP)
- Profil sahifasi
- Sessions management
- **Total:** 24 SP

### Sprint 4: Academic Structure
- OTM, Fakultet, Kafedra modellari
- Mutaxassisliklar va o'quv rejalari
- Akademik yil/semestr
- Admin panel — OTM CRUD
- Admin panel — Fakultet/Kafedra CRUD
- **Total:** 22 SP

### Sprint 5: Content Upload
- File upload (chunked)
- MinIO integratsiyasi
- Video transcoding setup (FFmpeg)
- HLS streaming
- PDF, hujjat ko'rish
- Materiallar boshqaruvi
- **Total:** 28 SP

### Sprint 6: Basic Course
- Kurs modeli
- Modullar va darslar
- O'qituvchi: kurs yaratish
- Talaba: kurs ko'rish
- Progress tracking (asosiy)
- MVP demo
- **Total:** 24 SP

**Phase 1 jami:** 145 SP

## Phase 2 — Core LMS (6 sprint)

### Sprint 7: SCORM
- SCORM 1.2 parser
- SCORM 2004 parser
- xAPI endpoint
- SCORM player UI
- Progress saqlash
- **Total:** 26 SP

### Sprint 8: Assignments
- Assignment modeli
- Topshiriq yaratish UI (o'qituvchi)
- Topshirish UI (talaba)
- Fayl yuklash
- Antiplag.uz integratsiyasi
- Baholash UI
- **Total:** 24 SP

### Sprint 9: Live Classes
- Zoom S2S OAuth
- Meeting yaratish
- Webhook handler
- Yozuv yuklab olish
- Live dars UI
- Davomatni yozib olish
- **Total:** 28 SP

### Sprint 10: Communications
- Forum (asosiy)
- Real-time chat (WebSocket)
- Email service (SMTP)
- SMS gateway (Eskiz)
- Telegram bot (asosiy)
- Bildirishnomalar
- **Total:** 26 SP

### Sprint 11: HEMIS Integration
- HEMIS API client
- Talabalarni import
- Mutaxassisliklarni sinxronlash
- Davomat eksport
- Baholar eksport
- Cron jobs
- **Total:** 24 SP

### Sprint 12: Polish + Demo
- Bug fixing
- UI/UX yaxshilash
- Test coverage 75%+
- Documentation
- Demo OTM uchun
- **Total:** 18 SP

**Phase 2 jami:** 146 SP

## Phase 3 — Advanced (6 sprint)

### Sprint 13: Exam Engine
- Test/imtihon modellari
- Savollar bank
- Random selection algoritmi
- Imtihon UI (talaba)
- Avtomatik baholash
- **Total:** 28 SP

### Sprint 14: Auto-proctoring
- Face detection (MediaPipe/TensorFlow.js)
- Eye tracking
- Tab switching detection
- Webcam recording
- Suspicious activity alerts
- **Total:** 32 SP

### Sprint 15: Click Integration
- Click API integratsiyasi
- Prepare/Complete endpoints
- Tranzaksiyalar tarixi
- Refund qo'llab-quvvatlash
- Test sandbox
- **Total:** 22 SP

### Sprint 16: Payme Integration
- Payme API integratsiyasi
- Receipt yaratish
- Webhook handler
- Reconciliation
- **Total:** 22 SP

### Sprint 17: Contracts + E-IMZO
- Shartnoma shabloni
- PDF generatsiya
- E-IMZO integratsiya
- Hujjat saqlash
- Audit trail
- **Total:** 24 SP

### Sprint 18: OTJBAT/TSDIN
- OTJBAT API integratsiyasi
- TSDIN integratsiyasi
- Davlat hisobotlari
- Real-time monitoring
- 559-qaror compliance audit
- **Total:** 26 SP

**Phase 3 jami:** 154 SP

## Phase 4 — Polish & Pilot (4 sprint)

### Sprint 19: Performance
- Database optimization
- Redis caching
- CDN setup
- Image optimization
- Bundle optimization
- Load testing
- **Total:** 24 SP

### Sprint 20: Security & Compliance
- OWASP ZAP scan
- Pentest
- Security fixes
- Audit log to'liqlashtirish
- Backup automation
- **Total:** 22 SP

### Sprint 21: UX Polish
- Mobile responsive
- WCAG 2.1 AA
- i18n (uz/ru/en)
- Dark mode
- Loading/empty states
- **Total:** 26 SP

### Sprint 22: Documentation + Pilot
- User docs
- Admin docs
- API docs
- Video tutoriallar
- Pilot launch (1-2 OTM)
- Bug fixing
- **Total:** 22 SP

**Phase 4 jami:** 94 SP

## Phase 5 — Launch (2 sprint)

### Sprint 23: Pre-Launch
- Load testing (10K users)
- Disaster recovery test
- Support team trening
- Marketing materiallari
- OTM onboarding
- **Total:** 18 SP

### Sprint 24: Launch
- Production launch
- 24/7 monitoring
- Incident response
- Post-launch fixes
- Hisobot va metrikalar
- **Total:** 14 SP

**Phase 5 jami:** 32 SP

## Umumiy hisob

| Phase | Sprintlar | SP | Davomiyligi |
|-------|-----------|-----|-------------|
| Phase 1 — MVP | 6 | 145 | 3 oy |
| Phase 2 — Core | 6 | 146 | 3 oy |
| Phase 3 — Advanced | 6 | 154 | 3 oy |
| Phase 4 — Polish | 4 | 94 | 2 oy |
| Phase 5 — Launch | 2 | 32 | 1 oy |
| **JAMI** | **24** | **571** | **12 oy** |

## Komanda velositi

Taxminiy hisob (komanda 8-10 kishi):
- Sprint velocity: 22-28 SP
- O'rtacha: 24 SP/sprint

## Sprint board (Jira/Linear)

```
┌─────────────────────────────────────────────────────────┐
│ Sprint 7: SCORM                          (Sprint 7/24)  │
├─────────────────────────────────────────────────────────┤
│ Backlog        │ In Progress  │ Review    │ Done        │
├────────────────┼──────────────┼───────────┼─────────────┤
│ □ SCORM 2004   │ ▶ SCORM 1.2  │ ⏸ xAPI    │ ✓ Setup     │
│ □ Player UI    │   parser     │   endpoint│ ✓ Models    │
│                │              │           │             │
└────────────────┴──────────────┴───────────┴─────────────┘
```

## Definition of Done (DoD)

Vazifa "Done" deb hisoblanadi qachonki:

- [ ] Kod yozildi va PR yaratildi
- [ ] Code review o'tdi (kamida 1 reviewer)
- [ ] Unit testlar yozildi (coverage ≥ 80%)
- [ ] Integration testlar o'tdi
- [ ] CI pipeline yashil
- [ ] Documentation yangilandi
- [ ] Staging'ga deploy qilindi
- [ ] QA tomonidan test qilindi
- [ ] Product Owner approve qildi
- [ ] Main branch'ga merge qilindi
