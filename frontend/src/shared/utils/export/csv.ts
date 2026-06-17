// CSV eksport — brendlangan sarlavha qatorlari + jadval (BOM bilan, Excel-mos).
import { downloadBlob, timestampedFilename } from '@shared/utils/download'
import { BRAND, nowStamp } from './brand'
import type { CellValue, ExportSpec } from './types'

function esc(v: CellValue): string {
  const s = v === null || v === undefined ? '' : String(v)
  return `"${s.replace(/"/g, '""')}"`
}

export function toCsv(spec: ExportSpec): void {
  const rows: string[] = []
  rows.push(esc(BRAND.university))
  rows.push(esc(spec.title))
  if (spec.subtitle) rows.push(esc(spec.subtitle))
  rows.push(esc(`${BRAND.platform} — ${nowStamp()}`))
  for (const m of spec.meta ?? []) rows.push(`${esc(m.label)},${esc(m.value)}`)
  rows.push('')
  rows.push(spec.columns.map((c) => esc(c.label)).join(','))
  for (const r of spec.rows) {
    rows.push(spec.columns.map((c) => esc(r[c.key])).join(','))
  }
  const blob = new Blob(['﻿' + rows.join('\r\n')], {
    type: 'text/csv;charset=utf-8;',
  })
  downloadBlob(blob, timestampedFilename(spec.filename, 'csv'))
}
