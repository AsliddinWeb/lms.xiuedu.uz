/**
 * Phase 8f — Browser download helpers.
 *
 *   downloadBlob(blob, 'students.csv')
 */

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  // Bir oz vaqt o'tgach object URL'ni bo'shatish (browser hali yuklayotgan
  // bo'lishi mumkin — darhol revoke qilsak abort bo'lishi mumkin).
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function timestampedFilename(prefix: string, ext = 'csv'): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const ts =
    `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_` +
    `${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
  return `${prefix}_${ts}.${ext}`
}
