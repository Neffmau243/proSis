import { computed, ref } from 'vue'

/**
 * Estado de paginación para tablas que consumen PageResponse
 * (limit/offset/has_more). Nunca asumir que una página incompleta es la última.
 */
export function usePagination(initialLimit = 25) {
  const limit = ref(initialLimit)
  const offset = ref(0)
  const total = ref(0)
  const hasMore = ref(false)

  const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1)

  function applyPage(page: { total: number; has_more: boolean }): void {
    total.value = page.total
    hasMore.value = page.has_more
  }

  function goToPage(page: number): void {
    offset.value = (page - 1) * limit.value
  }

  function changeLimit(nextLimit: number): void {
    limit.value = nextLimit
    offset.value = 0
  }

  function reset(): void {
    offset.value = 0
    total.value = 0
    hasMore.value = false
  }

  return {
    limit,
    offset,
    total,
    hasMore,
    currentPage,
    applyPage,
    goToPage,
    changeLimit,
    reset,
  }
}