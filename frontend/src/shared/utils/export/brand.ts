// Eksport brendingi — universitet nomi, ranglar, logo (rasterizatsiya qilinadi).

export const BRAND = {
  university: 'Xalqaro innovatsion universiteti',
  platform: 'XIU EduPlatform',
  // Slate-900 — sarlavha foni (PDF/Excel)
  dark: { r: 15, g: 23, b: 42, hex: '0F172A' },
  // Sarlavha matni (oq)
  light: { r: 255, g: 255, b: 255, hex: 'FFFFFF' },
  // Muted matn (gray-500)
  muted: { r: 100, g: 116, b: 139, hex: '64748B' },
  // Jadval zebra fon (slate-50)
  zebra: { r: 248, g: 250, b: 252, hex: 'F8FAFC' },
  // Chiziq (slate-200)
  border: { r: 226, g: 232, b: 240, hex: 'E2E8F0' },
} as const

// Logo — brendlangan rounded mark ("XIU"). SVG sifatida, canvas orqali PNG'ga aylantiriladi.
const LOGO_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="52" fill="#0F172A"/>
  <text x="50%" y="50%" font-family="Helvetica, Arial, sans-serif" font-size="104" font-weight="700"
        letter-spacing="2" fill="#FFFFFF" text-anchor="middle" dominant-baseline="central">XIU</text>
</svg>`

let cachedLogo: string | null = null

/**
 * Logo SVG'ni PNG data-URL'ga aylantiradi (jsPDF.addImage va exceljs.addImage uchun).
 * Natija keshlanadi.
 */
export async function getLogoPng(size = 256): Promise<string> {
  if (cachedLogo) return cachedLogo
  const blob = new Blob([LOGO_SVG], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  try {
    const img = new Image()
    img.width = size
    img.height = size
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve()
      img.onerror = () => reject(new Error('logo yuklab bo\'lmadi'))
      img.src = url
    })
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('canvas context yo\'q')
    ctx.drawImage(img, 0, 0, size, size)
    cachedLogo = canvas.toDataURL('image/png')
    return cachedLogo
  } finally {
    URL.revokeObjectURL(url)
  }
}

/** Joriy vaqtni "DD.MM.YYYY HH:MM" ko'rinishida (eksport sarlavhasi uchun). */
export function nowStamp(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`
}
