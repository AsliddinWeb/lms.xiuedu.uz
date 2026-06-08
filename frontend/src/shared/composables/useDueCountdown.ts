import { computed, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate } from '@shared/utils/datetime'

/**
 * Topshiriq due_date'ga nisbatan i18n-aware countdown matn qaytaradi.
 * Lokalga moslashgan, dakika/soat/kun granularligi bilan.
 */
export function useDueCountdown(dueIso: Ref<string | null | undefined>) {
  const { t, locale } = useI18n()

  const dueDate = computed(() =>
    dueIso.value ? new Date(dueIso.value) : null,
  )

  const minutesLeft = computed(() => {
    if (!dueDate.value) return null
    return Math.round((dueDate.value.getTime() - Date.now()) / 60000)
  })

  const isOverdue = computed(
    () => minutesLeft.value !== null && minutesLeft.value < 0,
  )

  const label = computed(() => {
    if (!dueDate.value) return ''
    const m = minutesLeft.value!
    if (m < 0) return t('assignments.due_overdue')

    const hours = Math.floor(m / 60)
    const days = Math.floor(hours / 24)
    const time = formatDate(dueDate.value, locale.value, {
      hour: '2-digit',
      minute: '2-digit',
    })

    const todayStart = new Date()
    todayStart.setHours(0, 0, 0, 0)
    const tomorrowStart = new Date(todayStart)
    tomorrowStart.setDate(tomorrowStart.getDate() + 1)
    const dayAfter = new Date(tomorrowStart)
    dayAfter.setDate(dayAfter.getDate() + 1)

    if (dueDate.value < tomorrowStart) {
      return t('assignments.due_today', { time })
    }
    if (dueDate.value < dayAfter) {
      return t('assignments.due_tomorrow', { time })
    }
    if (days >= 1) return t('assignments.due_in_days', { n: days })
    if (hours >= 1) return t('assignments.due_in_hours', { n: hours })
    return t('assignments.due_in_minutes', { n: Math.max(1, m) })
  })

  return { dueDate, minutesLeft, isOverdue, label }
}
