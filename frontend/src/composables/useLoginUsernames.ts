import { onMounted, shallowRef } from 'vue'

import { listActiveLoginUsernames } from '@/services/auth'

export function useLoginUsernames() {
  const usernames = shallowRef<string[]>([])
  const loading = shallowRef(false)
  const unavailable = shallowRef(false)

  async function load(): Promise<void> {
    loading.value = true
    unavailable.value = false

    try {
      usernames.value = await listActiveLoginUsernames()
    } catch {
      // Keep the login available even if its internal username directory is
      // temporarily unavailable.
      unavailable.value = true
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    void load()
  })

  return { usernames, loading, unavailable }
}
