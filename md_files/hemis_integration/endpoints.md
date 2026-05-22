# HEMIS API — to'liq endpoint reference

**Avto-generate:** OpenAPI v3.0.0 spec asosida.
**Servers:** https://student.xiuedu.uz/rest/, https://student.hemis.uz/rest/
**Jami:** 255 endpoint


## 1. Backend API (67 ta)

| Method | Path | Summary | Required params |
|--------|------|---------|-----------------|
| GET | `/v1/data/academic-record-list` | Akkreditatsiya baxolari ro'yxati | — |
| GET | `/v1/data/all-subject-list` | Barcha fanlar ro'yxati | — |
| GET | `/v1/data/attendance-control-list` | Davomad jurnali ro'yxati | — |
| GET | `/v1/data/attendance-list` | Kunlik davomad ro'yxati | — |
| GET | `/v1/data/attendance-stat` | Davomad statistikasi | — |
| GET | `/v1/data/auditorium-list` | Auditoriyalar ro'yxati | — |
| GET | `/v1/data/bim-employee-subjects` | BIM uchun PINFL bo'yicha xodim fanlar ro'yxati | pinfl |
| GET | `/v1/data/bim-student-subjects` | BIM uchun PINFL bo'yicha student fanlar ro'yxati | pinfl |
| GET | `/v1/data/classifier-list` | Klassifikatorlar ro'yxati | — |
| GET | `/v1/data/contract-list` | Talaba kontraktlari ro'yxati | — |
| GET | `/v1/data/curriculum-list` | O'quv re'jalar ro'yxati | — |
| GET | `/v1/data/curriculum-subject-list` | O'quv rejaga tegishli fanlar ro'yxati | — |
| GET | `/v1/data/curriculum-subject-teacher-list` | O'quv reja fanlariga biriktirilgan o'qituvchilar ro'yxati | — |
| GET | `/v1/data/curriculum-subject-topic-list` | O'quv reja fanlariga biriktirilgan mavzular ro'yxati | — |
| GET | `/v1/data/daily-absence` | Kunlik dars qoldirish statistikasi | — |
| GET | `/v1/data/debtor-student-list` | Debtor students list | — |
| GET | `/v1/data/department-list` | Fakultetlar ro'yxati | — |
| GET | `/v1/data/diploma-list` | Diplomlar ro'yxati | — |
| GET | `/v1/data/doctorate-student-list` | Doctorate students list | — |
| GET | `/v1/data/employee-list` | O'qituvchilar va hodimlar ro'yxati | type |
| GET | `/v1/data/employee-stats` | Active employees statistics (grouped by various parameters) | — |
| GET | `/v1/data/employee-subject-list` | O'qituvchiga dars jadvali asosida biriktirilgan fanlar | — |
| GET | `/v1/data/exam-list` | Umumiy imtihonlari ro'yxati | — |
| GET | `/v1/data/grade-type-list` | Baho turlari ro'yxati | — |
| GET | `/v1/data/group-list` | Guruhlar ro'yxati | — |
| GET | `/v1/data/laboratory-specialty-list` | Laboratoriya soati mavjud yo'nalishlar ro'yxati | — |
| GET | `/v1/data/lesson-pair-list` | Juftliklar ro'yxati | — |
| GET | `/v1/data/marking-system-list` | Baholash tizimi ro'yxati | — |
| GET | `/v1/data/poll-list` | So'rovnomalar ro'yxati | — |
| GET | `/v1/data/publication-methodical-list` | Uslubiy nashrlar ro'yxati | — |
| GET | `/v1/data/publication-property-list` | Intelektual mulklar ro'yxati | — |
| GET | `/v1/data/publication-scientifical-list` | Ilmiy nashrlar ro'yxati | — |
| GET | `/v1/data/rating-grade-list` | Qaydnoma turlari ro'yxati | — |
| GET | `/v1/data/schedule-list` | Dars jadvali | — |
| GET | `/v1/data/schedule-teachers` | Tanlangan fanlar bo'yicha dars jadvali qo'yilgan o'qituvchilar ro'yxati | — |
| GET | `/v1/data/scientific-activity-list` | Ilmiy faollik ro'yxati | — |
| GET | `/v1/data/semester-list` | Semesterlar va o'quv haftalari ro'yxati | — |
| GET | `/v1/data/specialty-list` | Mutaxassisliklar ro'yxati | — |
| GET | `/v1/data/student-absence-count` | Talabaning joriy semestrdagi qoldirgan darslari soni | — |
| GET | `/v1/data/student-absence-count-list` | Talabalar bo'yicha joriy semestrda qoldirgan darslar statistikasi | — |
| GET | `/v1/data/student-academic-data` | Talabaning barcha akademik ma'lumotlari (fan, yuklama, kredit, ball, baho, semestr, o'quv yili) - PINFL yoki student_id_number bo'yicha | — |
| GET | `/v1/data/student-certificate-list` | Talabalar sertifikatlari ro'yxati | — |
| GET | `/v1/data/student-count-by-shift` | O'qiyotgan talabalar soni va smena bo'yicha taqsimoti | — |
| GET | `/v1/data/student-debt-stats` | Akademik qarzdorlik va dars qoldirish statistikasi | — |
| GET | `/v1/data/student-debtor-count` | Qarzdor talabalar soni (har bir talaba o'z joriy semestrida) | — |
| GET | `/v1/data/student-decree-download` | Talabaga tegishli buyruq (decree) faylini yuklab olish. student_id_number yoki passport_pin parametrlaridan biri yuborilishi shart. | id |
| GET | `/v1/data/student-document-download` | Talabaning hujjatini turi bo'yicha yuklab olish (id avtomatik aniqlanadi). student_id_number yoki passport_pin parametrlaridan biri yuborilishi kerak. | type |
| GET | `/v1/data/student-gpa-list` | Talaba GPA ro'yxati | — |
| GET | `/v1/data/student-gpa-rating` | Talabalar GPA reytingi (o'quv yili bo'yicha) | _education_year |
| GET | `/v1/data/student-grade-list` | Kunlik baholar ro'yxati | — |
| GET | `/v1/data/student-info` | Talabaning administrativ va akademik malumotlarni olish | — |
| GET | `/v1/data/student-info-download` | Talabaning xujjatlarini yuklab olish. Barcha xujjatlar ro'yxati data/student-info metodida qaytuvchi obyektning documents nompli maydonida ro'yxat qilib berilgan. | student_id_number, id, type |
| GET | `/v1/data/student-list` | Talabalar ro'yxati | — |
| GET | `/v1/data/student-meta-log-list` | Talaba meta tarixi ro'yxati | — |
| GET | `/v1/data/student-performance-list` | Talaba imtihon baxolari ro'yxati | — |
| GET | `/v1/data/student-stats` | Aktiv talabalar statistikasi (turli parametrlar bo'yicha) | — |
| GET | `/v1/data/student-subject-list` | Talabaga biriktirilgan fanlar ro'yxati | — |
| GET | `/v1/data/subject-exam-list` | Fan imtihonlari ro'yxati | — |
| GET | `/v1/data/subject-file-resource-list` | O'quv reja va fanga biriktirilgan fan resurslari ro'yxati | — |
| GET | `/v1/data/subject-meta-list` | Fanlar ro'yxati | — |
| GET | `/v1/data/subject-task-student-list` | Talabalarga berilgan topshiriqlar ro'yxati | — |
| GET | `/v1/data/system-log-list` | Tizim jurnali ro'yxati | — |
| GET | `/v1/data/teacher-workload` | O'qituvchilar yuklamasi - dars soatlari | — |
| GET | `/v1/data/transcript` | Talabaning transcript malumotlarni olish | — |
| GET | `/v1/data/validate-phone` | Berilgan telefon raqam tizimda mavjudligini tekshirish | phone |
| GET | `/v1/data/version-info` | Tizim haqida ma'lumot | — |
| POST | `/v1/sso/verify` | SSO Tokenni tekshirish | — |

## 2. Public API (6 ta)

| Method | Path | Summary | Required params |
|--------|------|---------|-----------------|
| GET | `/v1/public/stat-employee` | Statistika - hodimlar bo'yicha | — |
| GET | `/v1/public/stat-structure` | Statistika - tuzilma bo'yicha | — |
| GET | `/v1/public/stat-student` | Statistika - talabalar bo'yicha | — |
| GET | `/v1/public/university-api-urls` | Universitet API manzillari | — |
| GET | `/v1/public/university-list` | HEMIS tizimidan foydalanayotgan barcha oliygohlar ro'yxati | — |
| GET | `/v1/public/university-profile` | Universitetning profil ma'lumotlari | — |

## 3. Student API (93 ta)

| Method | Path | Summary | Required params |
|--------|------|---------|-----------------|
| GET | `/v1/account/me` | Talabaning shaxsiy va akademik ma'lumotlari | — |
| GET | `/v1/account/refresh` | Talaba ayrim malumotlarini tashqi xizmatlardan yangilash | type |
| POST | `/v1/account/update` | Talaba ma'lumotlarini yangilash | — |
| POST | `/v1/ai/chat` | AI chatbot bilan suhbat | — |
| GET | `/v1/ai/history` | AI chatbot suhbat tarixi | — |
| GET | `/v1/ai/keywords` | Mavjud AI keyword lar ro'yxati | — |
| POST | `/v1/auth/login` | Talaba login paroli orqali avtorizatsiya qilish | — |
| POST | `/v1/auth/refresh-token` | JWT tokenni yangilash | X-Refresh-Token |
| GET | `/v1/billing/all` | Barcha billing ma'lumotlarini olish (uch API birgalikda) | — |
| GET | `/v1/billing/credit-module-contract` | Kredit modulli shartnoma ma'lumotlari | — |
| GET | `/v1/billing/residence-contract` | Yashash joyi shartnoma ma'lumotlari | — |
| POST | `/v1/billing/subsidy-rent-report` | Subsidiyali ijara arizasi hisoboti (MyGov) | — |
| GET | `/v1/data/student-subject-debts` | Talabaning fanlar bo'yicha qarzdorligi (PINFL orqali) | pinfl |
| GET | `/v1/education/attendance` | Talabaning davomadi | — |
| GET | `/v1/education/exam-table` | Talabaning imtihonlar jadvali | — |
| GET | `/v1/education/gpa-list` | Talabaning GPA ballari | — |
| GET | `/v1/education/gpa-rating` | Talabaning GPA bo'yicha reytingdagi o'rni | — |
| GET | `/v1/education/grade-type-list` | Baho turlari ro'yxati | — |
| GET | `/v1/education/performance` | Talabaning kunlik baholari | — |
| GET | `/v1/education/resources` | Talaba fanlariga biriktirilgan elektron resurslari | — |
| GET | `/v1/education/schedule` | Talabaning dars jadvali | — |
| GET | `/v1/education/semesters` | Talaba o'quv re'jasidagi semesterlar | — |
| GET | `/v1/education/subject` | Talabaga biriktirilgan fan ma'lumotlari | — |
| GET | `/v1/education/subject-list` | Talabaga biriktirilgan fanlar va fan natijalari | — |
| GET | `/v1/education/subjects` | Talabaga biriktirilgan fanlar | — |
| POST | `/v1/education/task-answer` | Test savoliga javob berish | — |
| GET | `/v1/education/task-detail` | Talabaga biriktirilgan topshiriq ma'lumotlari | — |
| POST | `/v1/education/task-finish` | Testni yakunlash va natijani saqlash | — |
| GET | `/v1/education/task-list` | Talabaga biriktirilgan fan uchun topshiriqlar ro'yxati | — |
| POST | `/v1/education/task-start` | Test topshirig'ini boshlash va savollarni olish | — |
| POST | `/v1/education/task-upload` | Topshiriqga javob yuborish | — |
| GET | `/v1/education/task-upload-check` | Topshiriqga javob yuborish mumkin ekanligini tekshirish | — |
| POST | `/v1/exam/answer` | Imtihon savoliga javob belgilash | — |
| POST | `/v1/exam/finish` | Imtihonni yakunlash | — |
| GET | `/v1/exam/list` | Talaba uchun mavjud imtihonlar ro'yxati | — |
| GET | `/v1/exam/result` | Imtihon natijalarini ko'rish | exam |
| POST | `/v1/exam/start` | Imtihonni boshlash va savollarni olish | — |
| POST | `/v1/exam/verify-face` | Yuz tasdiqdan o'tkazish (Face Verification) | — |
| GET | `/v1/grant-application/application` | Bitta arizaning ma'lumotlarini olish (history bilan) | id |
| GET | `/v1/grant-application/applications` | Talabaning Grand arizalari ro'yxati | — |
| POST | `/v1/grant-application/delete` | Draft arizani o'chirish | id |
| GET | `/v1/grant-application/filter-options` | Grant shakllari va grant turlari ro'yxati | — |
| GET | `/v1/grant-application/profile` | Grandga talabgor arizasi uchun talabaning ma'lumotlari, GPA, ballari, grant turlari va ariza topshirish muddati (submission_window: start_date, end_date, is_open, error) | — |
| POST | `/v1/grant-application/save` | Arizani draft sifatida saqlash (yaratish/tahrirlash) | — |
| POST | `/v1/grant-application/submit` | Arizani yuborish (final submit) | — |
| GET | `/v1/plagiarism/balance` | Antiplagiat tizimi balansi | — |
| GET | `/v1/plagiarism/categories` | Antiplagiat hujjat kategoriyalari | — |
| POST | `/v1/plagiarism/certificate/{documentId}` | Hujjat antiplagiat sertifikatini yuklab olish | documentId |
| DELETE | `/v1/plagiarism/delete/{id}` | Yuklangan plagiat hujjatini o'chirish | id |
| GET | `/v1/plagiarism/document-types` | Hujjat turlari royxati | — |
| GET | `/v1/plagiarism/file/{id}` | Yuklangan plagiat faylini ko'rish/yuklab olish | id |
| GET | `/v1/plagiarism/history` | Talabaning plagiat tekshiruv tarixi | — |
| GET | `/v1/plagiarism/result/{documentId}` | Hujjat tekshiruv natijasi | documentId |
| POST | `/v1/plagiarism/send/{id}` | Submit uploaded document for antiplag.uz check | id |
| GET | `/v1/plagiarism/services` | Antiplagiat tekshirish xizmatlari royxati | — |
| GET | `/v1/plagiarism/status/{documentId}` | Hujjat tekshiruv holati | documentId |
| POST | `/v1/plagiarism/upload` | Hujjatni plagiat tekshiruvi uchun yuklash | — |
| POST | `/v1/poll/answer` | So'rovnomaga javob berish | — |
| GET | `/v1/poll/list` | Talaba uchun mavjud so'rovnomalar ro'yxati | — |
| GET | `/v1/poll/view` | So'rovnoma tafsilotlari | uid |
| GET | `/v1/social-activity/application` | Bitta arizaning ma'lumotlarini olish | id |
| POST | `/v1/social-activity/application-delete` | Arizani o'chirish | id |
| POST | `/v1/social-activity/application-save` | Ariza yaratish yoki yangilash | — |
| POST | `/v1/social-activity/application-submit` | Arizani ko'rib chiqishga yuborish | id |
| GET | `/v1/social-activity/applications` | Talabaning ijtimoiy faollik arizalari ro'yxati | — |
| POST | `/v1/social-activity/criteria-save` | Yo'nalish (tab) bo'yicha mezonlarni saqlash | — |
| GET | `/v1/social-activity/directions` | Ijtimoiy faollik yo'nalishlari va mezonlari | — |
| POST | `/v1/social-activity/file-upload` | Mezon uchun asos faylni yuklash | — |
| GET | `/v1/social-activity/rating` | Talabalar reytingi - o'z kursi va yo'nalishidagi talabalar | — |
| GET | `/v1/sso/get-redirect-url` | SSO redirect URL va token olish | target |
| GET | `/v1/sso/targets` | Mavjud SSO manzillar ro'yxati | — |
| GET | `/v1/student/certificate` | Talaba sertifikatlari | — |
| GET | `/v1/student/contract` | Talabaning joriy yilgi kontrakti | — |
| GET | `/v1/student/contract-list` | Talabaning kontraktlari ro'yxati | — |
| GET | `/v1/student/decree` | Talaba buyruqlari | — |
| GET | `/v1/student/document` | Talabaning boshqa turdagi xujjatlari | — |
| GET | `/v1/student/document-all` | Talabaning barcha xujjatlari | — |
| GET | `/v1/student/message-contact-search` | Xabar yuborish uchun kontaktlarni qidirish | — |
| POST | `/v1/student/message-delete` | Xabarni o'chirish | — |
| GET | `/v1/student/message-list` | Talaba xabarlari ro'yxati | — |
| POST | `/v1/student/message-send` | Xabar yuborish | — |
| GET | `/v1/student/message-view` | Xabarni ko'rish | id |
| GET | `/v1/student/payment-history` | Talabaning to'lov tarixi | — |
| GET | `/v1/student/plagiarism` | Talaba antiplagiat tizimi orqali tekshirilgan xujjatlari | — |
| POST | `/v1/student/qr-attendance` | QR kod orqali davomatni belgilash | — |
| GET | `/v1/student/reference` | Talaba ma'lumotnomalari | — |
| GET | `/v1/student/reference-generate` | Talaba ma'lumotnomasini generatsiya qilish | — |
| GET | `/v1/student/scholarship` | Student scholarship information | — |
| GET | `/v1/student/stipend-list` | Talabaning stipendiyalari ro'yxati | — |
| GET | `/v1/student/survey` | Talaba so'rovnomalari ro'yxati | — |
| POST | `/v1/student/survey-answer` | Savolga javob berish | — |
| POST | `/v1/student/survey-finish` | So'rovnomani yakunlash | — |
| POST | `/v1/student/survey-start` | So'rovnomani boshlash | — |

## 4. Tutor API (76 ta)

| Method | Path | Summary | Required params |
|--------|------|---------|-----------------|
| GET | `/v1/tutor/social-activity/application` | Tyutor uchun bitta ariza to'liq ma'lumoti | id |
| POST | `/v1/tutor/social-activity/application-approve` | Arizani to'liq tasdiqlash | id |
| POST | `/v1/tutor/social-activity/application-reject` | Arizani rad etish (izoh majburiy) | — |
| GET | `/v1/tutor/social-activity/applications` | Tyutor talabalarining ijtimoiy faollik arizalari | — |
| GET | `/v1/tutor/social-activity/calculate-system-scores` | HEMIS tizimidan avtomatik ball hisoblash (GPA/Davomad) | application_id |
| POST | `/v1/tutor/social-activity/category-approve` | Kategoriya mezonlarini to'liq tasdiqlash | — |
| POST | `/v1/tutor/social-activity/criteria-approve` | Ariza mezonini tasdiqlash | — |
| POST | `/v1/tutor/social-activity/criteria-reject` | Ariza mezonini rad etish | — |
| POST | `/v1/tutor/social-activity/criteria-save` | Tyutor tomonidan Yo'nalish bo'yicha mezonlarni saqlash | — |
| POST | `/v1/tutor/social-activity/direction-reject` | Ariza yo'nalishini rad etish (izoh majburiy) | — |
| GET | `/v1/tutor/social-activity/directions` | Ijtimoiy faollik yo'nalishlari va mezonlari | — |
| POST | `/v1/tutor/social-activity/file-upload` | Tyutor tomonidan mezon uchun asos faylni yuklash | — |
| POST | `/v1/tutor/social-activity/manual-system-criteria` | Tizim kategoriyasi uchun qo'lda mezon kiritish | — |
| GET | `/v1/tutor/social-activity/rating` | Talabalar reytingi - tyutor guruhlari bo'yicha | — |
| GET | `/ver1/tutor/attendance/by-subject` | Fanlar bo'yicha davomat (har bir dars uchun batafsil ma'lumot) | — |
| GET | `/ver1/tutor/attendance/report` | Davomat hisoboti | — |
| GET | `/ver1/tutor/attendance/statistic` | Statistik davomat | — |
| POST | `/ver1/tutor/auth/login` | Tutor login va parol orqali avtorizatsiya qilish | — |
| POST | `/ver1/tutor/auth/logout` | Tizimdan chiqish | — |
| POST | `/ver1/tutor/auth/refresh-token` | JWT tokenni yangilash | — |
| GET | `/ver1/tutor/contract/debtors` | Qarzi bo'lgan talabalar | — |
| GET | `/ver1/tutor/contract/list` | Kontraktlar ro'yxati | — |
| GET | `/ver1/tutor/contract/view` | Kontrakt tafsiloti | id |
| GET | `/ver1/tutor/grade/debtors` | Qarzdor talabalar | education_year |
| GET | `/ver1/tutor/grade/gpa` | GPA ballar | — |
| GET | `/ver1/tutor/grade/rating` | Reyting qaydnomasi | education_year |
| GET | `/ver1/tutor/grade/student` | Talaba baholari | id |
| GET | `/ver1/tutor/grade/summary` | Jamlanma qaydnoma | — |
| GET | `/ver1/tutor/group/list` | Guruhlar ro'yxati | — |
| GET | `/ver1/tutor/group/semesters` | Guruhning semestrlar ro'yxati | group_id |
| GET | `/ver1/tutor/group/students` | Guruh talabalari | id |
| GET | `/ver1/tutor/group/view` | Guruh tafsiloti | id |
| GET | `/ver1/tutor/message/list` | Mening xabarlarim ro'yxati | — |
| POST | `/ver1/tutor/message/mark-as-read` | Xabarni o'qilgan deb belgilash | — |
| GET | `/ver1/tutor/message/recipients` | Qabul qiluvchilar ro'yxati (xodimlar va talabalar) | — |
| POST | `/ver1/tutor/message/send` | Xabar yuborish | — |
| GET | `/ver1/tutor/message/view` | Xabarni ko'rish | id |
| GET | `/ver1/tutor/profile/groups` | Tyutorga tegishli guruhlar ro'yxati | — |
| GET | `/ver1/tutor/profile/index` | Tyutor profili ma'lumotlari | — |
| POST | `/ver1/tutor/profile/update` | Tyutor profilini yangilash | — |
| GET | `/ver1/tutor/reference/accommodations` | Turar joy turlari ro'yxati | — |
| GET | `/ver1/tutor/reference/countries` | Davlatlar ro'yxati | — |
| GET | `/ver1/tutor/reference/districts` | Tumanlar ro'yxati | province |
| GET | `/ver1/tutor/reference/education-years` | O'quv yillari ro'yxati | — |
| GET | `/ver1/tutor/reference/provinces` | Viloyatlar ro'yxati | — |
| GET | `/ver1/tutor/reference/semesters` | Semestrlar ro'yxati | — |
| GET | `/ver1/tutor/reference/specialties` | Mutaxassisliklar ro'yxati | — |
| GET | `/ver1/tutor/reference/student-living-statuses` | Talaba yashash holati ro'yxati | — |
| GET | `/ver1/tutor/reference/student-roommate-types` | Xonadosh turi ro'yxati | — |
| GET | `/ver1/tutor/reference/student-statuses` | Talaba statuslari ro'yxati | — |
| GET | `/ver1/tutor/reference/subjects` | Fanlar ro'yxati | — |
| GET | `/ver1/tutor/reference/terrains` | Mahallalar ro'yxati | district |
| GET | `/ver1/tutor/schedule/exam-info` | Nazorat (imtihon) jadvali holati | curriculum_id, education_year, semester |
| GET | `/ver1/tutor/schedule/exams` | Nazorat jadvali | — |
| GET | `/ver1/tutor/schedule/filter-options` | Jadval filtrlari uchun ma'lumotlar | — |
| GET | `/ver1/tutor/schedule/lessons` | Dars jadvali | — |
| GET | `/ver1/tutor/schedule/weekly` | Guruhlar bo'yicha haftalik jadval | week_id |
| GET | `/ver1/tutor/statistics/dashboard` | Tutor dashboard statistikalari | — |
| GET | `/ver1/tutor/statistics/leaderboard` | Barcha tyutorlar foydalanish reytingi (leaderboard) | — |
| GET | `/ver1/tutor/statistics/leaderboard-export` | Tyutorlar reytingini Excel formatda yuklab olish | — |
| GET | `/ver1/tutor/statistics/monitoring` | Tyutorning barcha jamlanma tashxil (monitoring) statistikalari | — |
| GET | `/ver1/tutor/statistics/rating` | Tyutorning shaxsiy foydalanish reytingi | — |
| GET | `/ver1/tutor/student/history` | Talaba tarixi | id |
| GET | `/ver1/tutor/student/history-list` | Tyutor talabalari tarixi ro'yxati | — |
| GET | `/ver1/tutor/student/list` | Tyutor talabalari ro'yxati | — |
| GET | `/ver1/tutor/student/passport` | Talaba pasporti | id |
| POST | `/ver1/tutor/student/update` | Talaba ma'lumotlarini yangilash | id |
| GET | `/ver1/tutor/student/view` | Talaba anketasi | id |
| POST | `/ver1/tutor/student/visit-create` | Talaba tashrifini qayd etish | id |
| GET | `/ver1/tutor/student/visit-list` | Tyutor talabalari ro'yxati (tashrif ma'lumotlari bilan) | — |
| POST | `/ver1/tutor/task/create` | Yangi vazifa yaratish | — |
| GET | `/ver1/tutor/task/detail` | Vazifa tafsilotlari | id |
| POST | `/ver1/tutor/task/file-delete` | Vazifa faylini o'chirish | — |
| POST | `/ver1/tutor/task/file-upload` | Vazifa uchun fayl yuklash | — |
| GET | `/ver1/tutor/task/list` | Tyutor vazifalari ro'yxati | — |
| POST | `/ver1/tutor/task/update` | Vazifani yangilash (nomi, tavsifi, sanasi, natija, fayl, status) | — |

