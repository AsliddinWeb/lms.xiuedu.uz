import { defineStore } from 'pinia'
import { ref } from 'vue'

import { facultiesApi } from '@shared/api/academic'
import type { Faculty } from '@shared/types/academic'

export const useAcademicStore = defineStore('admin-academic', () => {
  const faculties = ref<Faculty[]>([])
  const facultiesLoaded = ref(false)

  async function fetchFaculties(force = false): Promise<void> {
    if (facultiesLoaded.value && !force) return
    const { items } = await facultiesApi.list({ page_size: 200 })
    faculties.value = items
    facultiesLoaded.value = true
  }

  function findFaculty(id: number | null | undefined): Faculty | undefined {
    return id == null ? undefined : faculties.value.find((f) => f.id === id)
  }

  return {
    faculties,
    facultiesLoaded,
    fetchFaculties,
    findFaculty,
  }
})
