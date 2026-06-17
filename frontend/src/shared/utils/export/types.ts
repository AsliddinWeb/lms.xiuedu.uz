// Professional eksport — umumiy tiplar (CSV / Excel / PDF).

export type ExportFormat = 'csv' | 'xlsx' | 'pdf'

export type CellValue = string | number | null | undefined

export interface ExportColumn {
  /** Qator obyektidagi kalit */
  key: string
  /** Ustun sarlavhasi (lokalizatsiya qilingan) */
  label: string
  /** Excel ustun kengligi (belgi soni) / PDF nisbiy og'irlik */
  width?: number
  /** Hizalash */
  align?: 'left' | 'right' | 'center'
}

/** Sarlavha ostidagi meta qatorlar (filtrlar, jami ko'rsatkichlar) */
export interface ExportMetaLine {
  label: string
  value: string
}

export interface ExportSpec {
  /** Hisobot sarlavhasi (masalan "Kurslar ro'yxati") */
  title: string
  /** Ixtiyoriy quyi sarlavha */
  subtitle?: string
  columns: ExportColumn[]
  rows: Array<Record<string, CellValue>>
  /** Fayl nomi asosi (kengaytma va vaqt belgisisiz) */
  filename: string
  /** Filtrlar / jami ko'rsatkichlar (sarlavha ostida ko'rsatiladi) */
  meta?: ExportMetaLine[]
  /** Lokal (sana formatlash uchun) */
  locale?: string
}
