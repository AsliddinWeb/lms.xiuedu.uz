"""Notifications moduli — Phase 7d.

In-app bildirishnomalar (sahifa qo'ng'irog'i + ro'yxat) + email fan-out
(MailHog dev, SendGrid prod). Asosiy hodisalar:

    exam.published      — imtihon e'lon qilindi (yozilgan talabalar)
    exam.graded         — urinish baholandi (manual grade)
    appeal.response     — apellyatsiyaga javob (apel beruvchi)
    live.scheduled      — live dars rejalashtirildi (kurs talabalari)
    live.starting       — live dars boshlanmoqda (5 daqiqada — Phase 8 scheduler)
"""
