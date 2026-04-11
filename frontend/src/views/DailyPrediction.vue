<script setup>
import { ref, computed, onMounted } from 'vue'
import { getDailyPrediction } from '../api/prediction'

const loading = ref(false)
const data = ref({ date: '', items: [], summary: { bullish: 0, bearish: 0, neutral: 0 } })

const selectedDate = ref('')
const filterPrediction = ref('全部')
const filterConfidence = ref('')

const predictionTabs = ['全部', '看多', '看空', '中性']
const confidenceOptions = ['高', '中', '低']

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (selectedDate.value) params.date = selectedDate.value
    const res = await getDailyPrediction(params)
    data.value = res.data
  } finally {
    loading.value = false
  }
}

const filteredItems = computed(() => {
  let items = data.value.items || []
  if (filterPrediction.value !== '全部') {
    items = items.filter(i => i.prediction === filterPrediction.value)
  }
  if (filterConfidence.value) {
    items = items.filter(i => i.confidence === filterConfidence.value)
  }
  return items
})

function predictionColor(pred) {
  if (pred === '看多') return '#67c23a'
  if (pred === '看空') return '#f56c6c'
  return '#909399'
}

function predictionText(pred) {
  if (pred === '看多') return '↑看多'
  if (pred === '看空') return '↓看空'
  return '→中性'
}

function confidenceType(conf) {
  if (conf === '高') return 'success'
  if (conf === '中') return 'warning'
  return 'info'
}

function changeClass(val) {
  if (val === null || val === undefined) return ''
  return val >= 0 ? 'positive' : 'negative'
}

function formatLatestDate(dateStr) {
  if (!dateStr) return '-'
  const parts = dateStr.split('-')
  if (parts.length < 3) return dateStr
  return `${parts[1]}/${parts[2]}`
}

const summaryDataNote = computed(() => {
  const d = data.value.items?.[0]?.latestDate
  if (!d) return ''
  return `数据截至 ${d} 收盘，每日16:30自动更新`
})

onMounted(loadData)
</script>

<template>
  <div class="daily-prediction">
    <!-- 汇总卡片 -->
    <el-row :gutter="16" class="summary-row">
      <el-col :span="8">
        <el-card shadow="never" class="summary-card bullish">
          <div class="card-inner">
            <div class="card-num">{{ data.summary.bullish }}</div>
            <div class="card-label">↑ 看多</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="summary-card bearish">
          <div class="card-inner">
            <div class="card-num">{{ data.summary.bearish }}</div>
            <div class="card-label">↓ 看空</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="summary-card neutral">
          <div class="card-inner">
            <div class="card-num">{{ data.summary.neutral }}</div>
            <div class="card-label">→ 中性</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <div v-if="summaryDataNote" class="summary-note">{{ summaryDataNote }}</div>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="filter-card">
      <div class="filter-bar">
        <el-radio-group v-model="filterPrediction" size="small">
          <el-radio-button v-for="t in predictionTabs" :key="t" :label="t" :value="t" />
        </el-radio-group>
        <el-select
          v-model="filterConfidence"
          placeholder="置信度"
          clearable
          size="small"
          style="width: 100px; margin-left: 12px"
        >
          <el-option v-for="c in confidenceOptions" :key="c" :label="c" :value="c" />
        </el-select>
        <el-date-picker
          v-model="selectedDate"
          type="date"
          placeholder="日期（默认今天）"
          value-format="YYYY-MM-DD"
          size="small"
          style="width: 160px; margin-left: 12px"
          @change="loadData"
        />
        <el-button size="small" type="primary" style="margin-left: 12px" :loading="loading" @click="loadData">
          刷新
        </el-button>
        <span class="date-label" v-if="data.date">{{ data.date }}</span>
      </div>
    </el-card>

    <!-- 股票列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="filteredItems" v-loading="loading" stripe>
        <el-table-column label="股票" width="140">
          <template #default="{ row }">
            <div class="stock-name">{{ row.stockName }}</div>
            <div class="stock-code">{{ row.stockCode }}</div>
          </template>
        </el-table-column>
        <el-table-column label="板块" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.sector" size="small" type="info">{{ row.sector }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="预测" width="90">
          <template #default="{ row }">
            <span :style="{ color: predictionColor(row.prediction), fontWeight: 600 }">
              {{ predictionText(row.prediction) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.confidence" :type="confidenceType(row.confidence)" size="small">
              {{ row.confidence }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="当前价" width="80" align="right">
          <template #default="{ row }">{{ row.latestClose != null ? row.latestClose.toFixed(2) : '-' }}</template>
        </el-table-column>
        <el-table-column label="锚位" width="80" align="right">
          <template #default="{ row }">{{ row.anchorPrice ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="距锚位%" width="90" align="right">
          <template #default="{ row }">
            <span
              v-if="row.changeFromAnchor !== null && row.changeFromAnchor !== undefined"
              :class="changeClass(row.changeFromAnchor)"
            >
              {{ row.changeFromAnchor >= 0 ? '+' : '' }}{{ Number(row.changeFromAnchor).toFixed(2) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="行情日期" width="80" align="center">
          <template #default="{ row }">
            <span class="date-cell">{{ formatLatestDate(row.latestDate) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="技术信号" min-width="200">
          <template #default="{ row }">
            <span class="signal-text">{{ row.technicalSignal || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.daily-prediction {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-card .card-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 0;
}

.card-num {
  font-size: 36px;
  font-weight: 700;
  line-height: 1.2;
}

.card-label {
  font-size: 14px;
  margin-top: 4px;
}

.bullish .card-num,
.bullish .card-label {
  color: #67c23a;
}

.bearish .card-num,
.bearish .card-label {
  color: #f56c6c;
}

.neutral .card-num,
.neutral .card-label {
  color: #909399;
}

.filter-card :deep(.el-card__body) {
  padding: 12px 16px;
}

.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.date-label {
  margin-left: auto;
  font-size: 13px;
  color: #909399;
}

.stock-name {
  font-weight: 500;
}

.stock-code {
  font-size: 12px;
  color: #909399;
}

.signal-text {
  font-size: 12px;
  color: #606266;
}

.positive {
  color: #67c23a;
  font-weight: 600;
}

.negative {
  color: #f56c6c;
  font-weight: 600;
}

.summary-note {
  font-size: 12px;
  color: #909399;
  text-align: center;
  margin-top: -8px;
}

.date-cell {
  font-size: 12px;
  color: #909399;
}
</style>
