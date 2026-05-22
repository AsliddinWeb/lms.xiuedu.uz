# 01. Tizim dizayni (System Design)

## Yuqori darajadagi arxitektura

```
┌──────────────────────────────────────────────────────────────────┐
│                       Foydalanuvchilar                           │
│       (Veb-brauzer  |  Mobil ilova  |  Tashqi tizimlar)          │
└──────────────────────────────┬───────────────────────────────────┘
                               │  HTTPS / WSS
┌──────────────────────────────▼───────────────────────────────────┐
│                     CDN / WAF (Cloudflare)                       │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│              Reverse Proxy + Load Balancer (Nginx)               │
└──────────────┬──────────────┬──────────────────┬─────────────────┘
               │              │                  │
   ┌───────────▼──┐  ┌────────▼────────┐  ┌──────▼──────────┐
   │  Vue 3 SPA   │  │  FastAPI API    │  │ WebSocket Server│
   │   (Static)   │  │   Gateway       │  │  (Real-time)    │
   └──────────────┘  └────────┬────────┘  └─────────────────┘
                              │
              ┌───────────────┼───────────────┬────────────────┐
              │               │               │                │
       ┌──────▼──────┐ ┌──────▼─────┐ ┌──────▼──────┐  ┌──────▼─────┐
       │  Auth Svc   │ │ Course Svc │ │  Exam Svc   │  │  Live Svc  │
       └──────┬──────┘ └──────┬─────┘ └──────┬──────┘  └──────┬─────┘
              │               │               │                │
              └───────────────┴──────┬────────┴────────────────┘
                                     │
        ┌───────────────────────────┬┴┬───────────────────────┐
        │                           │ │                       │
   ┌────▼─────┐  ┌──────────┐  ┌────▼─▼───┐  ┌──────────┐ ┌──▼─────┐
   │PostgreSQL│  │  Redis   │  │  MinIO   │  │OpenSearch│ │ Celery │
   │(Primary  │  │(Cache+   │  │(Storage) │  │(Search)  │ │(Tasks) │
   │+Replica) │  │ Sessions)│  └──────────┘  └──────────┘ └────────┘
   └──────────┘  └──────────┘
```

## Arxitektura tamoyillari

### 1. Modular Monolit → Mikroxizmatlar (Evolyutsion yondashuv)
Boshlang'ichda barcha modullar **bitta FastAPI ilovasida**, lekin har biri alohida domain (DDD) sifatida loyihalashtiriladi. Yuk ortib bilan modullarni alohida xizmatlarga ajratish mumkin bo'ladi.

**Sabab:**
- Tezroq ishga tushirish
- Kichik jamoa uchun qulay
- Keyinchalik ajratish oson (chunki domainlar toza)

### 2. API-First Design
Hamma ham API orqali ishlaydi. Frontend va mobile bir xil API'ni ishlatadi.

### 3. Stateless servislar
Har bir API instance stateless. Sessiyalar — Redis'da. Bu auto-scaling uchun zarur.

### 4. Event-driven (selektiv)
Kerak bo'lgan joyda — Celery + Redis orqali. Misol: video transkodlash, hisobotlarni yaratish, sync.

### 5. CQRS (selektiv)
Hisobotlar uchun alohida read-models (materialized views).

## Asosiy komponentlar

### Frontend (Vue 3 SPA)
- Vite orqali build
- TypeScript majburiy
- Pinia state management
- Vue Router 4
- Tailwind CSS
- Tarqalish: CDN + Nginx

### API Gateway (FastAPI)
- Async/await asosida
- OpenAPI 3.1 hujjatlash
- JWT autentifikatsiya
- Rate limiting (Redis)
- CORS, CSP sarlavhalari
- Strukturlangan logging

### WebSocket Server
- FastAPI + websockets
- Real-time chat
- Live notification
- Live exam proctoring stream

### Domain modullari (servislar)
1. Auth Service — OneID, JWT, 2FA
2. User Service — profil, RBAC
3. Academic Service — fakultet, kafedra, yo'nalish
4. Content Service — SCORM, video, EOʻMM
5. Course Service — kurs, modul, dars
6. Enrollment Service — qabul, ko'chirish
7. Live Service — Zoom integratsiya
8. Exam Service — test, imtihon, proktoring
9. Payment Service — Click, Payme
10. Notification Service — email, SMS, push, Telegram
11. Reports Service — analitika, eksport
12. Integration Hub — Hemis, OTJBAT, TSDIN

