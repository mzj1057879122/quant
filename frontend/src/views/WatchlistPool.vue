<template>
  <div class="watchlist-pool">
    <!-- 顶部栏 -->
    <div class="page-header">
      <div class="filter-btns">
        <el-button
          v-for="opt in STATUS_OPTS"
          :key="opt.value"
          :type="activeStatus === opt.value ? 'primary' : ''"
          size="small"
          @click="setStatus(opt.value)"
        >{{ opt.label }}</el-button>
      </div>
      <el-button type="primary" size="small" @click="showAddDialog = true">+ 添加</el-button>
    </div>

    <!-- 按板块分组 -->
    <div v-if="!loading" class="sector-list">
      <div
        v-for="group in groupedSectors"
        :key="group.sector"
        class="sector-section"
        :style="{ background: group.color || '#f9f9f9' }"
      >
        <!-- 板块标题行 -->
        <div class="sector-header">
          <template v-if="editingSector === group.sector">
            <el-input
              v-model="sectorEditValue"
              size="small"
              style="width: 120px"
              @keyup.enter="saveSectorName(group.sector)"
              @blur="saveSectorName(group.sector)"
              autofocus
            />
          </template>
          <template v-else>
            <span class="sector-name" @click="startEditSector(group.sector)">
              {{ group.sector || '未分类' }}
            </span>
          </template>
          <span class="sector-count">{{ group.items.length }}只</span>
          <!-- 颜色圆点 -->
          <div class="color-dot-wrap">
            <span
              class="color-dot"
              :style="{ background: group.color || '#ddd' }"
              @click="openColorPicker(group.sector)"
            />
            <!-- 颜色选择器 -->
            <div v-if="colorPickerSector === group.sector" class="color-picker-popup" @click.stop>
              <span
                v-for="c in PRESET_COLORS"
                :key="c.value"
                class="preset-dot"
                :title="c.label"
                :style="{ background: c.value, outline: group.color === c.value ? '2px solid #409eff' : 'none' }"
                @click="pickColor(group.sector, c.value)"
              />
            </div>
          </div>
        </div>

        <!-- 股票卡片拖拽列表 -->
        <draggable
          v-model="group.items"
          item-key="stockCode"
          class="stock-cards"
          handle=".drag-handle"
          ghost-class="drag-ghost"
          @end="onDragEnd(group)"
        >
          <template #item="{ element }">
            <div class="stock-card">
              <span class="drag-handle">⠿</span>
              <div class="card-body">
                <div class="card-row1">
                  <el-link type="primary" class="code" @click="goDetail(element.stockCode)">
                    {{ element.stockCode }}
                  </el-link>
                  <span class="name">{{ element.stockName }}</span>
                </div>
                <div class="card-row2">
                  <span
                    v-if="predictionMap[element.stockCode]"
                    :class="predClass(predictionMap[element.stockCode].prediction)"
                  >
                    {{ predArrow(predictionMap[element.stockCode].prediction) }}
                  </span>
                  <span v-else class="pred-neutral">→</span>
                  <span
                    v-if="predictionMap[element.stockCode]?.actualChangePct !== null && predictionMap[element.stockCode]?.actualChangePct !== undefined"
                    :class="predictionMap[element.stockCode].actualChangePct >= 0 ? 'color-up' : 'color-down'"
                    style="margin-left: 4px; font-size: 12px"
                  >
                    {{ predictionMap[element.stockCode].actualChangePct > 0 ? '+' : '' }}{{ predictionMap[element.stockCode].actualChangePct?.toFixed(2) }}%
                  </span>
                </div>
                <div class="card-row3">
                  <el-tag :type="statusType(element.status)" size="small">{{ statusLabel(element.status) }}</el-tag>
                </div>
              </div>
              <div class="card-actions">
                <el-button size="small" link @click="openEdit(element)">编辑</el-button>
                <el-popconfirm title="确认移除？" @confirm="removeItem(element.stockCode)">
                  <template #reference>
                    <el-button size="small" link type="danger">移除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
          </template>
        </draggable>
      </div>

      <div v-if="groupedSectors.length === 0" class="empty-tip">暂无自选股</div>
    </div>
    <div v-else class="loading-wrap" v-loading="loading" style="height: 200px" />

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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import draggable from 'vuedraggable'
import {
  getWatchlistItems,
  addWatchlistItem,
  updateWatchlistItem,
  updateWatchlistSector,
  reorderWatchlist,
  getSectorColors,
  saveSectorColor,
  deleteWatchlistItem,
} from '../api/watchlist'
import { getDailyPrediction } from '../api/prediction'

