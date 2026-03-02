import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getUnreadCount } from '../api/signal'

export const useSignalStore = defineStore('signal', () => {
  const unreadCount = ref(0)

  async function fetchUnreadCount() {
    try {
      const res = await getUnreadCount()
      unreadCount.value = res.count
    } catch (e) {
      // 静默失败
    }
  }

  return { unreadCount, fetchUnreadCount }
})