## 5. Fast API (12 ta)

| Method | Path | Summary | Required params |
|--------|------|---------|-----------------|
| POST | `/` | Chatting | token |
| GET | `/allowed-universities` | Get Allowed Universities | token |
| POST | `/check-plagiarism` | Check Plagiarism | token |
| POST | `/contract-info` | Get Contract Info | token |
| POST | `/course-recommendation` | Get Course Recommendation | token |
| GET | `/history` | Get Info | token |
| DELETE | `/history` | Delete Chat | token |
| POST | `/reload_allowed_universities` | Reload Allowed Universities | — |
| POST | `/student-gpa-summary` | Get Student Gpa Summary | token |
| POST | `/student-grade-summary` | Get Student Grade Summary | token |
| POST | `/student-subjects-summary` | Get Student Subject Summary | token |
| POST | `/student-timetable-summary` | Get Student Timetable Summary | token |

## Stat (1 ta)

| Method | Path | Summary | Required params |
|--------|------|---------|-----------------|
| GET | `/public/stat-tutor-monitoring` | Tutor monitoring statistikasini olish | — |

---

## Schema'lar (91 ta)

- `AcademicInformation`
- `AcademicRecord`
- `Admin`
- `Attendance`
- `AttendanceControl`
- `AttendanceStat`
- `Auditorium`
- `AuthRequest`
- `BadResponse`
- `Building`
- `Classifier`
- `Curriculum`
- `CurriculumStudent`
- `CurriculumSubject`
- `CurriculumSubjectDetail`
- `CurriculumSubjectExamType`
- `CurriculumSubjectMeta`
- `CurriculumSubjectTeacher`
- `CurriculumSubjectTopic`
- `CurriculumWeek`
- `Department`
- `DoctorateStudent`
- `EducationYear`
- `Employee`
- `EmployeeMeta`
- `EmployeeSubject`
- `Exam`
- `ExamGroup`
- `ExamQuestion`
- `ExamStudent`
- `File`
- `ForbiddenResponse`
- `ForeignCertificate`
- `GenericStat`
- `GradeType`
- `Group`
- `GroupMeta`
- `HTTPValidationError`
- `LessonPair`
- `MarkingSystem`
- `Message`
- `MessageContact`
- `MessageItem`
- `NotFoundResponse`
- `Pagination`
- `Poll`
- `PollOption`
- `PollUser`
- `PollUserSubject`
- `Question`
- `RatingGrade`
- `Response`
- `ScheduleTeacher`
- `Semester`
- `SemesterMeta`
- `Specialty`
- `SpecialtyMeta`
- `Student`
- `StudentAttendance`
- `StudentDataContract`
- `StudentDataPlagiarism`
- `StudentDataStipend`
- `StudentDecree`
- `StudentDiploma`
- `StudentEducationFormStatisticsItem`
- `StudentExam`
- `StudentGpa`
- `StudentGrade`
- `StudentMeta`
- `StudentMetaLog`
- `StudentPerformance`
- `StudentReference`
- `StudentSubject`
- `StudentSubjectMeta`
- `Subject`
- `SubjectFieResourceItem`
- `SubjectFileResource`
- `SubjectGroup`
- `SubjectMeta`
- `SubjectSchedule`
- `SubjectTaskStudent`
- `SubjectTaskStudentActivity`
- `SubjectTaskStudentMeta`
- `SystemClassifier`
- `SystemLog`
- `Token`
- `Tutor`
- `TutorAuthRequest`
- `University`
- `UniversityProfile`
- `ValidationError`
