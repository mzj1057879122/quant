<script setup>
import { ref, computed, onMounted } from 'vue'
import { getDailyPrediction } from '../api/prediction'

const loading = ref(false)
const data = ref({ date: '', items: [], summary: { bullish: 0, bearish: 0, neutral: 0 } })
const selectedDate = ref('')

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (selectedDate.value) params.date = selectedDate.value
    const res = await getDailyPrediction(params)
    data.value = res.data || { date: '', items: [], summary: { bullish: 0, bearish: 0, neutral: 0 } }
  } finally {
    loading.value = false
  }
}

const CONFIDENCE_ORDER = { '高': 0, '中': 1, '低': 2 }
const PREDICTION_ORDER = { '看多': 0, '看空': 1, '中性': 2 }

const sortedItems = computed(() => {
  const items = [...(data.value.items || [])]
  items.sort((a, b) => {
    const predDiff = (PREDICTION_ORDER[a.prediction] ?? 9) - (PREDICTION_ORDER[b.prediction] ?? 9)
    if (predDiff !== 0) return predDiff
    return (CONFIDENCE_ORDER[a.confidence] ?? 9) - (CONFIDENCE_ORDER[b.confidence] ?? 9)
  })
  return items
})

function predictionColor(pred) {
  if (pred === '看多') return '#67c23a'
  if (pred === '看空') return '#f56c6c'
  return '#909399'
}

function predictionText(pred) {
  if (pred === '看多') return '↑ 看多'
  if (pred === '看空') return '↓ 看空'
  return '→ 中性'
}

function confidenceType(conf) {
  if (conf === '高') return 'success'
  if (conf === '中') return 'warning'
  return 'info'
}

function verifyIcon(row) {
  const val = row.actualChangePct
  if (val === null || val === undefined) return '-'
  if (row.prediction === '看多') return val > 0 ? '✅' : '❌'
  if (row.prediction === '看空') return val < 0 ? '✅' : '❌'
  return '-'
}

onMounted(loadData)
</script>

<template>
  <div class="daily-prediction">
    <!-- 顶部一行：日期选择器 + 汇总数字 -->
    <div class="top-bar">
      <el-date-picker
        v-model="selectedDate"
        type="date"
        placeholder="日期（默认今天）"
        value-format="YYYY-MM-DD"
        size="small"
        style="width: 160px"
        @change="loadData"
      />
      <el-button size="small" type="primary" :loading="loading" @click="loadData">刷新</el-button>
      <div class="summary-nums">
        <span class="num bullish">↑ 看多 {{ data.summary.bullish }} 只</span>
        <span class="num bearish">↓ 看空 {{ data.summary.bearish }} 只</span>
        <span class="num neutral">→ 中性 {{ data.summary.neutral }} 只</span>
      </div>
    </div>

    <!-- 预测 vs 实际 表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="sortedItems" v-loading="loading" stripe>
        <el-table-column label="股票" width="140">
          <template #default="{ row }">
            <div class="stock-name">{{ row.stockName }}</div>
            <div class="stock-code">{{ row.stockCode }}</div>
          </template>
        </el-table-column>
        <el-table-column label="预测" width="90">
          <template #default="{ row }">
            <span :style="{ color: predictionColor(row.prediction), fontWeight: 600 }">
              {{ predictionText(row.prediction) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.confidence" :type="confidenceType(row.confidence)" size="small">
              {{ row.confidence }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="实际涨跌幅" width="110" align="right">
          <template #default="{ row }">
            <span
              v-if="row.actualChangePct !== null && row.actualChangePct !== undefined"
              :class="row.actualChangePct >= 0 ? 'positive' : 'negative'"
            >
              {{ row.actualChangePct >= 0 ? '+' : '' }}{{ Number(row.actualChangePct).toFixed(2) }}%
            </span>
            <span v-else class="no-data">-</span>
          </template>
        </el-table-column>
        <el-table-column label="对错" width="60" align="center">
          <template #default="{ row }">
            <span class="verify-icon">{{ verifyIcon(row) }}</span>
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

.top-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.summary-nums {
  display: flex;
  gap: 16px;
  margin-left: 8px;
}

.num {
  font-size: 13px;
  font-weight: 600;
}

.num.bullish { color: #67c23a; }
.num.bearish { color: #f56c6c; }
.num.neutral { color: #909399; }

.table-card :deep(.el-card__body) {
  padding: 0;
}

.stock-name {
  font-weight: 500;
}

.stock-code {
  font-size: 12px;
  color: #909399;
}

.positive {
  color: #67c23a;
  font-weight: 600;
}

.negative {
  color: #f56c6c;
  font-weight: 600;
}

.no-data {
  color: #c0c4cc;
}

.verify-icon {
  font-size: 15px;
}
</style>
