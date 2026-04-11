<template>
  <div class="watchlist-pool">
    <div class="page-header">
      <h2>自选股池</h2>
      <el-button type="primary" @click="showAddDialog = true">+ 添加</el-button>
    </div>

    <!-- 状态 Tab -->
    <el-tabs v-model="activeStatus" @tab-change="loadData">
      <el-tab-pane label="全部" name="" />
      <el-tab-pane label="关注中" name="watching" />
      <el-tab-pane label="持有" name="holding" />
      <el-tab-pane label="已出局" name="exited" />
    </el-tabs>

    <!-- 股票表格 -->
    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="stockCode" label="代码" width="90">
        <template #default="{ row }">
          <el-link type="primary" @click="goDetail(row.stockCode)">{{ row.stockCode }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="stockName" label="名称" width="100" />
      <el-table-column prop="sector" label="板块" width="120" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="anchorPrice" label="锚位" width="80">
        <template #default="{ row }">{{ row.anchorPrice ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="anchorDate" label="锚位日期" width="110" />
      <el-table-column prop="latestPrice" label="当前价" width="80">
        <template #default="{ row }">{{ row.latestPrice ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="距锚%" width="90">
        <template #default="{ row }">
          <span v-if="row.anchorDistPct !== null" :class="row.anchorDistPct >= 0 ? 'color-up' : 'color-down'">
            {{ row.anchorDistPct > 0 ? '+' : '' }}{{ row.anchorDistPct }}%
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="置信度" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.confidence" :type="confidenceType(row.confidence)" size="small">{{ row.confidence }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="addReason" label="加入原因" min-width="150" show-overflow-tooltip />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确认移除？" @confirm="removeItem(row.stockCode)">
            <template #reference>
              <el-button size="small" type="danger">移除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加对话框 -->
    <el-dialog v-model="showAddDialog" title="添加自选股" width="480px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="股票代码" required>
          <el-input v-model="addForm.stockCode" placeholder="如 603687" />
        </el-form-item>
        <el-form-item label="股票名称" required>
          <el-input v-model="addForm.stockName" placeholder="如 大胜达" />
        </el-form-item>
        <el-form-item label="板块">
          <el-input v-model="addForm.sector" placeholder="如 光通信" />
        </el-form-item>
        <el-form-item label="加入原因">
          <el-input v-model="addForm.addReason" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="addForm.status">
            <el-option label="关注中" value="watching" />
            <el-option label="持有" value="holding" />
            <el-option label="已出局" value="exited" />
          </el-select>
        </el-form-item>
        <el-form-item label="锚位价格">
          <el-input v-model.number="addForm.anchorPrice" type="number" />
        </el-form-item>
        <el-form-item label="锚位日期">
          <el-date-picker v-model="addForm.anchorDate" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="置信度">
          <el-select v-model="addForm.confidence">
            <el-option label="高" value="高" />
            <el-option label="中" value="中" />
            <el-option label="低" value="低" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitAdd">确认添加</el-button>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑自选股" width="480px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="板块">
          <el-input v-model="editForm.sector" />
        </el-form-item>
        <el-form-item label="加入原因">
          <el-input v-model="editForm.addReason" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status">
            <el-option label="关注中" value="watching" />
            <el-option label="持有" value="holding" />
            <el-option label="已出局" value="exited" />
          </el-select>
        </el-form-item>
        <el-form-item label="锚位价格">
          <el-input v-model.number="editForm.anchorPrice" type="number" />
        </el-form-item>
        <el-form-item label="锚位日期">
          <el-date-picker v-model="editForm.anchorDate" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="置信度">
          <el-select v-model="editForm.confidence">
            <el-option label="高" value="高" />
            <el-option label="中" value="中" />
            <el-option label="低" value="低" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getWatchlistItems, addWatchlistItem, updateWatchlistItem, deleteWatchlistItem } from '../api/watchlist'

const router = useRouter()
const items = ref([])
const loading = ref(false)
const activeStatus = ref('')

const showAddDialog = ref(false)
const showEditDialog = ref(false)
const editCode = ref('')

const addForm = ref({ stockCode: '', stockName: '', sector: '', addReason: '', status: 'watching', anchorPrice: null, anchorDate: null, confidence: '' })
const editForm = ref({ sector: '', addReason: '', status: 'watching', anchorPrice: null, anchorDate: null, confidence: '' })

async function loadData() {
  loading.value = true
  try {
    const res = await getWatchlistItems(activeStatus.value ? { status: activeStatus.value } : {})
    items.value = res.items || []
  } finally {
    loading.value = false
  }
}

function goDetail(code) {
  router.push(`/stocks/${code}`)
}

function statusLabel(s) {
  return { watching: '关注中', holding: '持有', exited: '已出局' }[s] || s
}

function statusType(s) {
  return { watching: 'primary', holding: 'success', exited: 'info' }[s] || ''
}

function confidenceType(c) {
  return { '高': 'danger', '中': 'warning', '低': 'info' }[c] || ''
}

async function submitAdd() {
  if (!addForm.value.stockCode || !addForm.value.stockName) {
    ElMessage.warning('股票代码和名称不能为空')
    return
  }
  await addWatchlistItem(addForm.value)
  ElMessage.success('添加成功')
  showAddDialog.value = false
  addForm.value = { stockCode: '', stockName: '', sector: '', addReason: '', status: 'watching', anchorPrice: null, anchorDate: null, confidence: '' }
  loadData()
}

function openEdit(row) {
  editCode.value = row.stockCode
  editForm.value = {
    sector: row.sector,
    addReason: row.addReason,
    status: row.status,
    anchorPrice: row.anchorPrice,
    anchorDate: row.anchorDate,
    confidence: row.confidence,
  }
  showEditDialog.value = true
}

async function submitEdit() {
  await updateWatchlistItem(editCode.value, editForm.value)
  ElMessage.success('更新成功')
  showEditDialog.value = false
  loadData()
}

async function removeItem(code) {
  await deleteWatchlistItem(code)
  ElMessage.success('已移除')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.watchlist-pool {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
}
.color-up { color: #f56c6c; }
.color-down { color: #67c23a; }
</style>
