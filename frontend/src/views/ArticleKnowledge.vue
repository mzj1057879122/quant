<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { submitArticle, submitFromUrl, getArticleStatus, getArticleList, retryArticle, deleteArticle, batchUpdateDate, triggerDailySummary, getDailySummary } from '../api/article'

// 提交
const submitMode = ref('url')
const articleUrl = ref('')
const urlSubmitting = ref(false)
const title = ref('')
const author = ref('')
const source = ref('')
const articleDate = ref(new Date().toISOString().slice(0, 10))
const content = ref('')
const submitting = ref(false)

// URL提取自定义日期
const urlCustomDate = ref(null)
const urlDateConfirmed = ref(false)

// 轮询
const currentArticle = ref(null)
let pollTimer = null
let pollCount = 0

// 文章列表
const articles = ref([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const selectedArticles = ref([])

// 批量修改日期
const batchDateDialogVisible = ref(false)
const batchNewDate = ref(new Date().toISOString().slice(0, 10))

// 每日汇总
const summaryDate = ref(new Date().toISOString().slice(0, 10))
const dailySummary = ref(null)
const summaryLoading = ref(false)
let summaryPollTimer = null

// 当日已完成文章数
const completedCount = computed(() => {
  return articles.value.filter(a => a.status === 'completed' && a.articleDate === summaryDate.value).length
})

// ==================== URL自定义日期 ====================

function handleUrlDateConfirm() {
  if (!urlCustomDate.value) {
    ElMessage.warning('请选择日期')
    return
  }
  urlDateConfirmed.value = true
  ElMessage.success(`已锁定日期：${urlCustomDate.value}，后续提取均使用此日期`)
}

function handleUrlDateCancel() {
  urlCustomDate.value = null
  urlDateConfirmed.value = false
}

// ==================== 提交 ====================

async function handleUrlSubmit() {
  if (!articleUrl.value?.trim()) {
    ElMessage.warning('请输入文章链接')
    return
  }
  urlSubmitting.value = true
  try {
    const customDate = urlDateConfirmed.value ? urlCustomDate.value : null
    const res = await submitFromUrl(articleUrl.value.trim(), customDate)
    currentArticle.value = res
    ElMessage.success(`已提取「${res.title || '文章'}」，正在分析...`)
    articleUrl.value = ''
    startPolling(res.id)
    loadArticles()
  } catch (e) { /* 拦截器处理 */ } finally {
    urlSubmitting.value = false
  }
}

async function handleSubmit() {
  if (!content.value || content.value.trim().length < 10) {
    ElMessage.warning('请输入至少10个字符的文章内容')
    return
  }
  submitting.value = true
  try {
    const res = await submitArticle({
      title: title.value || null,
      author: author.value || null,
      content: content.value,
      source: source.value || null,
      articleDate: articleDate.value,
    })
    currentArticle.value = res
    ElMessage.success('文章已提交，正在分析...')
    title.value = ''
    author.value = ''
    source.value = ''
    articleDate.value = new Date().toISOString().slice(0, 10)
    content.value = ''
    startPolling(res.id)
  } catch (e) { /* 拦截器处理 */ } finally {
    submitting.value = false
  }
}

// ==================== 轮询 ====================

function startPolling(articleId) {
  stopPolling()
  pollCount = 0
  pollTimer = setInterval(async () => {
    pollCount++
    if (pollCount > 40) { stopPolling(); return }
    try {
      const res = await getArticleStatus(articleId)
      currentArticle.value = res
      if (res.status === 'completed' || res.status === 'failed') {
        stopPolling()
        loadArticles()
        ElMessage[res.status === 'completed' ? 'success' : 'error'](res.status === 'completed' ? '分析完成' : '分析失败')
      }
    } catch (e) { /* 静默 */ }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// ==================== 文章列表 ====================

async function loadArticles() {
  loading.value = true
  try {
    const res = await getArticleList({ page: currentPage.value, pageSize: pageSize.value })
    articles.value = res.items || []
    total.value = res.total || 0
  } catch (e) { /* 静默 */ } finally {
    loading.value = false
  }
}

function handleSelectionChange(selection) {
  selectedArticles.value = selection
}

function openBatchDateDialog() {
  if (selectedArticles.value.length === 0) {
    ElMessage.warning('请先勾选文章')
    return
  }
  batchNewDate.value = new Date().toISOString().slice(0, 10)
  batchDateDialogVisible.value = true
}

async function handleBatchUpdateDate() {
  const ids = selectedArticles.value.map(a => a.id)
  try {
    const res = await batchUpdateDate(ids, batchNewDate.value)
    ElMessage.success(res.message)
    batchDateDialogVisible.value = false
    selectedArticles.value = []
    loadArticles()
  } catch (e) { /* 拦截器处理 */ }
}

async function handleRetry(row) {
  try {
    const res = await retryArticle(row.id)
    ElMessage.success('已重新提交')
    currentArticle.value = res
    startPolling(res.id)
    loadArticles()
  } catch (e) { /* 拦截器处理 */ }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' })
    await deleteArticle(row.id)
    ElMessage.success('已删除')
    loadArticles()
  } catch (e) { /* 取消 */ }
}

function handlePageChange(page) {
  currentPage.value = page
  loadArticles()
}

// ==================== 每日汇总 ====================

async function handleGenerateSummary() {
  summaryLoading.value = true
  try {
    await triggerDailySummary(summaryDate.value)
    ElMessage.success('正在生成每日汇总...')
    startSummaryPolling()
  } catch (e) { /* 拦截器处理 */ } finally {
    summaryLoading.value = false
  }
}

function startSummaryPolling() {
  stopSummaryPolling()
  let count = 0
  summaryPollTimer = setInterval(async () => {
    count++
    if (count > 60) { stopSummaryPolling(); return }
    try {
      const res = await getDailySummary(summaryDate.value)
      dailySummary.value = res
      if (res.status === 'completed' || res.status === 'failed') {
        stopSummaryPolling()
        ElMessage[res.status === 'completed' ? 'success' : 'error'](res.status === 'completed' ? '每日汇总完成' : '汇总生成失败')
      }
    } catch (e) { /* 静默 */ }
  }, 3000)
}

function stopSummaryPolling() {
  if (summaryPollTimer) { clearInterval(summaryPollTimer); summaryPollTimer = null }
}

async function loadDailySummary() {
  try {
    const res = await getDailySummary(summaryDate.value)
    dailySummary.value = res
  } catch (e) {
    dailySummary.value = null
  }
}

function onSummaryDateChange() {
  loadDailySummary()
}

// ==================== 工具函数 ====================

function parseAnalysis(resultSummary) {
  if (!resultSummary) return null
  try { return JSON.parse(resultSummary) } catch { return null }
}

function parseJsonField(jsonStr) {
  if (!jsonStr) return []
  try { return JSON.parse(jsonStr) } catch { return [] }
}

function opinionColor(opinion) {
  const map = { '看多': '#67c23a', '看空': '#f56c6c', '中性': '#909399', '观望': '#e6a23c' }
  return map[opinion] || '#909399'
}

function probabilityColor(p) {
  if (p == null) return '#909399'
  if (p >= 60) return '#67c23a'
  if (p >= 40) return '#e6a23c'
  return '#f56c6c'
}

function heatTag(score) {
  if (score == null) return { text: '-', type: 'info' }
  if (score >= 70) return { text: `${score} 火热`, type: 'danger' }
  if (score >= 40) return { text: `${score} 温和`, type: 'warning' }
  return { text: `${score} 冷门`, type: 'info' }
}

function formatStatus(s) {
  return { pending: '待处理', processing: '分析中', completed: '已完成', failed: '失败' }[s] || s
}

function statusType(s) {
  return { pending: 'info', processing: 'warning', completed: 'success', failed: 'danger' }[s] || 'info'
}

function formatDuration(sec) {
  if (!sec) return '-'
  return sec < 60 ? `${sec}秒` : `${Math.floor(sec / 60)}分${sec % 60}秒`
}

function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
}

onMounted(() => { loadArticles(); loadDailySummary() })
onUnmounted(() => { stopPolling(); stopSummaryPolling() })
</script>

<template>
  <div>
    <!-- 提交区域 -->
    <el-card style="margin-bottom: 20px">
      <template #header>
        <div style="display: flex; align-items: center; gap: 16px">
          <span style="font-weight: bold">提交文章</span>
          <el-radio-group v-model="submitMode" size="small">
            <el-radio-button value="url">链接提取</el-radio-button>
            <el-radio-button value="manual">手动粘贴</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div v-if="submitMode === 'url'">
        <!-- 自定义日期 -->
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px">
          <span style="font-size: 13px; color: #606266; white-space: nowrap">指定日期：</span>
          <el-date-picker
            v-model="urlCustomDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="不指定则自动提取"
            style="width: 180px"
            :disabled="urlDateConfirmed"
            clearable
          />
          <el-button
            v-if="!urlDateConfirmed"
            type="primary"
            size="small"
            :disabled="!urlCustomDate"
            @click="handleUrlDateConfirm"
          >确认</el-button>
          <template v-else>
            <el-tag type="success" size="small">已锁定：{{ urlCustomDate }}</el-tag>
            <el-button type="info" size="small" plain @click="handleUrlDateCancel">取消</el-button>
          </template>
        </div>
        <div style="display: flex; gap: 12px">
          <el-input v-model="articleUrl" placeholder="粘贴淘股吧文章链接" clearable style="flex: 1" @keyup.enter="handleUrlSubmit" />
          <el-button type="primary" :loading="urlSubmitting" @click="handleUrlSubmit">提取并分析</el-button>
        </div>
        <p style="margin-top: 8px; font-size: 12px; color: #909399">支持淘股吧(tgb.cn)、韭研公社(jiuyangongshe.com)，自动提取标题/作者/日期/正文</p>
      </div>
      <el-form v-else label-width="80px">
        <div style="display: flex; gap: 16px; margin-bottom: 16px">
          <el-form-item label="标题" style="flex: 1; margin-bottom: 0">
            <el-input v-model="title" placeholder="可选" clearable />
          </el-form-item>
          <el-form-item label="作者" style="width: 160px; margin-bottom: 0">
            <el-input v-model="author" placeholder="可选" clearable />
          </el-form-item>
          <el-form-item label="日期" style="width: 200px; margin-bottom: 0">
            <el-date-picker v-model="articleDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="来源" style="width: 160px; margin-bottom: 0">
            <el-input v-model="source" placeholder="可选" clearable />
          </el-form-item>
        </div>
        <el-form-item label="内容" required>
          <el-input v-model="content" type="textarea" :rows="8" placeholder="粘贴文章内容（至少10个字符）" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">提交分析</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 当前处理状态 -->
    <el-card v-if="currentArticle && (currentArticle.status === 'pending' || currentArticle.status === 'processing')" style="margin-bottom: 20px">
      <div style="text-align: center; padding: 20px 0">
        <el-icon class="is-loading" :size="28" style="color: #409eff; margin-bottom: 8px"><Loading /></el-icon>
        <p style="color: #909399">正在分析文章，预计20秒左右...</p>
      </div>
    </el-card>

    <!-- 每日汇总 -->
    <el-card style="margin-bottom: 20px">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between">
          <span style="font-weight: bold">每日综合策略</span>
          <div style="display: flex; align-items: center; gap: 12px">
            <el-date-picker v-model="summaryDate" type="date" value-format="YYYY-MM-DD" style="width: 160px" @change="onSummaryDateChange" />
            <el-button type="success" :loading="summaryLoading" @click="handleGenerateSummary">
              生成汇总
            </el-button>
          </div>
        </div>
      </template>

      <!-- 汇总内容 -->
      <div v-if="dailySummary && dailySummary.status === 'completed'">
        <div style="margin-bottom: 8px; color: #909399; font-size: 13px">
          基于 {{ dailySummary.articleCount }} 篇文章 | 耗时 {{ formatDuration(dailySummary.processDuration) }}
        </div>

        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="多作者共识">{{ dailySummary.consensus || '-' }}</el-descriptions-item>
          <el-descriptions-item label="分歧点">{{ dailySummary.divergence || '-' }}</el-descriptions-item>
          <el-descriptions-item label="明日策略">{{ dailySummary.strategy || '-' }}</el-descriptions-item>
          <el-descriptions-item label="策略演变">{{ dailySummary.evolution || '-' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 个股综合观点 -->
        <div v-if="parseJsonField(dailySummary.stockViews).length" style="margin-top: 16px">
          <p style="font-weight: bold; margin-bottom: 8px">个股综合观点</p>
          <el-table :data="parseJsonField(dailySummary.stockViews)" size="small" border>
            <el-table-column prop="name" label="股票" width="120" />
            <el-table-column label="看多/空/中" width="120" align="center">
              <template #default="{ row }">
                <span style="color: #67c23a">{{ row.bullCount || 0 }}</span> /
                <span style="color: #f56c6c">{{ row.bearCount || 0 }}</span> /
                <span style="color: #909399">{{ row.neutralCount || 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column label="上涨概率" width="140" align="center">
              <template #default="{ row }">
                <div v-if="row.probability != null" style="display: flex; align-items: center; gap: 6px">
                  <el-progress
                    :percentage="row.probability"
                    :stroke-width="14"
                    :color="probabilityColor(row.probability)"
                    :show-text="false"
                    style="flex: 1"
                  />
                  <span :style="{ color: probabilityColor(row.probability), fontWeight: 'bold', fontSize: '13px', minWidth: '36px' }">{{ row.probability }}%</span>
                </div>
                <span v-else style="color: #c0c4cc">-</span>
              </template>
            </el-table-column>
            <el-table-column label="热度" width="100" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.heatScore != null" :type="heatTag(row.heatScore).type" size="small">{{ heatTag(row.heatScore).text }}</el-tag>
                <span v-else style="color: #c0c4cc">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="synthesis" label="综合看法" />
            <el-table-column prop="suggestedAction" label="建议操作" width="200" />
          </el-table>
        </div>

        <!-- 板块综合观点 -->
        <div v-if="parseJsonField(dailySummary.sectorViews).length" style="margin-top: 16px">
          <p style="font-weight: bold; margin-bottom: 8px">板块综合观点</p>
          <el-table :data="parseJsonField(dailySummary.sectorViews)" size="small" border>
            <el-table-column prop="name" label="板块" width="150" />
            <el-table-column prop="outlook" label="综合展望" />
            <el-table-column prop="keyPoints" label="关键要点" />
          </el-table>
        </div>
      </div>

      <div v-else-if="dailySummary && dailySummary.status === 'processing'" style="text-align: center; padding: 20px 0">
        <el-icon class="is-loading" :size="28" style="color: #67c23a"><Loading /></el-icon>
        <p style="color: #909399; margin-top: 8px">正在生成综合策略...</p>
      </div>

      <div v-else-if="dailySummary && dailySummary.status === 'failed'">
        <el-alert type="error" :closable="false">
          <template #title>{{ dailySummary.errorMessage || '生成失败' }}</template>
        </el-alert>
      </div>

      <div v-else style="text-align: center; padding: 20px 0; color: #c0c4cc">
        提交文章分析完成后，点击"生成汇总"获取当日综合策略
      </div>
    </el-card>

    <!-- 文章列表 -->
    <el-card v-loading="loading">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between">
          <span style="font-weight: bold">文章分析记录</span>
          <el-button
            v-if="selectedArticles.length > 0"
            type="primary"
            size="small"
            @click="openBatchDateDialog"
          >
            批量修改日期 ({{ selectedArticles.length }})
          </el-button>
        </div>
      </template>
      <el-table :data="articles" style="width: 100%" row-key="id" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column type="expand">
          <template #default="{ row }">
            <div style="padding: 12px 20px">
              <!-- 结构化观点 -->
              <div v-if="parseAnalysis(row.resultSummary)" style="margin-bottom: 16px">
                <div style="margin-bottom: 12px">
                  <p style="font-weight: bold; margin-bottom: 4px">市场判断</p>
                  <p style="color: #606266; font-size: 13px">{{ parseAnalysis(row.resultSummary).marketView || '-' }}</p>
                </div>

                <div v-if="parseAnalysis(row.resultSummary).stockViews?.length" style="margin-bottom: 12px">
                  <p style="font-weight: bold; margin-bottom: 8px">个股观点</p>
                  <el-table :data="parseAnalysis(row.resultSummary).stockViews" size="small" border>
                    <el-table-column prop="name" label="股票" width="120" />
                    <el-table-column prop="opinion" label="看法" width="70" align="center">
                      <template #default="{ row: sv }">
                        <span :style="{ color: opinionColor(sv.opinion), fontWeight: 'bold' }">{{ sv.opinion }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="logic" label="逻辑" />
                    <el-table-column prop="strategy" label="策略" width="180" />
                    <el-table-column prop="risk" label="风险" width="150" />
                  </el-table>
                </div>

                <div v-if="parseAnalysis(row.resultSummary).sectorViews?.length" style="margin-bottom: 12px">
                  <p style="font-weight: bold; margin-bottom: 8px">板块观点</p>
                  <el-table :data="parseAnalysis(row.resultSummary).sectorViews" size="small" border>
                    <el-table-column prop="name" label="板块" width="150" />
                    <el-table-column prop="opinion" label="看法" width="70" align="center">
                      <template #default="{ row: sv }">
                        <span :style="{ color: opinionColor(sv.opinion), fontWeight: 'bold' }">{{ sv.opinion }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="logic" label="逻辑" />
                    <el-table-column prop="keyStocks" label="关键票" width="200">
                      <template #default="{ row: sv }">{{ (sv.keyStocks || []).join('、') }}</template>
                    </el-table-column>
                  </el-table>
                </div>

                <div v-if="parseAnalysis(row.resultSummary).keyPredictions?.length" style="margin-bottom: 12px">
                  <p style="font-weight: bold; margin-bottom: 4px">关键预判</p>
                  <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                    <li v-for="(p, i) in parseAnalysis(row.resultSummary).keyPredictions" :key="i">{{ p }}</li>
                  </ul>
                </div>

                <div v-if="parseAnalysis(row.resultSummary).tradingAdvice">
                  <p style="font-weight: bold; margin-bottom: 4px">操作建议</p>
                  <p style="color: #606266; font-size: 13px">{{ parseAnalysis(row.resultSummary).tradingAdvice }}</p>
                </div>
              </div>

              <!-- 错误信息 -->
              <div v-if="row.errorMessage">
                <pre style="white-space: pre-wrap; background: #fef0f0; padding: 12px; border-radius: 4px; color: #f56c6c; font-size: 13px">{{ row.errorMessage }}</pre>
              </div>

              <!-- 原文链接 -->
              <div v-if="row.sourceUrl" style="margin-top: 8px">
                <a :href="row.sourceUrl" target="_blank" style="color: #409eff; font-size: 13px">查看原文</a>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="180">
          <template #default="{ row }">{{ row.title || '（无标题）' }}</template>
        </el-table-column>
        <el-table-column prop="author" label="作者" width="100">
          <template #default="{ row }">{{ row.author || '-' }}</template>
        </el-table-column>
        <el-table-column prop="articleDate" label="日期" width="110" sortable />
        <el-table-column prop="source" label="来源" width="80">
          <template #default="{ row }">{{ row.source || '-' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ formatStatus(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="processDuration" label="耗时" width="70" align="center">
          <template #default="{ row }">{{ formatDuration(row.processDuration) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button v-if="row.status === 'failed'" text type="warning" size="small" @click="handleRetry(row)">重试</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="total > pageSize" style="margin-top: 16px; display: flex; justify-content: flex-end">
        <el-pagination :current-page="currentPage" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="handlePageChange" />
      </div>
    </el-card>

    <!-- 批量修改日期弹窗 -->
    <el-dialog v-model="batchDateDialogVisible" title="批量修改日期" width="400px">
      <div style="margin-bottom: 12px; color: #606266">
        已选 <b>{{ selectedArticles.length }}</b> 篇文章，统一修改为：
      </div>
      <el-date-picker
        v-model="batchNewDate"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="选择日期"
        style="width: 100%"
      />
      <template #footer>
        <el-button @click="batchDateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchUpdateDate">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>
