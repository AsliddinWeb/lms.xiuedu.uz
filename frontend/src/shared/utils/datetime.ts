/**
 * Sana/vaqt formatlash — barcha tillar uchun tushunarli.
 *
 * Muammo: Intl.DateTimeFormat 'uz-Latn'/'uz-Cyrl' uchun oy va hafta nomlarini
 * bilmaydi — natijada "M06" (ICU root fallback) chiqadi. Shu sababli o'zbek
 * tillari uchun oy/hafta nomlarini O'ZIMIZ beramiz va sanani qo'lda yig'amiz;
 * ru/en uchun esa Intl'ga topshiramiz.
 *
 * Barcha komponentlar inline `new Intl.DateTimeFormat(intlLocale(...), opts)`
 * o'rniga shu yerdagi funksiyalarni ishlatishi kerak.
 */
import { intlLocale } from '@shared/i18n'

type AppLocale = string
type FieldStyle = 'numeric' | '2-digit' | 'long' | 'short'

export interface DateFormatOptions {
  weekday?: 'long' | 'short'
  year?: 'numeric' | '2-digit'
  month?: FieldStyle
  day?: 'numeric' | '2-digit'
  hour?: 'numeric' | '2-digit'
  minute?: 'numeric' | '2-digit'
}

// Oylar (getMonth: 0-11)
const MONTHS = {
  'uz-lat': {
    long: ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'],
    short: ['yan', 'fev', 'mar', 'apr', 'may', 'iyn', 'iyl', 'avg', 'sen', 'okt', 'noy', 'dek'],
  },
  'uz-cyr': {
    long: ['январ', 'феврал', 'март', 'апрел', 'май', 'июн', 'июл', 'август', 'сентабр', 'октабр', 'ноябр', 'декабр'],
    short: ['ян', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'],
  },
}

// Hafta kunlari (getDay: 0=yakshanba .. 6=shanba)
const WEEKDAYS = {
  'uz-lat': {
    long: ['yakshanba', 'dushanba', 'seshanba', 'chorshanba', 'payshanba', 'juma', 'shanba'],
    short: ['Yak', 'Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan'],
  },
  'uz-cyr': {
    long: ['якшанба', 'душанба', 'сешанба', 'чоршанба', 'пайшанба', 'жума', 'шанба'],
    short: ['Якш', 'Душ', 'Сеш', 'Чор', 'Пай', 'Жум', 'Шан'],
  },
}

function isUz(locale: AppLocale): locale is 'uz-lat' | 'uz-cyr' {
  return locale === 'uz-lat' || locale === 'uz-cyr'
}

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

function toDate(input: Date | string | number): Date | null {
  const d = input instanceof Date ? input : new Date(input)
  return Number.isNaN(d.getTime()) ? null : d
}

/**
 * Asosiy funksiya — `Intl.DateTimeFormat(intlLocale(locale), opts).format(date)`
 * o'rniga ishlatiladi. O'zbek tillarida tabiiy "8-iyun 2026, 14:30" beradi.
 */
export function formatDate(
  input: Date | string | number,
  locale: AppLocale,
  options: DateFormatOptions = {},
): string {
  const date = toDate(input)
  if (!date) return typeof input === 'string' ? input : ''

  // ru/en/boshqalar — Intl yetarli
  if (!isUz(locale)) {
    return new Intl.DateTimeFormat(intlLocale(locale), options).format(date)
  }

  const months = MONTHS[locale]
  const weekdays = WEEKDAYS[locale]
  const segs: string[] = []

  // Hafta kuni
  if (options.weekday) {
    segs.push(weekdays[options.weekday][date.getDay()])
  }

  // Sana qismi (kun / oy / yil)
  const dateBits: string[] = []
  const day = options.day === '2-digit' ? pad2(date.getDate()) : String(date.getDate())
  const hasNamedMonth = options.month === 'long' || options.month === 'short'

  if (options.day && hasNamedMonth) {
    // "8-iyun" — o'zbekcha tartib
    dateBits.push(`${day}-${months[options.month as 'long' | 'short'][date.getMonth()]}`)
  } else if (options.day && options.month) {
    // raqamli oy — "08.06"
    const mm = options.month === '2-digit' ? pad2(date.getMonth() + 1) : String(date.getMonth() + 1)
    dateBits.push(`${day}.${mm}`)
  } else if (options.day) {
    dateBits.push(day)
  } else if (hasNamedMonth) {
    dateBits.push(months[options.month as 'long' | 'short'][date.getMonth()])
  } else if (options.month) {
    dateBits.push(options.month === '2-digit' ? pad2(date.getMonth() + 1) : String(date.getMonth() + 1))
  }

  if (options.year) {
    dateBits.push(options.year === '2-digit' ? pad2(date.getFullYear() % 100) : String(date.getFullYear()))
  }

  const dateStr = dateBits.join(' ')
  let out = ''
  if (segs.length && dateStr) out = `${segs[0]}, ${dateStr}`
  else out = segs[0] ?? dateStr

  // Vaqt qismi — "14:30"
  if (options.hour || options.minute) {
    const time = `${pad2(date.getHours())}:${pad2(date.getMinutes())}`
    out = out ? `${out}, ${time}` : time
  }

  return out
}

// --- Qulaylik wrapperlari (eng ko'p ishlatiladigan formatlar) ---

/** "8-iyun 2026" / "Jun 8, 2026" */
export function formatFullDate(input: Date | string | number, locale: AppLocale): string {
  return formatDate(input, locale, { day: 'numeric', month: 'short', year: 'numeric' })
}

/** "8-iyun" / "Jun 8" */
export function formatDayMonth(input: Date | string | number, locale: AppLocale): string {
  return formatDate(input, locale, { day: '2-digit', month: 'short' })
}

/** "14:30" */
export function formatTime(input: Date | string | number, locale: AppLocale): string {
  return formatDate(input, locale, { hour: '2-digit', minute: '2-digit' })
}

/** "8-iyun 2026, 14:30" */
export function formatDateTime(input: Date | string | number, locale: AppLocale): string {
  return formatDate(input, locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
