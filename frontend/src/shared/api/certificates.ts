/**
 * Sertifikatlar API klient — Phase 11d.
 *
 * Endpointlar /api/v1/me/certificates va public /api/v1/verify/{code}.
 */
import axios from 'axios'

import { apiClient } from './client'

export interface CertificateMyItem {
  id: number
  certificate_number: string
  course_id: number
  course_title: string
  score_percentage: string | null
  issued_at: string
  revoked_at: string | null
  pdf_url: string | null
  verification_url: string
}

export interface CertificateVerifyResponse {
  valid: boolean
  certificate_number?: string | null
  student_name?: string | null
  course_title?: string | null
  issued_at?: string | null
  revoked_at?: string | null
  revoke_reason?: string | null
  score_percentage?: string | null
}

export const certificatesApi = {
  async listMine(): Promise<CertificateMyItem[]> {
    const { data } = await apiClient.get<CertificateMyItem[]>('/me/certificates')
    return data
  },

  async getMine(id: number): Promise<CertificateMyItem> {
    const { data } = await apiClient.get<CertificateMyItem>(
      `/me/certificates/${id}`,
    )
    return data
  },

  async downloadPdfUrl(id: number): Promise<string> {
    // Backend 307 redirect bilan presigned URL beradi
    const { request } = await apiClient.get<unknown>(`/me/certificates/${id}/pdf`, {
      maxRedirects: 0,
      validateStatus: (s) => s < 400 || s === 307,
    })
    // axios browser'da redirectni avtomatik kuzatadi — alternativ: backenddan URL'ni JSON sifatida olish
    // Bu yerda fallback: window.open ushlaydi
    return (request?.responseURL as string) ?? ''
  },

  async verify(code: string): Promise<CertificateVerifyResponse> {
    // Public endpoint — autentifikatsiyasiz alohida axios chaqiriq
    const baseURL = import.meta.env.VITE_API_URL ?? '/api/v1'
    const { data } = await axios.get<CertificateVerifyResponse>(
      `${baseURL}/verify/${encodeURIComponent(code)}`,
    )
    return data
  },
}
