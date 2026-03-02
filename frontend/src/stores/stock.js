import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getWatchList } from '../api/userConfig'

export const useStockStore = defineStore('stock', () => {
  const watchList = ref([])

  async function fetchWatchList() {
    try {
      const res = await getWatchList()
      watchList.value = res.stockCodes || []
    } catch (e) {
      // 静默失败
    }
  }

  return { watchList, fetchWatchList }
})
