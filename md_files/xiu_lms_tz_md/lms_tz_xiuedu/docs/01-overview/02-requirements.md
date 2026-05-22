# 02. Talablar va Normativ Muvofiqlik

## Normativ-huquqiy asos

| # | Hujjat |
|---|--------|
| 1 | VM ning **2022-yil 3-oktabrdagi 559-son qarori** |
| 2 | 559-qarorga ilova — **Nizom** (33 banddan iborat) |
| 3 | **OʻzDSt 36.2030** — Elektron taʼlim standarti |
| 4 | "Shaxsga doir maʼlumotlar toʻgʻrisida"gi qonun |
| 5 | "Axborotlashtirish toʻgʻrisida"gi qonun |
| 6 | Prezident Farmoni **PF-60** (2022-2026 strategiya) |
| 7 | Xalqaro: SCORM 1.2/2004, IMS xAPI, WCAG 2.1 AA, ISO/IEC 27001 |

## 559-qarorning asosiy bandlari va tizimda aks etishi

| Nizom bandi | Talab | Tizimda qaerda |
|-------------|-------|----------------|
| 8-band | LMS platformasi majburiy | Loyihaning yadrosi |
| 8-band | Mamlakat ichidagi server | DevOps va deployment |
| 9-band | OʻzDSt 36.2030 muvofiqlik | Content modul |
| 10-band | LMS SCORM standartlariga mos | Content modul |
| 10-band | Avtoproktoring majburiy | Exam modul |
| 11-band | 9 ta komponent (LMS) | Modul ro'yxati |
| 13-band | Toʻlov-kontrakt asosida | Payment modul |
| 14-band | Ruxsatsiz yo'nalishlar ro'yxati | Admin panel |
| 15-band | Qabul parametrlari (300/30) | Enrollment modul |
| 21-band | Yakuniy attestatsiya — OTMda | Hybrid exam |
| 21-band | Sinxron/asinxron rejim | Live classes |
| 24-band | Hammasi LMS ichida | Single source |
| 26-band | 1:50 nisbati cheklangan | RBAC va validatsiya |
| 29-band | OTJBAT/TSDIN integratsiya | Integratsiya bo'limi |

## Funksional talablar (yuqori darajada)

### 1. Auth & Identity
- OneID, Hemis SSO, JWT tokenlar
- 2FA (TOTP, SMS)
- RBAC (rol-based access control)

### 2. Akademik boshqaruv
- OTM, fakultet, kafedra, yo'nalish, mutaxassislik
- O'quv reja va dasturlar
- Akademik kalendar

### 3. Talabalar boshqaruvi
- Onlayn qabul (Hemis sync bilan)
- Kontingent boshqaruvi
- Ko'chirish, qayta tiklash, chetlashtirish

### 4. Kontent boshqaruvi
- SCORM/xAPI paketlar
- Video-darslar (HLS, adaptive bitrate)
- EOʻMM (Elektron Oʻquv-Metodik Majmua)

### 5. O'quv jarayoni
- Kurslar va modullar
- Vazifalar va baholash
- Plagiatga qarshi tekshirish

### 6. Sinxron ta'lim
- Zoom integratsiya (asosiy)
- Jitsi/BBB (alternativ)
- Avtomatik davomat

### 7. Imtihonlar
- Test va imtihon turlari
- AI avtoproktoring
- Adaptiv testlar

### 8. To'lov
- Click, Payme integratsiyasi
- Kontrakt PDF generatsiya
- Boʻlib-boʻlib toʻlash

### 9. Kommunikatsiya
- Chat, forum, e-mail, SMS
- Telegram bot
- Push notification

### 10. Hisobotlar
- Real-time dashboard
- Eksport: PDF, Excel, CSV
- Custom hisobot konstruktor

## No-funksional talablar

| Kategoriya | Talab |
|------------|-------|
| **Performance** | Sahifa < 2s, API < 300ms (95p) |
| **Yuk** | 50 000 onlayn, 5 000 imtihon, 10 000 live |
| **Uptime** | 99.5% / 99.9% imtihon davrida |
| **Backup** | 2x kuniga, 90 kun saqlash |
| **Xavfsizlik** | OWASP Top 10, ISO 27001 |
| **i18n** | uz-lat, uz-cyr, ru, en |
| **A11y** | WCAG 2.1 AA |
| **Mobile** | Mobile-first, PWA |

## Texnologik tanlovlar (qisqacha)

| Qatlam | Texnologiya |
|--------|-------------|
| Backend | FastAPI + Python 3.11+ |
| Frontend | Vue 3 + Vite + TypeScript |
| Styling | Tailwind CSS |
| DB | PostgreSQL 15+ |
| Cache | Redis 7+ |
| Queue | Celery |
| Search | OpenSearch |
| Storage | MinIO (S3-compat) |
| Container | Docker + K8s |
| CI/CD | GitLab/GitHub Actions |

Batafsil: [02-architecture/02-tech-stack.md](../02-architecture/02-tech-stack.md)
