<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDailyPrediction } from '../api/prediction'

const router = useRouter()
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

const sortedItems = computed(() => data.value.items || [])

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
  if (row.isCorrect === 1) return '✅'
  if (row.isCorrect === 0) return '❌'
  return '-'
}

function goDetail(stockCode) {
  router.push(`/stock/${stockCode}`)
}

onMounted(loadData)
</script>

<template>
  <div class="daily-prediction">
    <!-- 顶部一行：日期选择器 + 刷新 + 汇总数字 -->
    <div class="top-bar">
      <el-date-picker
        v-model="selectedDate"
        type="date"
        placeholder="日期（默认最近有数据）"
        value-format="YYYY-MM-DD"
        size="small"
        style="width: 180px"
        @change="loadData"
      />
      <el-button size="small" type="primary" :loading="loading" @click="loadData">刷新</el-button>
      <div class="summary-nums">
        <span class="num bullish">↑ 看多 {{ data.summary.bullish }}</span>
        <span class="num bearish">↓ 看空 {{ data.summary.bearish }}</span>
        <span class="num neutral">→ 中性 {{ data.summary.neutral }}</span>
      </div>
      <span v-if="data.date" class="data-date">{{ data.date }}</span>
    </div>

    <!-- 预测 vs 实际 表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="sortedItems" v-loading="loading" stripe>
        <el-table-column label="股票" width="140">
          <template #default="{ row }">
            <a class="stock-link" @click="goDetail(row.stockCode)">
              <div class="stock-name">{{ row.stockName }}</div>
              <div class="stock-code">{{ row.stockCode }}</div>
            </a>
          </template>
        </el-table-column>
        <el-table-column label="方向" width="90">
          <template #default="{ row }">
            <span :style="{ color: predictionColor(row.prediction), fontWeight: 700, fontSize: '15px' }">
              {{ predictionText(row.prediction) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.confidence" :type="confidenceType(row.confidence)" size="small">
              {{ row.confidence }}
            </el-tag>
            <span v-else class="no-data">-</span>
          </template>
        </el-table-column>
        <el-table-column label="实际涨跌" width="100" align="right">
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
}

.num {
  font-size: 14px;
  font-weight: 700;
}

.num.bullish { color: #67c23a; }
.num.bearish { color: #f56c6c; }
.num.neutral { color: #909399; }

.data-date {
  font-size: 12px;
  color: #909399;
  margin-left: 4px;
}

.table-card :deep(.el-card__body) {
  padding: 0;
}

.stock-link {
  cursor: pointer;
  text-decoration: none;
}

.stock-link:hover .stock-name {
  color: #409eff;
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
