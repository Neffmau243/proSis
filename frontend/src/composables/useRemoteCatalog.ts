import { onScopeDispose, shallowRef } from 'vue'

/** Bounded searches: debounce typing, ignore stale responses, retain selected options. */
export function useRemoteCatalog<T>(options: {
  fetch: (query: string | undefined) => Promise<{ items: T[] }>
  key: (item: T) => string | number
}) {
  const items = shallowRef<T[]>([])
  const loading = shallowRef(false)
  const error = shallowRef<string | null>(null)
  let version = 0
  let timer: ReturnType<typeof setTimeout> | undefined

  async function load(query?: string, retain: T[] = []): Promise<void> {
    const request = ++version
    loading.value = true
    error.value = null
    try {
      const page = await options.fetch(query)
      if (request !== version) return
      items.value = Array.from(
        new Map([...retain, ...page.items].map((item) => [options.key(item), item])).values(),
      )
    } catch (cause) {
      if (request === version)
        error.value = cause instanceof Error ? cause.message : 'No se pudieron cargar las opciones.'
    } finally {
      if (request === version) loading.value = false
    }
  }

  function search(query: string, retain: T[] = []): void {
    clearTimeout(timer)
    version += 1
    const text = query.trim()
    if (text.length === 1) {
      loading.value = false
      return
    }
    timer = setTimeout(() => {
      void load(text || undefined, retain)
    }, 250)
  }

  onScopeDispose(() => {
    clearTimeout(timer)
    version += 1
  })
  return { items, loading, error, load, search }
}
