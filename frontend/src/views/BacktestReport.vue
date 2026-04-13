<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const API = '/api/v1/quant-backtest'

// ── 状态 ──
const runs = ref([])
const selectedRun = ref('')
const summary = ref(null)
const loading = ref(false)
const triggering = ref(false)
const triggerRunId = ref('')

// 明细
const trades = ref([])
const tradeTotal = ref(0)
const tradePage = ref(1)
const tradePageSize = ref(50)
const filterStock = ref('')
const filterReason = ref('')
const sortBy = ref('return_pct')
const sortOrder = ref('desc')

// ECharts 实例
let quarterChart = null
let reasonChart = null

// ── 加载回测批次列表 ──
async function loadRuns() {
  const res = await fetch(`${API}/runs`)
  const data = await res.json()
  runs.value = data.runs || []
  if (runs.value.length > 0 && !selectedRun.value) {
    selectedRun.value = runs.value[0]
  }
}

// ── 加载汇总统计 ──
async function loadSummary() {
  if (!selectedRun.value) return
  loading.value = true
  try {
    const res = await fetch(`${API}/summary?runId=${selectedRun.value}`)
    if (!res.ok) { summary.value = null; return }
    summary.value = await res.json()
    await loadTrades()
    renderCharts()
  } finally {
    loading.value = false
  }
}

// ── 加载交易明细 ──
async function loadTrades() {
  if (!selectedRun.value) return
  const params = new URLSearchParams({
    runId: selectedRun.value,
    page: tradePage.value,
    pageSize: tradePageSize.value,
    sortBy: sortBy.value,
    sortOrder: sortOrder.value,
  })
  if (filterStock.value) params.append('stockCode', filterStock.value)
  if (filterReason.value) params.append('exitReason', filterReason.value)

  const res = await fetch(`${API}/trades?${params}`)
  const data = await res.json()
  trades.value = data.items || []
  tradeTotal.value = data.total || 0
}

// ── 手动触发回测 ──
async function triggerBacktest() {
  if (!triggerRunId.value.trim()) { alert('请填写批次ID'); return }
  triggering.value = true
  try {
    const res = await fetch(`${API}/trigger?runId=${triggerRunId.value}`, { method: 'POST' })
    const data = await res.json()
    alert(data.message)
    await loadRuns()
  } finally {
    triggering.value = false
  }
}

// ── ECharts 渲染 ──
function renderCharts() {
  if (!summary.value) return

  // 季度胜率柱状图
  const qDom = document.getElementById('quarterChart')
  if (qDom) {
    if (quarterChart) quarterChart.dispose()
    quarterChart = echarts.init(qDom)
    const quarters = summary.value.byQuarter || []
    quarterChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['交易次数', '胜率(%)'] },
      xAxis: { type: 'category', data: quarters.map(q => q.quarter), axisLabel: { rotate: 30 } },
      yAxis: [
        { type: 'value', name: '次数' },
        { type: 'value', name: '胜率(%)', min: 0, max: 100 },
      ],
      series: [
        {
          name: '交易次数', type: 'bar', data: quarters.map(q => q.total),
          itemStyle: { color: '#409eff' },
        },
        {
          name: '胜率(%)', type: 'line', yAxisIndex: 1,
          data: quarters.map(q => q.winRate),
          itemStyle: { color: '#67c23a' },
          label: { show: true, formatter: '{c}%' },
        },
      ],
    })
  }

  // 出场原因饼图
  const rDom = document.getElementById('reasonChart')
  if (rDom) {
    if (reasonChart) reasonChart.dispose()
    reasonChart = echarts.init(rDom)
    const reasons = summary.value.byExitReason || []
    const reasonNameMap = {
      volume_top: '极值量出场',
      stop_loss: '跌破锚位',
      time_stop: '时间止损',
      data_end: '数据截止',
    }
    reasonChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}次 ({d}%)' },
      legend: { orient: 'vertical', left: 'left' },
      series: [{
        name: '出场原因', type: 'pie', radius: '60%',
        data: reasons.map(r => ({
          name: reasonNameMap[r.reason] || r.reason,
          value: r.total,
        })),
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
      }],
    })
  }
}

// ── 排序处理 ──
function handleSortChange({ prop, order }) {
  sortBy.value = prop || 'return_pct'
  sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  tradePage.value = 1
  loadTrades()
}

// ── 收益率着色 ──
function returnClass(val) {
  if (val === null || val === undefined) return ''
  return val > 0 ? 'text-green' : val < 0 ? 'text-red' : ''
}

// ── 出场原因标签 ──
const reasonLabel = { volume_top: '极值量', stop_loss: '止损', time_stop: '时间止', data_end: '截止' }
const reasonType = { volume_top: 'warning', stop_loss: 'danger', time_stop: 'info', data_end: '' }

watch(selectedRun, () => { tradePage.value = 1; loadSummary() })
watch([filterStock, filterReason], () => { tradePage.value = 1; loadTrades() })
watch(tradePage, loadTrades)

onMounted(async () => {
  await loadRuns()
  if (selectedRun.value) await loadSummary()
})
</script>

