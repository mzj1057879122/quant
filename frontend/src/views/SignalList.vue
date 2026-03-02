<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getSignalList, markSignalRead, markAllRead, detectSignals } from '../api/signal'
import { useSignalStore } from '../stores/signal'
import StatusBadge from '../components/StatusBadge.vue'

const router = useRouter()
const signalStore = useSignalStore()

const signals = ref([])
const total = ref(0)
const loading = ref(false)
const detectLoading = ref(false)

// 筛选条件
const filterCode = ref('')
const filterType = ref('')
const filterDateRange = ref([])
const currentPage = ref(1)
const pageSize = ref(20)

const signalTypes = [
  { value: '', label: '全部' },
  { value: 'approaching', label: '接近前高' },
  { value: 'breakout', label: '突破前高' },
  { value: 'failed', label: '突破失败' },
]

async function loadSignals() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      pageSize: pageSize.value,
    }
    if (filterCode.value) params.stockCode = filterCode.value
    if (filterType.value) params.signalType = filterType.value
    if (filterDateRange.value?.length === 2) {
      params.startDate = filterDateRange.value[0]
      params.endDate = filterDateRange.value[1]
    }

    const res = await getSignalList(params)
    signals.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    // 静默
  } finally {
    loading.value = false
  }
}

async function handleMarkRead(signal) {
  try {
    await markSignalRead(signal.id)
    signal.isRead = 1
    signalStore.fetchUnreadCount()
  } catch (e) {
    // 静默
  }
}

async function handleMarkAllRead() {
  try {
    const res = await markAllRead()
    ElMessage.success(`已全部标记为已读`)
    await loadSignals()
    signalStore.fetchUnreadCount()
  } catch (e) {
    // 静默
  }
}

async function handleDetect() {
  detectLoading.value = true
  try {
    const res = await detectSignals()
    ElMessage.success(`检测完成，生成 ${res.result?.signals || 0} 条信号`)
    await loadSignals()
    signalStore.fetchUnreadCount()
  } catch (e) {
    // 静默
  } finally {
    detectLoading.value = false
  }
}

function handleFilter() {
  currentPage.value = 1
  loadSignals()
}

function handlePageChange(page) {
  currentPage.value = page
  loadSignals()
}

function goToStock(stockCode) {
  router.push(`/stocks/${stockCode}`)
}

onMounted(loadSignals)
</script>

<template>
  <div>
    <!-- 筛选栏 -->
    <el-card style="margin-bottom: 20px">
      <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap">
        <el-input
          v-model="filterCode"
          placeholder="股票代码"
          style="width: 160px"
          clearable
          @clear="handleFilter"
        />
        <el-select v-model="filterType" placeholder="信号类型" style="width: 160px" @change="handleFilter">
          <el-option
            v-for="t in signalTypes"
            :key="t.value"
            :label="t.label"
            :value="t.value"
          />
        </el-select>
        <el-date-picker
          v-model="filterDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 280px"
          @change="handleFilter"
        />
        <el-button type="primary" @click="handleFilter">
          <el-icon><Search /></el-icon> 筛选
        </el-button>
        <div style="margin-left: auto; display: flex; gap: 8px">
          <el-button :loading="detectLoading" @click="handleDetect">
            <el-icon><Cpu /></el-icon> 执行检测
          </el-button>
          <el-button @click="handleMarkAllRead">
            <el-icon><Check /></el-icon> 全部已读
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 信号表格 -->
    <el-card v-loading="loading">
      <el-table :data="signals" style="width: 100%" :row-class-name="({ row }) => row.isRead === 0 ? 'unread-row' : ''">
        <el-table-column prop="signalType" label="类型" width="130">
          <template #default="{ row }">
            <StatusBadge :type="row.signalType" />
          </template>
        </el-table-column>
        <el-table-column prop="stockCode" label="代码" width="90">
          <template #default="{ row }">
            <el-button text type="primary" @click="goToStock(row.stockCode)">{{ row.stockCode }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="stockName" label="名称" width="100" />
        <el-table-column prop="signalDate" label="日期" width="110" />
        <el-table-column prop="previousHighPrice" label="前高价" width="90" />
        <el-table-column prop="triggerPrice" label="触发价" width="90" />
        <el-table-column prop="closePrice" label="收盘价" width="90" />
        <el-table-column prop="successRate" label="成功率" width="80">
          <template #default="{ row }">
            <span v-if="row.successRate != null">{{ row.successRate }}%</span>
            <span v-else style="color: #c0c4cc">--</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.isRead === 0"
              text
              type="primary"
              size="small"
              @click="handleMarkRead(row)"
            >
              已读
            </el-button>
            <span v-else style="color: #c0c4cc; font-size: 12px">已读</span>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; display: flex; justify-content: flex-end">
        <el-pagination
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style>
.unread-row {
  font-weight: 600;
  background-color: #ecf5ff !important;
}
</style>
