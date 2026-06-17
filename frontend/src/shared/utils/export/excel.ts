// Excel (.xlsx) eksport — logo + brendlangan sarlavha + stillangan jadval.
import ExcelJS from 'exceljs'
import { downloadBlob, timestampedFilename } from '@shared/utils/download'
import { BRAND, getLogoPng, nowStamp } from './brand'
import type { CellValue, ExportSpec } from './types'

function cellText(v: CellValue): string | number {
  if (v === null || v === undefined) return ''
  return v
}

export async function toExcel(spec: ExportSpec): Promise<void> {
  const wb = new ExcelJS.Workbook()
  wb.creator = BRAND.platform
  wb.created = new Date()
  const ws = wb.addWorksheet(spec.title.slice(0, 28) || 'Hisobot', {
    views: [{ state: 'frozen', ySplit: 0 }],
  })

  const colCount = spec.columns.length
  const lastCol = String.fromCharCode(64 + Math.min(colCount, 26))

  // Ustun kengliklari
  ws.columns = spec.columns.map((c) => ({
    width: c.width ?? Math.max(14, c.label.length + 4),
  }))

  // Logo (top-left, suzuvchi)
  try {
    const png = await getLogoPng(256)
    const imgId = wb.addImage({ base64: png, extension: 'png' })
    ws.addImage(imgId, {
      tl: { col: 0, row: 0 },
      ext: { width: 46, height: 46 },
      editAs: 'oneCell',
    })
  } catch {
    /* logo bo'lmasa header'siz davom etadi */
  }

  // Sarlavha bloki (logo uchun A ustuni bo'sh qoldiriladi -> matn B'dan)
  const titleStartRow = 1
  const r1 = ws.getRow(titleStartRow)
  r1.height = 22
  ws.mergeCells(titleStartRow, 2, titleStartRow, colCount)
  const c1 = ws.getCell(titleStartRow, 2)
  c1.value = BRAND.university
  c1.font = { bold: true, size: 13, color: { argb: 'FF' + BRAND.dark.hex } }
  c1.alignment = { vertical: 'middle' }

  ws.mergeCells(2, 2, 2, colCount)
  const c2 = ws.getCell(2, 2)
  c2.value = spec.subtitle ? `${spec.title} — ${spec.subtitle}` : spec.title
  c2.font = { size: 11, color: { argb: 'FF' + BRAND.muted.hex } }

  ws.mergeCells(3, 1, 3, colCount)
  const metaParts = [`${BRAND.platform} · ${nowStamp()}`]
  for (const m of spec.meta ?? []) metaParts.push(`${m.label}: ${m.value}`)
  const c3 = ws.getCell(3, 1)
  c3.value = metaParts.join('   ·   ')
  c3.font = { size: 9, color: { argb: 'FF' + BRAND.muted.hex } }

  // Bo'sh qator
  const headerRowIdx = 5

  // Ustun sarlavhalari
  const headerRow = ws.getRow(headerRowIdx)
  headerRow.height = 20
  spec.columns.forEach((col, i) => {
    const cell = headerRow.getCell(i + 1)
    cell.value = col.label
    cell.font = { bold: true, size: 10, color: { argb: 'FF' + BRAND.light.hex } }
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF' + BRAND.dark.hex },
    }
    cell.alignment = { vertical: 'middle', horizontal: col.align ?? 'left' }
    cell.border = {
      bottom: { style: 'thin', color: { argb: 'FF' + BRAND.border.hex } },
    }
  })

  // Ma'lumot qatorlari
  spec.rows.forEach((r, ri) => {
    const row = ws.getRow(headerRowIdx + 1 + ri)
    spec.columns.forEach((col, ci) => {
      const cell = row.getCell(ci + 1)
      cell.value = cellText(r[col.key])
      cell.font = { size: 10, color: { argb: 'FF1E293B' } }
      cell.alignment = { vertical: 'middle', horizontal: col.align ?? 'left' }
      if (ri % 2 === 1) {
        cell.fill = {
          type: 'pattern',
          pattern: 'solid',
          fgColor: { argb: 'FF' + BRAND.zebra.hex },
        }
      }
      cell.border = {
        bottom: { style: 'hair', color: { argb: 'FF' + BRAND.border.hex } },
      }
    })
  })

  // Avtofiltr
  ws.autoFilter = {
    from: { row: headerRowIdx, column: 1 },
    to: { row: headerRowIdx, column: colCount },
  }
  void lastCol

  const buf = await wb.xlsx.writeBuffer()
  const blob = new Blob([buf], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  downloadBlob(blob, timestampedFilename(spec.filename, 'xlsx'))
}
