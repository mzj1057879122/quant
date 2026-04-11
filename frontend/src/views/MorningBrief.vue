<template>
  <div class="morning-brief">
    <div class="page-header">
      <h2>盘前纪要</h2>
      <div class="header-right">
        <el-select v-model="source" placeholder="来源" clearable style="width: 120px" @change="loadLatest">
          <el-option label="briefA（详版）" value="briefA" />
          <el-option label="briefB（快版）" value="briefB" />
        </el-select>
        <el-date-picker v-model="selectedDate" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width: 140px" @change="loadByDate" />
      </div>
    </div>

    <!-- 最新纪要 -->
    <div v-if="currentBrief">
      <el-card shadow="never" class="brief-card">
        <template #header>
          <div class="brief-header">
            <span class="brief-date">{{ currentBrief.briefDate }}</span>
            <el-tag size="small">{{ currentBrief.source }}</el-tag>
          </div>
        </template>
        <pre class="brief-content">{{ currentBrief.rawContent }}</pre>
      </el-card>
    </div>

    <div v-if="multipleItems.length > 1">
      <el-card v-for="b in multipleItems" :key="b.id" shadow="never" class="brief-card">
        <template #header>
          <div class="brief-header">
            <span class="brief-date">{{ b.briefDate }}</span>
            <el-tag size="small">{{ b.source }}</el-tag>
          </div>
        </template>
        <pre class="brief-content">{{ b.rawContent }}</pre>
      </el-card>
    </div>

    <el-empty v-if="!currentBrief && multipleItems.length === 0" description="暂无数据" />

    <!-- 历史列表 -->
    <el-card shadow="never" class="list-card">
      <template #header><span>历史列表</span></template>
      <el-table :data="listData" v-loading="loading" size="small" @row-click="selectBrief">
        <el-table-column prop="briefDate" label="日期" width="120" />
        <el-table-column prop="source" label="来源" width="100" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" @click.stop="viewDetail(row)">查看</el-button>
          </template>
        </el-table-column>
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
import { getLatestBrief, getBriefList, getBriefByDate } from '../api/brief'

const source = ref('')
const selectedDate = ref(null)
const currentBrief = ref(null)
const multipleItems = ref([])

const listData = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20

async function loadLatest() {
  multipleItems.value = []
  const params = source.value ? { source: source.value } : {}
  const res = await getLatestBrief(params)
  currentBrief.value = res.brief
}

async function loadByDate() {
  if (!selectedDate.value) return
  currentBrief.value = null
  const res = await getBriefByDate(selectedDate.value)
  const items = res.items || []
  if (items.length === 1) {
    currentBrief.value = items[0]
    multipleItems.value = []
  } else {
    multipleItems.value = items
  }
}

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, pageSize }
    if (source.value) params.source = source.value
    const res = await getBriefList(params)
    listData.value = res.items || []
    total.value = res.total || 0
  } finally {
    loading.value = false
  }
}

async function viewDetail(row) {
  selectedDate.value = row.briefDate
  await loadByDate()
  window.scrollTo(0, 0)
}

function selectBrief(row) {
  viewDetail(row)
}

onMounted(async () => {
  await Promise.all([loadLatest(), loadList()])
})
</script>

<style scoped>
.morning-brief {
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
.header-right {
  display: flex;
  gap: 8px;
}
.brief-card {
  margin-bottom: 16px;
}
.brief-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.brief-date {
  font-weight: bold;
}
.brief-content {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  line-height: 1.6;
  max-height: 600px;
  overflow-y: auto;
  font-family: inherit;
  margin: 0;
}
.list-card {
  margin-top: 16px;
}
.pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