const router = useRouter()

const STATUS_OPTS = [
  { label: '全部', value: '' },
  { label: '关注中', value: 'watching' },
  { label: '持有', value: 'holding' },
]

const PRESET_COLORS = [
  { label: '天蓝', value: '#e8f4fd' },
  { label: '浅红', value: '#fde8e8' },
  { label: '浅绿', value: '#e8fde8' },
  { label: '浅橙', value: '#fdf3e8' },
  { label: '浅紫', value: '#f0e8fd' },
  { label: '浅黄', value: '#fdfae8' },
  { label: '浅青', value: '#e8fdf8' },
  { label: '浅粉', value: '#fde8f4' },
  { label: '浅灰', value: '#f4f4f4' },
  { label: '浅棕', value: '#f9f0e8' },
  { label: '浅靛', value: '#e8eafd' },
  { label: '浅碧', value: '#e8f9fd' },
]

const loading = ref(false)
const activeStatus = ref('')
const items = ref([])
const sectorColors = ref({})  // sector -> color
const predictionMap = ref({}) // stockCode -> { prediction, actualChangePct }

// 板块名编辑
const editingSector = ref(null)
const sectorEditValue = ref('')

// 颜色选择器
const colorPickerSector = ref(null)

// 对话框
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const editCode = ref('')
const addForm = ref({ stockCode: '', stockName: '', sector: '', addReason: '', status: 'watching', anchorPrice: null, anchorDate: null, confidence: '' })
const editForm = ref({ sector: '', addReason: '', status: 'watching', anchorPrice: null, anchorDate: null, confidence: '' })

// 按板块分组（computed 只用于初次分组，拖拽用可变的 groupedSectors）
const groupedSectors = ref([])

function buildGroups(rawItems) {
  const map = new Map()
  for (const item of rawItems) {
    const key = item.sector || ''
    if (!map.has(key)) {
      map.set(key, { sector: key, items: [], color: sectorColors.value[key] || '' })
    }
    map.get(key).items.push(item)
  }
  return Array.from(map.values())
}

function setStatus(val) {
  activeStatus.value = val
  loadData()
}

