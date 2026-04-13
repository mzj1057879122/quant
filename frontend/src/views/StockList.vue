<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getStockList, syncStocks } from '../api/stock'
import { getWatchList, updateWatchList } from '../api/userConfig'

const router = useRouter()
const stockList = ref([])
const watchList = ref([])
const total = ref(0)
const keyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const syncLoading = ref(false)
const batchInput = ref('')
const batchDialogVisible = ref(false)
const selectedTier = ref('')

async function loadStocks() {
  loading.value = true
  try {
    const res = await getStockList({
      keyword: keyword.value || undefined,
      page: currentPage.value,
      pageSize: pageSize.value,
      tier: selectedTier.value || undefined,
    })
    stockList.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    // 静默
  } finally {
    loading.value = false
  }
}

async function loadWatchList() {
  try {
    const res = await getWatchList()
    watchList.value = res.stockCodes || []
  } catch (e) {
    // 静默
  }
}

function isWatched(stockCode) {
  return watchList.value.includes(stockCode)
}

async function toggleWatch(stockCode) {
  const newList = [...watchList.value]
  const idx = newList.indexOf(stockCode)
  if (idx >= 0) {
    newList.splice(idx, 1)
  } else {
    newList.push(stockCode)
  }
  try {
    await updateWatchList(newList)
    watchList.value = newList
    ElMessage.success(idx >= 0 ? '已取消关注' : '已添加关注')
  } catch (e) {
    // 静默
  }
}

async function handleSync() {
  syncLoading.value = true
  try {
    const res = await syncStocks()
    ElMessage.success(`同步完成，新增 ${res.newCount} 只股票`)
    await loadStocks()
  } catch (e) {
    // 静默
  } finally {
    syncLoading.value = false
  }
}

async function handleBatchImport() {
  const codes = batchInput.value
    .split(/[,\n\s]+/)
    .map(c => c.trim())
    .filter(c => c.length > 0)

  if (codes.length === 0) {
    ElMessage.warning('请输入股票代码')
    return
  }

  const newList = [...new Set([...watchList.value, ...codes])]
  try {
    await updateWatchList(newList)
    watchList.value = newList
    ElMessage.success(`已添加 ${codes.length} 只股票到关注列表`)
    batchDialogVisible.value = false
    batchInput.value = ''
  } catch (e) {
    // 静默
  }
}

function goToDetail(stockCode) {
  router.push(`/stocks/${stockCode}`)
}

function handleSearch() {
  currentPage.value = 1
  loadStocks()
}

function handlePageChange(page) {
  currentPage.value = page
  loadStocks()
}

function handleTierFilter(tier) {
  selectedTier.value = tier
  currentPage.value = 1
  loadStocks()
}

function tierTag(tier) {
  if (tier === 'A') return { label: '🔥A级', type: 'success' }
  if (tier === 'C') return { label: 'C级', type: 'info' }
  return { label: 'B级', type: 'primary' }
}

onMounted(() => {
  loadStocks()
  loadWatchList()
})
</script>

<template>
  <div>
    <!-- 操作栏 -->
    <el-card style="margin-bottom: 20px">
      <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap">
        <el-input
          v-model="keyword"
          placeholder="输入股票代码或名称搜索"
          style="width: 280px"
          clearable
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button @click="handleSearch">
              <el-icon><Search /></el-icon>
            </el-button>
          </template>
        </el-input>
        <el-button type="primary" @click="batchDialogVisible = true">
          <el-icon><Plus /></el-icon> 批量导入
        </el-button>
        <el-button :loading="syncLoading" @click="handleSync">
          <el-icon><Refresh /></el-icon> 同步股票列表
        </el-button>
        <span style="color: #909399; font-size: 13px; margin-left: auto">
          已关注 {{ watchList.length }} 只股票
        </span>
      </div>

      <!-- Tier 筛选按钮 -->
      <div style="margin-top: 12px; display: flex; gap: 8px; align-items: center">
        <span style="color: #606266; font-size: 13px">分级筛选：</span>
        <el-button
          :type="selectedTier === '' ? 'primary' : 'default'"
          size="small"
          @click="handleTierFilter('')"
        >全部</el-button>
        <el-button
          :type="selectedTier === 'A' ? 'success' : 'default'"
          size="small"
          @click="handleTierFilter('A')"
        >🔥 A级</el-button>
        <el-button
          :type="selectedTier === 'B' ? 'primary' : 'default'"
          size="small"
          @click="handleTierFilter('B')"
        >B级</el-button>
        <el-button
          :type="selectedTier === 'C' ? 'info' : 'default'"
          size="small"
          @click="handleTierFilter('C')"
        >C级</el-button>
      </div>
    </el-card>

    <!-- 股票表格 -->
    <el-card v-loading="loading">
      <el-table :data="stockList" style="width: 100%">
        <el-table-column prop="stockCode" label="代码" width="100" />
        <el-table-column prop="stockName" label="名称" width="140" />
        <el-table-column label="分级" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="tierTag(row.tier).type">
              {{ tierTag(row.tier).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="market" label="市场" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.market === 'sh' ? 'danger' : 'primary'">
              {{ row.market.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="industry" label="行业" />
        <el-table-column label="关注" width="100" align="center">
          <template #default="{ row }">
            <el-button
              :type="isWatched(row.stockCode) ? 'warning' : 'default'"
              size="small"
              @click="toggleWatch(row.stockCode)"
            >
              {{ isWatched(row.stockCode) ? '已关注' : '关注' }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button text type="primary" @click="goToDetail(row.stockCode)">详情</el-button>
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

    <!-- 批量导入弹窗 -->
    <el-dialog v-model="batchDialogVisible" title="批量导入股票" width="500px">
      <el-input
        v-model="batchInput"
        type="textarea"
        :rows="6"
        placeholder="输入股票代码，用逗号、空格或换行分隔&#10;例如：000001,600519,300750"
      />
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>
