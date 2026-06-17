// PDF eksport — logo + brendlangan header (har sahifada) + jadval (jspdf-autotable).
// Unicode (uz/ru) matn uchun DejaVuSans shrifti lazy yuklanadi.
import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { BRAND, getLogoPng, nowStamp } from './brand'
import type { CellValue, ExportSpec } from './types'

const FONT = 'DejaVuSans'

function fmt(v: CellValue): string {
  return v === null || v === undefined ? '' : String(v)
}

export async function toPdf(spec: ExportSpec): Promise<void> {
  const landscape = spec.columns.length >= 6
  const doc = new jsPDF({
    orientation: landscape ? 'landscape' : 'portrait',
    unit: 'pt',
    format: 'a4',
  })

  // Unicode shrift (lazy chunk)
  try {
    const { dejaVuSansBase64 } = await import('./fonts/dejavuSans')
    doc.addFileToVFS('DejaVuSans.ttf', dejaVuSansBase64)
    doc.addFont('DejaVuSans.ttf', FONT, 'normal')
    doc.setFont(FONT)
  } catch {
    /* shrift bo'lmasa standart bilan davom (faqat lotin) */
  }

  const pageW = doc.internal.pageSize.getWidth()
  const margin = 40
  const d = BRAND.dark
  const mut = BRAND.muted

  // Logo (header bandida chiziladi)
  let logoPng: string | null = null
  try {
    logoPng = await getLogoPng(256)
  } catch {
    logoPng = null
  }

  const metaParts = [`${BRAND.platform} · ${nowStamp()}`]
  for (const m of spec.meta ?? []) metaParts.push(`${m.label}: ${m.value}`)
  const metaLine = metaParts.join('    ·    ')

  function drawHeader() {
    // Yuqori band
    doc.setFillColor(d.r, d.g, d.b)
    doc.rect(0, 0, pageW, 64, 'F')
    if (logoPng) doc.addImage(logoPng, 'PNG', margin, 12, 40, 40)
    const tx = margin + (logoPng ? 52 : 0)
    doc.setTextColor(255, 255, 255)
    doc.setFontSize(13)
    doc.text(BRAND.university, tx, 30)
    doc.setFontSize(9)
    doc.setTextColor(200, 210, 225)
    doc.text(BRAND.platform, tx, 46)
  }

  // Sahifa raqami (footer)
  function drawFooter() {
    const pageH = doc.internal.pageSize.getHeight()
    const page = doc.getNumberOfPages()
    doc.setFontSize(8)
    doc.setTextColor(mut.r, mut.g, mut.b)
    doc.text(`${page}`, pageW - margin, pageH - 16, { align: 'right' })
    doc.text(BRAND.university, margin, pageH - 16)
  }

  // Hisobot sarlavhasi (band ostida) — faqat 1-sahifa
  drawHeader()
  doc.setTextColor(d.r, d.g, d.b)
  doc.setFontSize(13)
  doc.text(spec.title, margin, 92)
  doc.setFontSize(9)
  doc.setTextColor(mut.r, mut.g, mut.b)
  let metaY = 108
  if (spec.subtitle) {
    doc.text(spec.subtitle, margin, metaY)
    metaY += 13
  }
  doc.text(metaLine, margin, metaY)

  const head = [spec.columns.map((c) => c.label)]
  const body = spec.rows.map((r) => spec.columns.map((c) => fmt(r[c.key])))

  const columnStyles: Record<number, { halign: 'left' | 'right' | 'center' }> = {}
  spec.columns.forEach((c, i) => {
    if (c.align) columnStyles[i] = { halign: c.align }
  })

  autoTable(doc, {
    head,
    body,
    startY: metaY + 14,
    margin: { left: margin, right: margin, top: 78 },
    styles: { font: FONT, fontSize: 8, cellPadding: 5, textColor: [30, 41, 59], lineColor: [BRAND.border.r, BRAND.border.g, BRAND.border.b], lineWidth: 0.3 },
    headStyles: { font: FONT, fillColor: [d.r, d.g, d.b], textColor: [255, 255, 255], fontSize: 9, halign: 'left' },
    alternateRowStyles: { fillColor: [BRAND.zebra.r, BRAND.zebra.g, BRAND.zebra.b] },
    columnStyles,
    didDrawPage: (data) => {
      // 2+ sahifalarda ham header bandi
      if (data.pageNumber > 1) drawHeader()
      drawFooter()
    },
  })

  doc.save(`${spec.filename}-${nowStamp().replace(/[.: ]/g, '-')}.pdf`)
}