async function loadData() {
  loading.value = true
  try {
    const [watchRes, predRes, colorRes] = await Promise.all([
      getWatchlistItems(activeStatus.value ? { status: activeStatus.value } : {}),
      getDailyPrediction({}),
      getSectorColors(),
    ])
    sectorColors.value = colorRes.colors || {}
    items.value = watchRes.items || []

    // 构建预测 map
    const pm = {}
    for (const p of (predRes.items || [])) {
      pm[p.stockCode] = { prediction: p.prediction, actualChangePct: p.actualChangePct }
    }
    predictionMap.value = pm

    groupedSectors.value = buildGroups(items.value)
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

function predArrow(pred) {
  if (pred === '看多') return '↑'
  if (pred === '看空') return '↓'
  return '→'
}

function predClass(pred) {
  if (pred === '看多') return 'pred-up'
  if (pred === '看空') return 'pred-down'
  return 'pred-neutral'
}

// 板块名编辑
function startEditSector(sector) {
  editingSector.value = sector
  sectorEditValue.value = sector
}

async function saveSectorName(oldSector) {
  const newName = sectorEditValue.value.trim()
  editingSector.value = null
  if (!newName || newName === oldSector) return

  // 批量更新该板块下所有股票的 sector
  const group = groupedSectors.value.find(g => g.sector === oldSector)
  if (!group) return
  try {
    await Promise.all(group.items.map(item => updateWatchlistSector(item.stockCode, newName)))
    ElMessage.success('板块名已更新')
    await loadData()
  } catch {
    ElMessage.error('更新失败')
  }
}

// 颜色选择
function openColorPicker(sector) {
  colorPickerSector.value = colorPickerSector.value === sector ? null : sector
}

async function pickColor(sector, color) {
  colorPickerSector.value = null
  try {
    await saveSectorColor(sector, color)
    sectorColors.value[sector] = color
    const group = groupedSectors.value.find(g => g.sector === sector)
    if (group) group.color = color
  } catch {
    ElMessage.error('保存颜色失败')
  }
}

// 拖拽结束
async function onDragEnd(group) {
  // 重新编号：只更新当前板块内的 sortOrder
  const payload = group.items.map((item, idx) => ({
    stockCode: item.stockCode,
    sortOrder: idx,
  }))
  try {
    await reorderWatchlist(payload)
  } catch {
    ElMessage.error('排序保存失败')
  }
}

// 添加
async function submitAdd() {
  if (!addForm.value.stockCode || !addForm.value.stockName) {
    ElMessage.warning('股票代码和名称不能为空')
    return
  }
  try {
    await addWatchlistItem(addForm.value)
    ElMessage.success('添加成功')
    showAddDialog.value = false
    addForm.value = { stockCode: '', stockName: '', sector: '', addReason: '', status: 'watching', anchorPrice: null, anchorDate: null, confidence: '' }
    loadData()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '添加失败')
  }
}

// 编辑
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

// 移除
async function removeItem(code) {
  await deleteWatchlistItem(code)
  ElMessage.success('已移除')
  loadData()
}

// 关闭颜色选择器（点击其他区域）
function onDocClick() {
  colorPickerSector.value = null
}

onMounted(() => {
  loadData()
  document.addEventListener('click', onDocClick)
})
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

.filter-btns {
  display: flex;
  gap: 6px;
}

.sector-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sector-section {
  border-radius: 10px;
  padding: 12px 16px 16px;
  border: 1px solid rgba(0,0,0,0.06);
}

.sector-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.sector-name {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  cursor: pointer;
  border-bottom: 1px dashed #aaa;
}

.sector-name:hover {
  color: #409eff;
}

.sector-count {
  font-size: 12px;
  color: #888;
}

.color-dot-wrap {
  position: relative;
}

.color-dot {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid rgba(0,0,0,0.15);
  cursor: pointer;
  vertical-align: middle;
}

.color-picker-popup {
  position: absolute;
  top: 20px;
  left: 0;
  z-index: 100;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  width: 168px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.12);
}

.preset-dot {
  display: inline-block;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1px solid rgba(0,0,0,0.12);
  cursor: pointer;
  outline-offset: 2px;
}

.preset-dot:hover {
  transform: scale(1.15);
}

.stock-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stock-card {
  background: #fff;
  border-radius: 8px;
  border: 1px solid rgba(0,0,0,0.08);
  padding: 8px 10px 8px 6px;
  width: 180px;
  display: flex;
  align-items: flex-start;
  gap: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  position: relative;
  transition: box-shadow 0.15s;
}

.stock-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}

.stock-card:hover .drag-handle {
  opacity: 1;
}

.drag-handle {
  cursor: grab;
  color: #bbb;
  font-size: 16px;
  line-height: 1;
  opacity: 0;
  transition: opacity 0.15s;
  padding-top: 2px;
  user-select: none;
}

.card-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.card-row1 {
  display: flex;
  align-items: center;
  gap: 5px;
}

.code {
  font-size: 13px;
  font-weight: 600;
}

.name {
  font-size: 12px;
  color: #555;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  max-width: 80px;
}

.card-row2 {
  display: flex;
  align-items: center;
  font-size: 14px;
}

.card-row3 {
  display: flex;
}

.card-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex-shrink: 0;
}

.drag-ghost {
  opacity: 0.4;
  background: #c8ebfb;
}

.color-up { color: #f56c6c; }
.color-down { color: #67c23a; }

.pred-up { color: #f56c6c; font-size: 15px; font-weight: bold; }
.pred-down { color: #67c23a; font-size: 15px; font-weight: bold; }
.pred-neutral { color: #aaa; font-size: 15px; }

.empty-tip {
  text-align: center;
  color: #aaa;
  padding: 40px 0;
}
</style>
