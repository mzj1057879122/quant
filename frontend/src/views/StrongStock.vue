<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getStrongStockList } from '../api/strong'

const stocks = ref([])
const total = ref(0)
const loading = ref(false)
const dataUpdatedAt = ref('')
const fromCache = ref(false)

// 筛选条件
const maxDays = ref(5)
const minGainPct = ref(15)
const maxGainPct = ref(100)

async function loadStocks(forceRefresh = false) {
  loading.value = true
  try {
    const res = await getStrongStockList({
      maxDays: maxDays.value,
      minGainPct: minGainPct.value,
      maxGainPct: maxGainPct.value,
      forceRefresh,
    })
    stocks.value = res.items || []
    total.value = res.total || 0
    fromCache.value = res.fromCache || false
    dataUpdatedAt.value = res.dataUpdatedAt ? new Date(res.dataUpdatedAt).toLocaleString('zh-CN') : ''
  } catch (e) {
    ElMessage.error('获取强势股数据失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function handleQuery() {
  loadStocks(false)
}

function handleRefresh() {
  loadStocks(true)
}

onMounted(() => {
  loadStocks()
})
</script>

<template>
  <div>
    <!-- 筛选栏 -->
    <el-card style="margin-bottom: 16px">
      <el-form inline>
        <el-form-item label="最多连涨天数">
          <el-input-number
            v-model="maxDays"
            :min="1"
            :max="20"
            controls-position="right"
            style="width: 120px"
          />
        </el-form-item>
        <el-form-item label="最低涨幅%">
          <el-input-number
            v-model="minGainPct"
            :min="1"
            :max="200"
            :precision="1"
            controls-position="right"
            style="width: 120px"
          />
        </el-form-item>
        <el-form-item label="最大涨幅%">
          <el-input-number
            v-model="maxGainPct"
            :min="1"
            :max="200"
            :precision="1"
            controls-position="right"
            style="width: 120px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleQuery">查询</el-button>
          <el-button :loading="loading" @click="handleRefresh" style="margin-left: 8px">刷新数据</el-button>
        </el-form-item>
        <el-form-item v-if="dataUpdatedAt" style="margin-left: auto">
          <span style="color: #909399; font-size: 13px">
            数据时间：{{ dataUpdatedAt }}
            <el-tag v-if="fromCache" size="small" type="info" style="margin-left: 6px">缓存</el-tag>
            <el-tag v-else size="small" type="success" style="margin-left: 6px">最新</el-tag>
          </span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格 -->
    <el-card>
      <div style="margin-bottom: 12px; color: #606266; font-size: 14px">
        共 <strong>{{ total }}</strong> 只强势股
        <span v-if="loading" style="margin-left: 8px; color: #409eff">（数据加载中，约需3-10秒...）</span>
      </div>
      <el-table
        v-loading="loading"
        :data="stocks"
        border
        stripe
        style="width: 100%"
        element-loading-text="正在拉取数据，请稍候..."
      >
        <el-table-column type="index" label="排名" width="60" align="center" />
        <el-table-column prop="stockCode" label="股票代码" width="100" align="center" />
        <el-table-column prop="stockName" label="股票简称" width="120" />
        <el-table-column prop="closePrice" label="收盘价" width="90" align="right">
          <template #default="{ row }">{{ row.closePrice.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="daysUp" label="连涨天数" width="90" align="center">
          <template #default="{ row }">{{ row.daysUp }} 天</template>
        </el-table-column>
        <el-table-column prop="gainPct" label="累计涨幅%" width="110" align="right">
          <template #default="{ row }">
            <span style="color: #f56c6c; font-weight: bold">+{{ row.gainPct.toFixed(2) }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="turnoverPct" label="累计换手率%" width="120" align="right">
          <template #default="{ row }">{{ row.turnoverPct.toFixed(2) }}%</template>
        </el-table-column>
        <el-table-column prop="industry" label="所属行业" />
      </el-table>
    </el-card>
  </div>
</template>