<template>
  <div>
    <!-- 顶部操作栏 -->
    <el-row :gutter="16" style="margin-bottom: 20px" align="middle">
      <el-col :span="6">
        <el-select v-model="selectedRun" placeholder="选择回测批次" style="width: 100%">
          <el-option v-for="r in runs" :key="r" :label="r" :value="r" />
        </el-select>
      </el-col>
      <el-col :span="1">
        <el-button type="primary" :loading="loading" @click="loadSummary">刷新</el-button>
      </el-col>
      <el-col :span="8" :offset="1">
        <el-input
          v-model="triggerRunId"
          placeholder="新批次ID，如 2025_full"
          style="width: 200px; margin-right: 8px"
        />
        <el-button type="success" :loading="triggering" @click="triggerBacktest">触发回测</el-button>
      </el-col>
    </el-row>

    <div v-if="loading" style="text-align:center; padding: 40px">
      <el-text type="info">加载中...</el-text>
    </div>

    <template v-if="summary && !loading">
      <!-- 统计卡片 -->
      <el-row :gutter="16" style="margin-bottom: 20px">
        <el-col :span="4">
          <el-card shadow="never">
            <div style="font-size:13px;color:#909399">总交易次数</div>
            <div style="font-size:28px;font-weight:bold;color:#303133">{{ summary.total }}</div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card shadow="never">
            <div style="font-size:13px;color:#909399">胜率</div>
            <div style="font-size:28px;font-weight:bold;" :class="summary.winRate >= 50 ? 'text-green' : 'text-red'">
              {{ summary.winRate }}%
            </div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card shadow="never">
            <div style="font-size:13px;color:#909399">平均收益率</div>
            <div style="font-size:28px;font-weight:bold;" :class="summary.avgReturn >= 0 ? 'text-green' : 'text-red'">
              {{ summary.avgReturn > 0 ? '+' : '' }}{{ summary.avgReturn }}%
            </div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card shadow="never">
            <div style="font-size:13px;color:#909399">最大收益</div>
            <div style="font-size:28px;font-weight:bold;color:#67c23a">
              +{{ summary.maxReturn }}%
            </div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card shadow="never">
            <div style="font-size:13px;color:#909399">最大亏损</div>
            <div style="font-size:28px;font-weight:bold;color:#f56c6c">
              {{ summary.minReturn }}%
            </div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card shadow="never">
            <div style="font-size:13px;color:#909399">盈利次数</div>
            <div style="font-size:28px;font-weight:bold;color:#303133">{{ summary.wins }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 图表区 -->
      <el-row :gutter="16" style="margin-bottom: 20px">
        <el-col :span="14">
          <el-card shadow="never" header="季度胜率分布">
            <div id="quarterChart" style="height: 280px" />
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card shadow="never" header="出场原因分布">
            <div id="reasonChart" style="height: 280px" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 季度明细表 -->
      <el-card shadow="never" header="季度统计明细" style="margin-bottom: 20px">
        <el-table :data="summary.byQuarter" size="small">
          <el-table-column prop="quarter" label="季度" width="100" />
          <el-table-column prop="total" label="交易次数" width="100" />
          <el-table-column prop="wins" label="盈利次数" width="100" />
          <el-table-column label="胜率" width="100">
            <template #default="{ row }">
              <span :class="row.winRate >= 50 ? 'text-green' : 'text-red'">{{ row.winRate }}%</span>
            </template>
          </el-table-column>
          <el-table-column label="平均收益" width="120">
            <template #default="{ row }">
              <span :class="row.avgReturn >= 0 ? 'text-green' : 'text-red'">
                {{ row.avgReturn > 0 ? '+' : '' }}{{ row.avgReturn }}%
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 交易明细 -->
      <el-card shadow="never" header="交易明细">
        <el-row :gutter="12" style="margin-bottom: 12px">
          <el-col :span="5">
            <el-input v-model="filterStock" placeholder="股票代码过滤" clearable />
          </el-col>
          <el-col :span="5">
            <el-select v-model="filterReason" placeholder="出场原因" clearable style="width:100%">
              <el-option label="极值量出场" value="volume_top" />
              <el-option label="跌破锚位" value="stop_loss" />
              <el-option label="时间止损" value="time_stop" />
              <el-option label="数据截止" value="data_end" />
            </el-select>
          </el-col>
        </el-row>

        <el-table
          :data="trades"
          size="small"
          @sort-change="handleSortChange"
          default-sort="{ prop: 'return_pct', order: 'descending' }"
        >
          <el-table-column prop="stockCode" label="股票代码" width="90" />
          <el-table-column prop="signalDate" label="启动日" width="105" sortable="custom" />
          <el-table-column label="锚位" width="80">
            <template #default="{ row }">{{ row.anchorPrice?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="进场价" width="80">
            <template #default="{ row }">{{ row.entryPrice?.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="出场价" width="80">
            <template #default="{ row }">{{ row.exitPrice?.toFixed(2) ?? '-' }}</template>
          </el-table-column>
          <el-table-column prop="exitDate" label="出场日" width="105" />
          <el-table-column label="出场原因" width="100">
            <template #default="{ row }">
              <el-tag :type="reasonType[row.exitReason]" size="small">
                {{ reasonLabel[row.exitReason] || row.exitReason }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="holdDays" label="持仓天数" width="90" sortable="custom" />
          <el-table-column label="收益率" width="100" prop="return_pct" sortable="custom">
            <template #default="{ row }">
              <span :class="returnClass(row.returnPct)" style="font-weight:600">
                {{ row.returnPct !== null ? (row.returnPct > 0 ? '+' : '') + row.returnPct.toFixed(2) + '%' : '-' }}
              </span>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="tradePage"
          :page-size="tradePageSize"
          :total="tradeTotal"
          layout="total, prev, pager, next"
          style="margin-top: 16px; justify-content: flex-end"
        />
      </el-card>
    </template>

    <el-empty v-if="!loading && !summary" description="暂无回测数据，请先触发回测" />
  </div>
</template>

<style scoped>
.text-green { color: #67c23a; }
.text-red { color: #f56c6c; }
</style>