### Background Workers (Celery)
- Video transkodlash
- Email/SMS yuborish
- Hemis sync
- Hisobotlarni yaratish
- Avtoproktoring tahlili
- Plagiat tekshiruvi

### Maʼlumotlar bazasi
- **PostgreSQL 15+** (asosiy)
- **Read replicas** (kamida 2 ta)
- **Connection pooling** — PgBouncer
- **Backup** — pgBackRest
- **Partitioning** — audit_logs, proctoring_events

### Cache va Queue
- **Redis 7+** — sessiya, kesh, queue
- **Redis Sentinel** — HA uchun
- **Celery broker** — Redis yoki RabbitMQ

### Object Storage
- **MinIO** (S3-compatible)
- Video, hujjatlar, profilerasm
- 3 ta nod (distributed)
- 10 TB+ kapasiteti

### Search
- **OpenSearch** — kontent qidiruvi
- Talaba, kurs, material qidiruvi
- Full-text uz/ru/en

### Live Streaming
- **Zoom API** (asosiy)
- **BigBlueButton** yoki **Jitsi Meet** (alternativ)
- TURN server WebRTC uchun

## Multi-tenancy → Single-tenant XIU (2026-05-10)

**Yakuniy qaror:** Loyiha **faqat XIU** uchun ishlab chiqiladi (single-tenant).
Quyidagi multi-tenant strategiyalar tahlili tarixiy ma'lumot sifatida saqlandi.

| Strategiya | Tavsifi | Qo'llanish |
|------------|---------|------------|
| **Shared DB, shared schema** | Hammasi bitta DB, `tenant_id` ustun | (tarixiy) |
| **Shared DB, separate schema** | Bitta DB, har OTM o'z schema'si | (tarixiy) |
| **Separate DB** | Har OTM uchun alohida DB | (tarixiy) |

**Joriy holat:** Soft single-tenant. Schema "Shared DB + tenant_id" ko'rinishida
qoldirilgan, lekin runtime butunlay XIU singleton (kelajakda multi-tenant
qaytarish trivial bo'lishi uchun). Tafsilot: `../../../single-tenant-architecture.md`.

## Saqlash (Storage) hisoblari

### 1 OTM uchun yillik taxmin

| Tur | Hajm |
|-----|------|
| 1 talaba uchun matn ma'lumotlari | ~10 MB/yil |
| 1 fan uchun video kontent | ~5 GB |
| 1 imtihon uchun proktoring video | ~500 MB |
| Audit loglar | ~100 MB/foydalanuvchi/yil |

### 1000 talabalik OTM uchun

- Matn DB: ~10 GB/yil
- Video kontent: 50 fan × 5 GB = 250 GB
- Proktoring: 1000 × 10 imtihon × 500 MB = 5 TB/yil
- Loglar: 100 GB/yil

**Jami:** ~5.5 TB/yil

## Yuk taxminlari

### Peak (imtihon davri)

- Onlayn talabalar: 50 000
- Bir vaqtdagi imtihon: 5 000
- Bir vaqtdagi live: 10 000 (turli xonalarda)
- Webhook hodisalar: 100 / sekund
- API requests: 5000 RPS

### Normal kun

- Onlayn: 10 000-15 000
- API: 500-1000 RPS
- Video stream: 2000 parallel

## Texnik qarorlar (ADRs)

| Qaror | Tanlov | Sabab |
|-------|--------|-------|
| Backend tili | Python 3.11+ | Async, ekosistema, AI/ML |
| Web framework | FastAPI | Async, OpenAPI, type hints |
| ORM | SQLAlchemy 2.0 | Async, mature, flexible |
| Frontend | Vue 3 | Engil, TS support, ekosistema |
| State mgmt | Pinia | Vue 3 official |
| CSS | Tailwind | Utility-first, tez |
| DB | PostgreSQL | JSONB, full-text, ACID |
| Cache | Redis | Standart, tez |
| Search | OpenSearch | Open-source, ELK alternativ |
| Container | Docker | Industry standard |
| Orchestration | K8s | Auto-scaling, self-healing |
| Live video | Zoom + Jitsi | Bozorda yetakchi + alternativ |

## Keyingi qadam

- [02-tech-stack.md](02-tech-stack.md) — texnologik stek batafsil
- [03-folder-structure.md](03-folder-structure.md) — papka tuzilmasi
