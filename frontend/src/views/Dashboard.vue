<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSignalList, getSignalStatistics } from '../api/signal'
import { getWatchList } from '../api/userConfig'
import { getLatestQuote } from '../api/stock'
import SignalCard from '../components/SignalCard.vue'
import StatusBadge from '../components/StatusBadge.vue'

const router = useRouter()
const recentSignals = ref([])
const statistics = ref([])
const watchStocks = ref([])
const loading = ref(false)

const statTypeLabels = {
  approaching: '接近前高',
  breakout: '突破前高',
  failed: '突破失败',
  // 旧类型兼容
  breakout_confirm: '突破确认',
  false_breakout: '假突破',
  breakdown: '突破失败下跌',
}

async function loadData() {
  loading.value = true
  try {
    const [signalRes, statRes, watchRes] = await Promise.all([
      getSignalList({ pageSize: 20 }),
      getSignalStatistics({}),
      getWatchList(),
    ])
    recentSignals.value = signalRes.items || []
    statistics.value = statRes.items || []

    // 加载关注股票的最新行情
    const codes = watchRes.stockCodes || []
    const stockPromises = codes.slice(0, 20).map(async (code) => {
      try {
        const quote = await getLatestQuote(code)
        return { stockCode: code, ...quote }
      } catch {
        return { stockCode: code, stockName: '--', closePrice: '--', changePct: null }
      }
    })
    watchStocks.value = await Promise.all(stockPromises)
  } catch (e) {
    // 静默
  } finally {
    loading.value = false
  }
}

function goToStock(stockCode) {
  router.push(`/stocks/${stockCode}`)
}

function goToSignal(signal) {
  router.push(`/stocks/${signal.stockCode}`)
}

onMounted(loadData)
</script>

<template>
  <div v-loading="loading">
    <!-- 信号统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 20px">
      <el-col :span="4" v-for="stat in statistics" :key="stat.signalType">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 28px; font-weight: bold; color: #409eff">{{ stat.count }}</div>
            <div style="margin-top: 8px; color: #909399; font-size: 13px">
              {{ statTypeLabels[stat.signalType] || stat.signalType }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4" v-if="statistics.length === 0">
        <el-card shadow="hover">
          <div style="text-align: center; color: #909399">暂无信号统计</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 最新信号 -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="font-weight: 500">最新信号</span>
              <el-button text type="primary" @click="router.push('/signals')">查看全部</el-button>
            </div>
          </template>
          <div v-if="recentSignals.length === 0" style="text-align: center; color: #909399; padding: 40px 0">
            暂无信号数据
          </div>
          <SignalCard
            v-for="signal in recentSignals.slice(0, 10)"
            :key="signal.id"
            :signal="signal"
            @click="goToSignal"
          />
        </el-card>
      </el-col>

      <!-- 关注股票行情 -->
      <el-col :span="10">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="font-weight: 500">关注股票</span>
              <el-button text type="primary" @click="router.push('/stocks')">管理</el-button>
            </div>
          </template>
          <div v-if="watchStocks.length === 0" style="text-align: center; color: #909399; padding: 40px 0">
            暂未关注任何股票
          </div>
          <div
            v-for="stock in watchStocks"
            :key="stock.stockCode"
            style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f0f0f0; cursor: pointer"
            @click="goToStock(stock.stockCode)"
          >
            <div>
              <span style="font-weight: 500">{{ stock.stockCode }}</span>
              <span style="margin-left: 8px; color: #606266">{{ stock.stockName || '--' }}</span>
            </div>
            <div style="text-align: right">
              <div style="font-weight: 500">{{ stock.closePrice || '--' }}</div>
              <div
                v-if="stock.changePct != null"
                :style="{ color: stock.changePct >= 0 ? '#ef5350' : '#26a69a', fontSize: '13px' }"
              >
                {{ stock.changePct >= 0 ? '+' : '' }}{{ stock.changePct }}%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
