# XIU LMS — masofaviy ta'lim platformasini ishlab chiqish

**Buyurtmachi:** Xalqaro Innovatsiya Universiteti (XIU)
**Ijrochi:** NEONSOFT MCHJ

---

## Loyihaning maqsadi

Universitetning o'quv jarayonini to'liq raqamlashtirish — talabalar, o'qituvchilar va ma'muriyat uchun yagona muhit yaratish. HEMIS bilan integratsiya, masofaviy darslar, baholash, kurs materiallari va kommunikatsiyani bitta zamonaviy tizimga birlashtirish.

---

## Loyiha doirasida bajarilgan asosiy ishlar

### 1. Foydalanuvchi tizimi va xavfsizlik

- JWT asosida autentifikatsiya, parol siyosati, "Eslab qol" mexanizmi
- 2FA (Authenticator orqali ikki bosqichli kirish) va zaxira kodlar
- Email tasdiqlash, parolni tiklash oqimi
- RBAC — rol va ruxsatlar tizimi (talaba, o'qituvchi, admin, super admin)
- HEMIS OAuth2 standart oqimi orqali avtomatik kirish

### 2. Akademik modul

- Fakultetlar, kafedralar, yo'nalishlar, fanlar bazasi
- O'quv rejalari (versiyalanadi) va o'quv kalendari (semestrlar, ta'tillar, imtihon davrlari)
- HEMIS bilan ma'lumotlarni avtomatik sinxronlash va audit log

### 3. Kurslar va o'quv materiallari

- Kurs konstruktori: modullar, darslar, kontent (video, PDF, matn, fayl, havola)
- Kursga yozilish (avto, qo'lda, self-enroll), kurs talabalari ro'yxati
- Talaba progressi: dars-darsbay yakunlanish, sertifikat avtomatik berilishi
- Kurslar katalogi va talaba "Mening kurslarim" sahifasi

### 4. Topshiriqlar va baholash

- Topshiriq turlari (essay, fayl yuklash), urinishlar soni va kechikish jarimasi
- Avtomatik va qo'lda baholash, rubric'lar, peer review
- Gradebook (oraliq, yakuniy, jami ball, harf bahoga konvertatsiya)
- GPA hisoblash va semestr ko'rsatkichlari
- Apellyatsiya tizimi

### 5. Live (jonli) darslar

- LiveKit WebRTC asosida video-konferens xona
- Ekran ulashish, audio-only rejim, qo'l ko'tarish, reaksiyalar
- Yozib olish va keyinchalik ko'rish (MinIO'da saqlash)
- Live dars jadvali va eslatmalar

### 6. Imtihonlar va proktoring

- Imtihon vaqti, ochilish/yopilish oqimi
- Avtomatik proktoring uchun infratuzilma
- Yaqinlashayotgan imtihonlar widget'i

### 7. Sertifikatlar

- Kursni 100% yakunlash bo'yicha avtomatik PDF sertifikat
- QR-kod va tasdiqlash sahifasi (public verify)
- Sertifikatlar reestri

### 8. Forum, chat va xabarnomalar

- Kurs forumi: mavzu, javob, "like", pin, lock, e'lon
- Real-vaqt chat (1-1, guruh, kurs guruhi) WebSocket orqali
- Push xabarnomalar (Email, SMS, Telegram bot, Web Push)
- Foydalanuvchi sozlamalari (kanal-by-kanal)

### 9. Gamifikatsiya

- Belgilar (badges), reyting (kunlik / haftalik / oylik)
- Ball tizimi va talabalar leaderboard

### 10. Admin panel

- Foydalanuvchilarni boshqarish, rollar va ruxsatlar
- Universitet sozlamalari, fakultetlar va kafedralar
- Kurslar va kontent boshqaruvi
- Hisobotlar va analitika
- To'liq audit log (har bir admin amali)

### 11. Talaba shaxsiy kabineti

- Bosh sahifa: faollik grafigi (7 kun / 30 kun / yil), seriya kunlar, eng faol kun
- Yaqinlashayotgan imtihonlar va live darslar widget'i
- O'qib chiqilmagan xabarnomalar
- Profil, avatar, til, vaqt mintaqasi sozlamalari

### 12. Ko'p tilli interfeys

- O'zbek (lotin), O'zbek (kirill), Rus, Ingliz tillarida to'liq tarjima

### 13. Xavfsizlik va monitoring

- Rate limiting (Redis bo'yicha), CSRF, XSS himoyasi
- Sentry orqali xato monitoringi
- To'liq audit log

---

## Foydalanilgan texnologiyalar

| Soha | Texnologiya |
|---|---|
| Backend | Python 3.11, FastAPI 0.110+, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Frontend | Vue 3 (Composition API) + TypeScript, Vite, Pinia, vue-i18n, Tailwind CSS |
| Ma'lumotlar bazasi | PostgreSQL 15 |
| Kesh va real-vaqt | Redis (rate-limit, pub/sub, session) |
| Fayl saqlash | MinIO (S3-mos), presigned URL'lar |
| Real-vaqt video | LiveKit WebRTC server |
| Konteynerlashtirish | Docker, Docker Compose v2 |
| Server | Ubuntu 22.04 LTS, nginx reverse proxy, Let's Encrypt SSL |
| Integratsiyalar | HEMIS OAuth2, SMTP, SMS gateway, Telegram bot |

---

## Loyiha natijasi

Universitet uchun to'liq ishchi holatga keltirilgan, production-ready masofaviy ta'lim platformasi yaratildi va serverga joriy etildi:

- **https://lms.xiuedu.uz** — talaba va o'qituvchi kabineti
- **https://lms-admin.xiuedu.uz** — administratsiya paneli
- **https://lms-api.xiuedu.uz** — backend API

Tizim 4 til (uz-lat, uz-cyr, ru, en), HEMIS bilan integratsiya, jonli darslar, avtomatik sertifikatlash va to'liq ma'muriy boshqaruv funksiyalari bilan ta'minlangan.

---

**Ijrochi:** NEONSOFT MCHJ
**Buyurtmachi:** Xalqaro Innovatsiya Universiteti (XIU)
