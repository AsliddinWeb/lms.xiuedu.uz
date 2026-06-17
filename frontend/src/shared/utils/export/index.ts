// Professional eksport — markaziy kirish nuqtasi.
// CSV / Excel / PDF, brendlangan (logo + universitet sarlavhasi).
//
// Foydalanish:
//   import { exportTable } from '@shared/utils/export'
//   await exportTable('pdf', { title, columns, rows, filename, meta })
import { toCsv } from './csv'
import type { ExportFormat, ExportSpec } from './types'

export type { ExportColumn, ExportFormat, ExportMetaLine, ExportSpec, CellValue } from './types'

export async function exportTable(format: ExportFormat, spec: ExportSpec): Promise<void> {
  if (format === 'csv') {
    toCsv(spec)
    return
  }
  if (format === 'xlsx') {
    const { toExcel } = await import('./excel')
    await toExcel(spec)
    return
  }
  const { toPdf } = await import('./pdf')
  await toPdf(spec)
}
