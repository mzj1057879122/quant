<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSignalList } from '../api/signal'
import { getLatestBrief } from '../api/brief'
// import { getBacktestStats } from '../api/backtest'
import { getWatchlistItems } from '../api/watchlist'
import SignalCard from '../components/SignalCard.vue'

const router = useRouter()
const loading = ref(false)

// 盘前纪要
const latestBrief = ref(null)
const briefExpanded = ref(false)

// 统计数字
const backtestRate = ref(null)
const watchlistCount = ref(0)
const todaySignalCount = ref(0)
const avgReturn = ref(null)

// 今日重点关注
const focusStocks = ref([])

// 最新突破信号
const recentSignals = ref([])

async function loadData() {
  loading.value = true
  try {
    const [briefRes, btRes, watchRes, signalCountRes, signalRes] = await Promise.all([
      getLatestBrief(),
      fetch('/api/v1/quant-backtest/runs').then(r => r.json()),
      getWatchlistItems({}),
      getSignalList({ pageSize: 1 }),
      getSignalList({ pageSize: 10 }),
    ])

    // 盘前纪要（不指定 source，取最新一条）
    latestBrief.value = briefRes.brief

    // 回测总胜率（量化策略 v7，取最新批次）
    try {
      const runsData = btRes
      const latestRun = (runsData.runs || [])[0]
      if (latestRun) {
        const summaryRes = await fetch(`/api/v1/quant-backtest/summary?runId=${latestRun}`)
        const summaryData = await summaryRes.json()
        backtestRate.value = summaryData.winRate ?? null
        avgReturn.value = summaryData.avgReturn ?? null
      }
    } catch (e) { /* 静默 */ }

    // 自选股总数
    watchlistCount.value = watchRes.total ?? 0

    // 今日重点关注：status=watching，按置信度排序，取前20
    const watchItems = (watchRes.items || []).filter(w => w.status === 'watching')
    const confidenceOrder = { '高': 0, '中': 1, '低': 2 }
    focusStocks.value = [...watchItems]
      .sort((a, b) => (confidenceOrder[a.confidence] ?? 3) - (confidenceOrder[b.confidence] ?? 3))
      .slice(0, 20)

    // 突破信号总数（用 pageSize=1 拿 total）
    todaySignalCount.value = signalCountRes.total ?? 0

    // 最新突破信号列表
    recentSignals.value = signalRes.items || []
  } catch (e) {
    // 静默
  } finally {
    loading.value = false
  }
}

function goToStock(code) {
  router.push(`/stocks/${code}`)
}

function goToSignal(signal) {
  router.push(`/stocks/${signal.stockCode}`)
}

function confidenceType(c) {
  return { '高': 'success', '中': 'warning', '低': 'danger' }[c] || ''
}

onMounted(loadData)
</script>

<template>
  <div v-loading="loading">
    <!-- 盘前概要 -->
    <el-card shadow="never" style="margin-bottom: 16px" v-if="latestBrief">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: 500">今日盘前概要 · {{ latestBrief.briefDate }}</span>
          <div style="display: flex; gap: 8px">
            <el-button text type="primary" @click="briefExpanded = !briefExpanded">
              {{ briefExpanded ? '收起' : '展开' }}
            </el-button>
            <el-button text type="primary" @click="router.push('/brief')">查看全文</el-button>
          </div>
        </div>
      </template>
      <div style="white-space: pre-wrap; font-size: 13px; line-height: 1.7; color: #333">
        <template v-if="briefExpanded">{{ latestBrief.rawContent }}</template>
        <template v-else>
          {{ latestBrief.rawContent?.slice(0, 300) }}{{ latestBrief.rawContent?.length > 300 ? '…' : '' }}
        </template>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-card shadow="never">
          <div style="text-align: center; padding: 8px 0">
            <div style="font-size: 28px; font-weight: bold; color: #409eff">
              {{ backtestRate !== null ? backtestRate + '%' : '-' }}
            </div>
            <div style="margin-top: 6px; color: #909399; font-size: 13px">回测总胜率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div style="text-align: center; padding: 8px 0">
            <div style="font-size: 28px; font-weight: bold; color: #67c23a">{{ watchlistCount }}</div>
            <div style="margin-top: 6px; color: #909399; font-size: 13px">自选股数量</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div style="text-align: center; padding: 8px 0">
            <div style="font-size: 28px; font-weight: bold; color: #e6a23c">
              {{ avgReturn !== null ? avgReturn + '%' : '-' }}
            </div>
            <div style="margin-top: 6px; color: #909399; font-size: 13px">平均收益率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div style="text-align: center; padding: 8px 0">
            <div style="font-size: 28px; font-weight: bold; color: #f56c6c">{{ todaySignalCount }}</div>
            <div style="margin-top: 6px; color: #909399; font-size: 13px">突破信号数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 重点关注列表（60%） -->
      <el-col :span="14">
        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="font-weight: 500">重点关注列表</span>
              <el-button text type="primary" @click="router.push('/watchlist')">查看全部</el-button>
            </div>
          </template>
          <div v-if="focusStocks.length === 0" style="text-align: center; color: #909399; padding: 30px 0">暂无关注股票</div>
          <el-table :data="focusStocks" size="small" @row-click="row => goToStock(row.stockCode)">
            <el-table-column prop="stockCode" label="代码" width="90">
              <template #default="{ row }">
                <el-link type="primary" @click.stop="goToStock(row.stockCode)">{{ row.stockCode }}</el-link>
              </template>
            </el-table-column>
            <el-table-column prop="stockName" label="名称" width="90" />
            <el-table-column prop="sector" label="板块" min-width="90" />
            <el-table-column label="置信度" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.confidence" :type="confidenceType(row.confidence)" size="small">{{ row.confidence }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="anchorPrice" label="锚位" width="75">
              <template #default="{ row }">{{ row.anchorPrice ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="距锚%" width="80">
              <template #default="{ row }">
                <span v-if="row.anchorDistPct !== null && row.anchorDistPct !== undefined"
                  :style="{ color: row.anchorDistPct >= 0 ? '#f56c6c' : '#67c23a' }">
                  {{ row.anchorDistPct > 0 ? '+' : '' }}{{ row.anchorDistPct }}%
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 最新突破信号（40%） -->
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="font-weight: 500">最新突破信号</span>
              <el-button text type="primary" @click="router.push('/signals')">查看全部</el-button>
            </div>
          </template>
          <div v-if="recentSignals.length === 0" style="text-align: center; color: #909399; padding: 30px 0">暂无信号数据</div>
          <SignalCard
            v-for="signal in recentSignals"
            :key="signal.id"
            :signal="signal"
            @click="goToSignal"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
