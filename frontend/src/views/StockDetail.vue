<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getStockDetail, getQuotes, fetchQuotes } from '../api/stock'
import { getBreakoutAnalysis, getSignalList } from '../api/signal'
import { getBacktestList } from '../api/backtest'
import { getWatchlistItems, addWatchlistItem, deleteWatchlistItem } from '../api/watchlist'
import KLineChart from '../components/KLineChart.vue'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const stockCode = route.params.code

const stockInfo = ref(null)
const quotes = ref([])
const breakoutData = ref(null)
const signals = ref([])
const loading = ref(false)
const fetchLoading = ref(false)

// 新增：回测胜率
const backtestInfo = ref(null)

// 新增：watchlist 状态
const watchlistItem = ref(null)

async function loadData() {
  loading.value = true
  try {
    const [stockRes, quoteRes, analysisRes, signalRes, btAllRes, btCorrectRes, wlRes] = await Promise.all([
      getStockDetail(stockCode).catch(() => null),
      getQuotes(stockCode, { limit: 250 }),
      getBreakoutAnalysis(stockCode).catch(() => null),
      getSignalList({ stockCode, pageSize: 100 }),
      getBacktestList({ stockCode, pageSize: 1 }).catch(() => null),
      getBacktestList({ stockCode, isCorrect: 1, pageSize: 1 }).catch(() => null),
      getWatchlistItems({ status: '' }).catch(() => ({ items: [] })),
    ])
    stockInfo.value = stockRes
    quotes.value = quoteRes.items || []
    breakoutData.value = analysisRes
    signals.value = signalRes.items || []
    const btTotal = btAllRes?.total || 0
    const btCorrect = btCorrectRes?.total || 0
    backtestInfo.value = btTotal > 0
      ? { total: btTotal, correct: btCorrect, rate: Math.round(btCorrect / btTotal * 1000) / 10 }
      : null
    const wlItems = wlRes.items || []
    watchlistItem.value = wlItems.find(w => w.stockCode === stockCode) || null
  } catch (e) {
    // 静默
  } finally {
    loading.value = false
  }
}

async function toggleWatchlist() {
  if (watchlistItem.value) {
    await deleteWatchlistItem(stockCode)
    watchlistItem.value = null
    ElMessage.success('已从自选股池移除')
  } else {
    await addWatchlistItem({ stockCode, stockName: stockInfo.value?.stockName || stockCode })
    await loadData()
    ElMessage.success('已加入自选股池')
  }
}

async function handleFetch() {
  fetchLoading.value = true
  try {
    const res = await fetchQuotes(stockCode)
    ElMessage.success(`拉取完成，新增 ${res.count} 条`)
    await loadData()
  } catch (e) {
    // 静默
  } finally {
    fetchLoading.value = false
  }
}

// 将 breakoutData 和 watchlist 锚位组合成 KLineChart 所需的 previousHighs 格式
function getChartHighs() {
  const highs = []
  if (breakoutData.value?.currentHigh) {
    const h = breakoutData.value.currentHigh
    highs.push({ highPrice: h.highPrice, highDate: h.highDate, status: 'active', highType: 'local_high' })
  }
  if (watchlistItem.value?.anchorPrice) {
    highs.push({
      highPrice: watchlistItem.value.anchorPrice,
      highDate: watchlistItem.value.anchorDate || '',
      status: 'active',
      highType: 'anchor',
    })
  }
  return highs
}

const resultTagType = (result) => result === 'success' ? 'success' : 'danger'
const resultLabel = (result) => result === 'success' ? '突破成功' : '突破失败'

const statusMap = {
  approaching: { label: '接近前高', type: 'warning' },
  breakout: { label: '已突破', type: 'success' },
  below: { label: '低于前高', type: 'info' },
  none: { label: '无数据', type: 'info' },
}

