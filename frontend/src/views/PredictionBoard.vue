<template>
  <div class="prediction-board">
    <h2>预测看板</h2>

    <!-- 胜率统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-card">
            <div class="stat-value">{{ stats.overall?.rate ?? '-' }}%</div>
            <div class="stat-label">总胜率</div>
            <div class="stat-sub">{{ stats.overall?.correct }}/{{ stats.overall?.total }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6" v-for="v in stats.byVersion" :key="v.version">
        <el-card shadow="never">
          <div class="stat-card">
            <div class="stat-value">{{ v.rate }}%</div>
            <div class="stat-label">{{ v.version }} 胜率</div>
            <div class="stat-sub">{{ v.correct }}/{{ v.total }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6" v-for="c in stats.byConfidence" :key="c.confidence">
        <el-card shadow="never">
          <div class="stat-card">
            <div class="stat-value">{{ c.rate }}%</div>
            <div class="stat-label">置信度「{{ c.confidence }}」</div>
            <div class="stat-sub">{{ c.correct }}/{{ c.total }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 胜率趋势折线图 -->
    <el-card shadow="never" class="chart-card">
      <template #header><span>胜率趋势（按日期）</span></template>
      <div ref="chartEl" style="height: 260px;" />
    </el-card>

    <!-- 预测记录表 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="table-header">
          <span>预测记录</span>
          <div class="filters">
            <el-input v-model="filter.stockCode" placeholder="股票代码" clearable style="width: 120px" @change="loadList" />
            <el-date-picker v-model="filter.startDate" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width: 140px" @change="loadList" />
            <el-date-picker v-model="filter.endDate" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 140px" @change="loadList" />
            <el-select v-model="filter.isCorrect" placeholder="对错" clearable style="width: 90px" @change="loadList">
              <el-option label="正确" :value="1" />
              <el-option label="错误" :value="0" />
            </el-select>
            <el-select v-model="filter.version" placeholder="版本" clearable style="width: 80px" @change="loadList">
              <el-option label="v1" value="v1" />
              <el-option label="v2" value="v2" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="listData" v-loading="listLoading" stripe size="small">
        <el-table-column prop="stockCode" label="代码" width="80">
          <template #default="{ row }">
            <el-link type="primary" @click="goDetail(row.stockCode)">{{ row.stockCode }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="stockName" label="名称" width="90" />
        <el-table-column prop="predictDate" label="预测日期" width="110" />
        <el-table-column prop="version" label="版本" width="60" />
        <el-table-column prop="confidence" label="置信" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.confidence" :type="confidenceType(row.confidence)" size="small">{{ row.confidence }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="对错" width="70">
          <template #default="{ row }">
            <span v-if="row.isCorrect === 1" class="color-up">✅</span>
            <span v-else-if="row.isCorrect === 0" class="color-down">❌</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="actualResult" label="实际结果" width="120" show-overflow-tooltip />
        <el-table-column label="实际涨跌" width="90">
          <template #default="{ row }">
            <span v-if="row.actualChangePct !== null" :class="row.actualChangePct >= 0 ? 'color-up' : 'color-down'">
              {{ row.actualChangePct > 0 ? '+' : '' }}{{ row.actualChangePct }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="prediction" label="综合预测" min-width="200" show-overflow-tooltip />
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadList"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { getBacktestStats, getBacktestList, getBacktestTrend } from '../api/backtest'

const router = useRouter()
const stats = ref({ overall: null, byVersion: [], byConfidence: [] })
const chartEl = ref(null)
let chartInstance = null

const listData = ref([])
const listLoading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20

const filter = ref({ stockCode: '', startDate: null, endDate: null, isCorrect: null, version: null })

function goDetail(code) {
  router.push(`/stocks/${code}`)
}

function confidenceType(c) {
  return { '高': 'danger', '中': 'warning', '低': 'info' }[c] || ''
}

async function loadStats() {
  const res = await getBacktestStats()
  stats.value = res
}

async function loadTrend() {
  const res = await getBacktestTrend()
  const items = res.items || []
  if (!chartEl.value) return
  chartInstance = echarts.init(chartEl.value)
  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: items.map(i => i.date) },
    yAxis: [
      { type: 'value', name: '胜率%', max: 100 },
      { type: 'value', name: '数量' },
    ],
    series: [
      {
        name: '胜率%',
        type: 'line',
        data: items.map(i => i.rate),
        smooth: true,
        itemStyle: { color: '#409eff' },
      },
      {
        name: '预测数',
        type: 'bar',
        yAxisIndex: 1,
        data: items.map(i => i.total),
        itemStyle: { color: '#e6f0ff' },
      },
    ],
  })
}

async function loadList() {
  listLoading.value = true
  try {
    const params = { page: page.value, pageSize }
    if (filter.value.stockCode) params.stockCode = filter.value.stockCode
    if (filter.value.startDate) params.startDate = filter.value.startDate
    if (filter.value.endDate) params.endDate = filter.value.endDate
    if (filter.value.isCorrect !== null && filter.value.isCorrect !== undefined) params.isCorrect = filter.value.isCorrect
    if (filter.value.version) params.version = filter.value.version

    const res = await getBacktestList(params)
    listData.value = res.items || []
    total.value = res.total || 0
  } finally {
    listLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadStats(), loadList()])
  await loadTrend()
})
</script>

<style scoped>
.prediction-board {
  padding: 20px;
}
.prediction-board h2 {
  margin: 0 0 16px;
  font-size: 18px;
}
.stats-row {
  margin-bottom: 16px;
}
.stat-card {
  text-align: center;
  padding: 8px 0;
}
.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}
.stat-label {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
}
.stat-sub {
  font-size: 12px;
  color: #999;
}
.chart-card, .table-card {
  margin-bottom: 16px;
}
.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filters {
  display: flex;
  gap: 8px;
}
.pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.color-up { color: #f56c6c; }
.color-down { color: #67c23a; }
</style>