const backtestColor = computed(() => {
  const rate = backtestInfo.value?.rate
  if (rate == null) return ''
  if (rate >= 85) return '#67c23a'
  if (rate >= 60) return '#e6a23c'
  return '#f56c6c'
})

const watchlistStatusLabel = computed(() => {
  const map = { watching: '关注中', holding: '持有', exited: '已出局' }
  return map[watchlistItem.value?.status] || watchlistItem.value?.status || ''
})

const watchlistStatusTagType = computed(() => {
  const map = { watching: 'primary', holding: 'success', exited: 'info' }
  return map[watchlistItem.value?.status] || 'info'
})

onMounted(loadData)
</script>

<template>
  <div v-loading="loading">
    <!-- 头部信息 -->
    <el-card style="margin-bottom: 20px">
      <div style="display: flex; justify-content: space-between; align-items: center">
        <div>
          <el-button text @click="router.back()" style="margin-right: 8px">
            <el-icon><ArrowLeft /></el-icon> 返回
          </el-button>
          <span style="font-size: 20px; font-weight: bold">
            {{ stockInfo?.stockCode || stockCode }}
          </span>
          <span style="margin-left: 12px; font-size: 18px; color: #606266">
            {{ stockInfo?.stockName || '' }}
          </span>
          <el-tag v-if="stockInfo?.market" size="small" style="margin-left: 12px">
            {{ stockInfo.market.toUpperCase() }}
          </el-tag>
          <span v-if="stockInfo?.industry" style="margin-left: 12px; color: #909399; font-size: 13px">
            {{ stockInfo.industry }}
          </span>
        </div>
        <div style="display: flex; gap: 8px; align-items: center">
          <el-button :type="watchlistItem ? 'default' : 'warning'" size="small" @click="toggleWatchlist">
            {{ watchlistItem ? '移出自选' : '加入自选' }}
          </el-button>
          <el-button :loading="fetchLoading" type="primary" @click="handleFetch">
            <el-icon><Download /></el-icon> 拉取最新数据
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- K线图 -->
    <el-card style="margin-bottom: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: 500">K线图</span>
          <div style="display: flex; gap: 12px; align-items: center">
            <!-- 回测胜率 -->
            <span
              v-if="backtestInfo"
              :style="{ color: backtestColor, fontWeight: '500', fontSize: '13px' }"
            >
              回测胜率：{{ backtestInfo.rate }}% (正确{{ backtestInfo.correct }}/共{{ backtestInfo.total }}次)
            </span>
            <!-- watchlist 状态 -->
            <el-tag v-if="watchlistItem" :type="watchlistStatusTagType" size="small">
              {{ watchlistStatusLabel }}
            </el-tag>
          </div>
        </div>
      </template>
      <div v-if="quotes.length === 0" style="text-align: center; color: #909399; padding: 60px 0">
        暂无行情数据，请先拉取数据
      </div>
      <KLineChart
        v-else
        :quotes="quotes"
        :previous-highs="getChartHighs()"
        :signals="signals"
      />
    </el-card>

    <el-row :gutter="20">
      <!-- 突破分析面板 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span style="font-weight: 500">突破分析</span>
          </template>

          <div v-if="!breakoutData || !breakoutData.currentHigh" style="text-align: center; color: #909399; padding: 30px 0">
            暂无分析数据，请先执行检测
          </div>

          <template v-else>
            <!-- 当前前高信息 -->
            <div style="margin-bottom: 16px; padding: 12px; background: #f5f7fa; border-radius: 6px">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
                <span style="font-weight: 500; font-size: 15px">当前前高</span>
                <el-tag :type="statusMap[breakoutData.currentStatus]?.type || 'info'" size="small">
                  {{ statusMap[breakoutData.currentStatus]?.label || breakoutData.currentStatus }}
                </el-tag>
              </div>
              <div style="display: flex; gap: 24px; font-size: 14px; color: #606266">
                <span>前高价: <b>{{ breakoutData.currentHigh.highPrice }}</b></span>
                <span>日期: {{ breakoutData.currentHigh.highDate }}</span>
                <span v-if="breakoutData.latestClose">最新收盘: {{ breakoutData.latestClose }}</span>
              </div>
            </div>

            <!-- 成功率统计 -->
            <el-row :gutter="12" style="margin-bottom: 16px">
              <el-col :span="6">
                <div style="text-align: center; padding: 8px 0">
                  <div style="font-size: 24px; font-weight: bold; color: #409eff">
                    {{ breakoutData.analysis.totalApproachCount }}
                  </div>
                  <div style="font-size: 12px; color: #909399; margin-top: 4px">总接近次数</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div style="text-align: center; padding: 8px 0">
                  <div style="font-size: 24px; font-weight: bold; color: #67c23a">
                    {{ breakoutData.analysis.breakoutSuccessCount }}
                  </div>
                  <div style="font-size: 12px; color: #909399; margin-top: 4px">突破成功</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div style="text-align: center; padding: 8px 0">
                  <div style="font-size: 24px; font-weight: bold; color: #f56c6c">
                    {{ breakoutData.analysis.breakoutFailCount }}
                  </div>
                  <div style="font-size: 12px; color: #909399; margin-top: 4px">突破失败</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div style="text-align: center; padding: 8px 0">
                  <div style="font-size: 24px; font-weight: bold" :style="{ color: breakoutData.analysis.successRate >= 50 ? '#67c23a' : '#f56c6c' }">
                    {{ breakoutData.analysis.successRate }}%
                  </div>
                  <div style="font-size: 12px; color: #909399; margin-top: 4px">成功率</div>
                </div>
              </el-col>
            </el-row>

            <!-- 历史事件表 -->
            <div v-if="breakoutData.historyEvents && breakoutData.historyEvents.length > 0">
              <div style="font-weight: 500; margin-bottom: 8px; font-size: 14px">历史事件</div>
              <el-table :data="breakoutData.historyEvents" size="small" max-height="300">
                <el-table-column prop="eventDate" label="日期" width="100" />
                <el-table-column prop="highPrice" label="前高价" width="80" />
                <el-table-column prop="approachPrice" label="接近价" width="80" />
                <el-table-column prop="result" label="结果" width="90">
                  <template #default="{ row }">
                    <el-tag :type="resultTagType(row.result)" size="small">
                      {{ resultLabel(row.result) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="涨幅" width="70">
                  <template #default="{ row }">
                    <span v-if="row.maxGainPct > 0" style="color: #ef5350">+{{ row.maxGainPct }}%</span>
                    <span v-else>--</span>
                  </template>
                </el-table-column>
                <el-table-column label="跌幅" width="70">
                  <template #default="{ row }">
                    <span v-if="row.maxDropPct < 0" style="color: #26a69a">{{ row.maxDropPct }}%</span>
                    <span v-else>--</span>
                  </template>
                </el-table-column>
                <el-table-column prop="daysToResult" label="天数" width="60" />
              </el-table>
            </div>
          </template>
        </el-card>
      </el-col>

      <!-- 信号历史 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span style="font-weight: 500">信号历史 ({{ signals.length }})</span>
          </template>
          <div v-if="signals.length === 0" style="text-align: center; color: #909399; padding: 30px 0">
            暂无信号记录
          </div>
          <el-table v-else :data="signals" size="small">
            <el-table-column prop="signalType" label="类型" width="110">
              <template #default="{ row }">
                <StatusBadge :type="row.signalType" />
              </template>
            </el-table-column>
            <el-table-column prop="signalDate" label="日期" width="110" />
            <el-table-column prop="previousHighPrice" label="前高价" width="80" />
            <el-table-column prop="closePrice" label="收盘价" width="80" />
            <el-table-column prop="successRate" label="成功率" width="70">
              <template #default="{ row }">
                <span v-if="row.successRate != null">{{ row.successRate }}%</span>
                <span v-else style="color: #c0c4cc">--</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
