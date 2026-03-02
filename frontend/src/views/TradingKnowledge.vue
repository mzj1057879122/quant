<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  submitKnowledge, submitKnowledgeFromUrl, getKnowledgeList, getKnowledge,
  updateKnowledge, retryKnowledge, reExtractKnowledge, deleteKnowledge,
  rebuildFramework, getLatestFramework, getFrameworkHistory,
} from '../api/knowledge'

// ==================== 框架 ====================
const framework = ref(null)
const frameworkLoading = ref(false)
const showFullFramework = ref(false)

async function loadFramework() {
  try {
    const res = await getLatestFramework()
    framework.value = res
  } catch (e) {
    framework.value = null
  }
}

let frameworkPollTimer = null
async function handleRebuildFramework() {
  frameworkLoading.value = true
  try {
    await rebuildFramework()
    ElMessage.success('正在重建框架...')
    startFrameworkPolling()
  } catch (e) { /* 拦截器 */ } finally {
    frameworkLoading.value = false
  }
}

function startFrameworkPolling() {
  stopFrameworkPolling()
  let count = 0
  frameworkPollTimer = setInterval(async () => {
    count++
    if (count > 60) { stopFrameworkPolling(); return }
    try {
      const res = await getLatestFramework()
      if (res && (res.status === 'completed' || res.status === 'failed')) {
        framework.value = res
        stopFrameworkPolling()
        ElMessage[res.status === 'completed' ? 'success' : 'error'](
          res.status === 'completed' ? '框架重建完成' : '框架重建失败'
        )
      }
    } catch (e) { /* 静默 */ }
  }, 3000)
}

function stopFrameworkPolling() {
  if (frameworkPollTimer) { clearInterval(frameworkPollTimer); frameworkPollTimer = null }
}

function parseFrameworkContent(fw) {
  if (!fw?.frameworkContent) return null
  try { return JSON.parse(fw.frameworkContent) } catch { return null }
}

// v2 框架是否为新格式（含 modules 字段）
function isV2Framework(content) {
  return content && content.modules && typeof content.modules === 'object'
}

// v2 提取原则是否为新格式
function isV2Principles(p) {
  return p && p.modules && typeof p.modules === 'object'
}

// 7 模块元数据
const MODULE_META = {
  marketAssessment: { name: '大盘大势判断', icon: '📊' },
  sectorScreening: { name: '板块轮动与主线判断', icon: '🔍' },
  capitalFlow: { name: '主力资金行为分析', icon: '💰' },
  patterns: { name: 'K线与形态交易法', icon: '📈' },
  tactics: { name: '涨停战法', icon: '🎯' },
  intradayTiming: { name: '分时交易技法', icon: '⏰' },
  riskManagement: { name: '风控与资金管理', icon: '🛡️' },
}

const MODULE_ORDER = ['marketAssessment', 'sectorScreening', 'capitalFlow', 'patterns', 'tactics', 'intradayTiming', 'riskManagement']

// 统计框架模块规则数
function countModuleRules(mod, key) {
  if (!mod || typeof mod !== 'object') return 0
  if (key === 'marketAssessment') return (mod.rules || []).length
  if (key === 'sectorScreening') return (mod.screeningRules || []).length + (mod.grading || []).length + (mod.rotationRules || []).length
  if (key === 'capitalFlow') return (mod.phases || []).length
  if (key === 'patterns') return (mod.buyPatterns || []).length + (mod.sellSignals || []).length
  if (key === 'tactics') return (mod.strategies || []).length
  if (key === 'intradayTiming') return (mod.buySignals || []).length + (mod.sellSignals || []).length
  if (key === 'riskManagement') return (mod.positionRules || []).length + (mod.stopLossRules || []).length + (mod.stopProfitRules || []).length + (mod.discipline || []).length
  return 0
}

// 判断提取的模块是否有内容
function hasModuleContent(mod) {
  if (!mod || typeof mod !== 'object') return false
  return Object.values(mod).some(v => Array.isArray(v) ? v.length > 0 : (v && typeof v === 'object' && Object.keys(v).length > 0))
}

// ==================== 提交心得 ====================
const submitMode = ref('url')
const knowledgeUrl = ref('')
const urlCategory = ref('')
const urlSubmitting = ref(false)
const kTitle = ref('')
const kAuthor = ref('')
const kSource = ref('')
const kCategory = ref('')
const kContent = ref('')
const submitting = ref(false)

// 轮询
const currentKnowledge = ref(null)
let pollTimer = null
let pollCount = 0

async function handleUrlSubmit() {
  if (!knowledgeUrl.value?.trim()) {
    ElMessage.warning('请输入文章链接')
    return
  }
  urlSubmitting.value = true
  try {
    const res = await submitKnowledgeFromUrl({
      url: knowledgeUrl.value.trim(),
      category: urlCategory.value || null,
    })
    currentKnowledge.value = res
    ElMessage.success(`已提取「${res.title || '文章'}」，正在提取原则...`)
    knowledgeUrl.value = ''
    urlCategory.value = ''
    startPolling(res.id)
    loadKnowledgeList()
  } catch (e) { /* 拦截器 */ } finally {
    urlSubmitting.value = false
  }
}

async function handleManualSubmit() {
  if (!kTitle.value?.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  if (!kContent.value || kContent.value.trim().length < 10) {
    ElMessage.warning('请输入至少10个字符的内容')
    return
  }
  submitting.value = true
  try {
    const res = await submitKnowledge({
      title: kTitle.value,
      author: kAuthor.value || null,
      content: kContent.value,
      source: kSource.value || null,
      category: kCategory.value || null,
    })
    currentKnowledge.value = res
    ElMessage.success('心得已提交，正在提取原则...')
    kTitle.value = ''
    kAuthor.value = ''
    kSource.value = ''
    kCategory.value = ''
    kContent.value = ''
    startPolling(res.id)
    loadKnowledgeList()
  } catch (e) { /* 拦截器 */ } finally {
    submitting.value = false
  }
}

function startPolling(id) {
  stopPolling()
  pollCount = 0
  pollTimer = setInterval(async () => {
    pollCount++
    if (pollCount > 40) { stopPolling(); return }
    try {
      const res = await getKnowledge(id)
      currentKnowledge.value = res
      if (res.status === 'completed' || res.status === 'failed') {
        stopPolling()
        loadKnowledgeList()
        ElMessage[res.status === 'completed' ? 'success' : 'error'](
          res.status === 'completed' ? '原则提取完成' : '原则提取失败'
        )
      }
    } catch (e) { /* 静默 */ }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// ==================== 心得列表 ====================
const knowledgeItems = ref([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)

async function loadKnowledgeList() {
  loading.value = true
  try {
    const res = await getKnowledgeList({ page: currentPage.value, pageSize: pageSize.value })
    knowledgeItems.value = res.items || []
    total.value = res.total || 0
  } catch (e) { /* 静默 */ } finally {
    loading.value = false
  }
}

function handlePageChange(page) {
  currentPage.value = page
  loadKnowledgeList()
}

async function handleRetry(row) {
  try {
    const res = await retryKnowledge(row.id)
    ElMessage.success('已重新提交')
    currentKnowledge.value = res
    startPolling(res.id)
    loadKnowledgeList()
  } catch (e) { /* 拦截器 */ }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' })
    await deleteKnowledge(row.id)
    ElMessage.success('已删除')
    loadKnowledgeList()
  } catch (e) { /* 取消 */ }
}

// ==================== 编辑 ====================
const editDialogVisible = ref(false)
const editForm = ref({ id: 0, title: '', author: '', content: '', category: '' })

function handleEdit(row) {
  editForm.value = {
    id: row.id,
    title: row.title,
    author: row.author || '',
    content: row.content,
    category: row.category || '',
  }
  editDialogVisible.value = true
}

async function handleEditSave() {
  try {
    await updateKnowledge(editForm.value.id, {
      title: editForm.value.title,
      author: editForm.value.author || null,
      content: editForm.value.content,
      category: editForm.value.category || null,
    })
    ElMessage.success('已保存')
    editDialogVisible.value = false
    loadKnowledgeList()
  } catch (e) { /* 拦截器 */ }
}

async function handleReExtract(row) {
  try {
    const res = await reExtractKnowledge(row.id)
    ElMessage.success('已重新提取')
    currentKnowledge.value = res
    startPolling(res.id)
    loadKnowledgeList()
  } catch (e) { /* 拦截器 */ }
}

// ==================== 工具函数 ====================

function parsePrinciples(str) {
  if (!str) return null
  try { return JSON.parse(str) } catch { return null }
}

function formatStatus(s) {
  return { pending: '待处理', processing: '提取中', completed: '已完成', failed: '失败' }[s] || s
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

onMounted(() => { loadFramework(); loadKnowledgeList() })
onUnmounted(() => { stopPolling(); stopFrameworkPolling() })
</script>

<template>
  <div>
    <!-- 当前交易框架 -->
    <el-card style="margin-bottom: 20px">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between">
          <span style="font-weight: bold">当前交易框架</span>
          <el-button type="primary" :loading="frameworkLoading" @click="handleRebuildFramework">重建框架</el-button>
        </div>
      </template>

      <div v-if="framework && framework.status === 'completed' && parseFrameworkContent(framework)">
        <div style="margin-bottom: 12px; color: #909399; font-size: 13px">
          v{{ framework.version }} | 基于 {{ framework.knowledgeCount }} 篇心得 | {{ formatTime(framework.createdAt) }} | 耗时 {{ formatDuration(framework.processDuration) }}
        </div>

        <!-- v2 新格式：7模块 collapse -->
        <template v-if="isV2Framework(parseFrameworkContent(framework))">
          <p style="margin-bottom: 8px">
            <strong>核心哲学：</strong>{{ parseFrameworkContent(framework).tradingPhilosophy || '-' }}
          </p>

          <div v-if="!showFullFramework">
            <div style="display: flex; flex-wrap: wrap; gap: 12px; color: #606266; font-size: 13px; margin-bottom: 8px">
              <span v-for="key in MODULE_ORDER" :key="key">
                {{ MODULE_META[key].name }}: {{ countModuleRules(parseFrameworkContent(framework).modules?.[key], key) }}条
              </span>
            </div>
            <el-button text type="primary" size="small" @click="showFullFramework = true">展开查看完整框架</el-button>
          </div>

          <div v-else>
            <el-collapse style="margin-top: 12px">
              <template v-for="key in MODULE_ORDER" :key="key">
                <el-collapse-item v-if="countModuleRules(parseFrameworkContent(framework).modules?.[key], key) > 0" :name="key">
                  <template #title>
                    <span style="font-weight: bold">{{ MODULE_META[key].name }}</span>
                    <span style="margin-left: 8px; color: #909399; font-size: 12px">
                      {{ parseFrameworkContent(framework).modules[key]?.purpose || '' }}
                      ({{ countModuleRules(parseFrameworkContent(framework).modules[key], key) }}条)
                    </span>
                  </template>

                  <!-- 大盘判断 -->
                  <div v-if="key === 'marketAssessment' && parseFrameworkContent(framework).modules[key]?.rules?.length">
                    <el-table :data="parseFrameworkContent(framework).modules[key].rules" size="small" border>
                      <el-table-column prop="dimension" label="维度" width="150" />
                      <el-table-column label="强势">
                        <template #default="{ row }">
                          <div v-if="row.levels?.['强势']">
                            <div style="font-size: 12px; color: #67c23a">{{ (row.levels['强势'].criteria || []).join('；') }}</div>
                            <div v-if="row.levels['强势'].action" style="font-size: 12px; color: #409eff; margin-top: 2px">→ {{ row.levels['强势'].action }}</div>
                          </div>
                        </template>
                      </el-table-column>
                      <el-table-column label="震荡">
                        <template #default="{ row }">
                          <div v-if="row.levels?.['震荡']">
                            <div style="font-size: 12px; color: #e6a23c">{{ (row.levels['震荡'].criteria || []).join('；') }}</div>
                            <div v-if="row.levels['震荡'].action" style="font-size: 12px; color: #409eff; margin-top: 2px">→ {{ row.levels['震荡'].action }}</div>
                          </div>
                        </template>
                      </el-table-column>
                      <el-table-column label="弱势">
                        <template #default="{ row }">
                          <div v-if="row.levels?.['弱势']">
                            <div style="font-size: 12px; color: #f56c6c">{{ (row.levels['弱势'].criteria || []).join('；') }}</div>
                            <div v-if="row.levels['弱势'].action" style="font-size: 12px; color: #409eff; margin-top: 2px">→ {{ row.levels['弱势'].action }}</div>
                          </div>
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>

                  <!-- 板块筛选 -->
                  <div v-if="key === 'sectorScreening'">
                    <div v-if="parseFrameworkContent(framework).modules[key]?.screeningRules?.length" style="margin-bottom: 12px">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">筛选条件</p>
                      <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                        <li v-for="(r, i) in parseFrameworkContent(framework).modules[key].screeningRules" :key="i">{{ r }}</li>
                      </ul>
                    </div>
                    <div v-if="parseFrameworkContent(framework).modules[key]?.grading?.length" style="margin-bottom: 12px">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">板块分级</p>
                      <el-table :data="parseFrameworkContent(framework).modules[key].grading" size="small" border>
                        <el-table-column prop="level" label="级别" width="80" />
                        <el-table-column prop="criteria" label="标准" />
                        <el-table-column prop="action" label="操作" width="200" />
                      </el-table>
                    </div>
                    <div v-if="parseFrameworkContent(framework).modules[key]?.rotationRules?.length">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">轮动规则</p>
                      <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                        <li v-for="(r, i) in parseFrameworkContent(framework).modules[key].rotationRules" :key="i">{{ r }}</li>
                      </ul>
                    </div>
                  </div>

                  <!-- 资金行为 -->
                  <div v-if="key === 'capitalFlow' && parseFrameworkContent(framework).modules[key]?.phases?.length">
                    <el-table :data="parseFrameworkContent(framework).modules[key].phases" size="small" border>
                      <el-table-column prop="phase" label="阶段" width="100" />
                      <el-table-column label="信号">
                        <template #default="{ row }">{{ (row.signals || []).join('；') }}</template>
                      </el-table-column>
                      <el-table-column prop="action" label="操作" width="200" />
                    </el-table>
                  </div>

                  <!-- K线形态 -->
                  <div v-if="key === 'patterns'">
                    <div v-if="parseFrameworkContent(framework).modules[key]?.buyPatterns?.length" style="margin-bottom: 12px">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">买入形态</p>
                      <el-table :data="parseFrameworkContent(framework).modules[key].buyPatterns" size="small" border>
                        <el-table-column prop="name" label="形态" width="120" />
                        <el-table-column prop="trigger" label="触发条件" />
                        <el-table-column prop="entry" label="入场点" width="180" />
                        <el-table-column prop="stopLoss" label="止损点" width="150" />
                      </el-table>
                    </div>
                    <div v-if="parseFrameworkContent(framework).modules[key]?.sellSignals?.length">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">卖出信号</p>
                      <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                        <li v-for="(s, i) in parseFrameworkContent(framework).modules[key].sellSignals" :key="i">{{ s }}</li>
                      </ul>
                    </div>
                  </div>

                  <!-- 涨停战法 -->
                  <div v-if="key === 'tactics' && parseFrameworkContent(framework).modules[key]?.strategies?.length">
                    <el-table :data="parseFrameworkContent(framework).modules[key].strategies" size="small" border>
                      <el-table-column prop="name" label="战法" width="120" />
                      <el-table-column prop="marketCondition" label="适用市况" width="100" />
                      <el-table-column label="条件">
                        <template #default="{ row }">{{ (row.conditions || []).join('；') }}</template>
                      </el-table-column>
                      <el-table-column prop="entry" label="入场" width="120" />
                      <el-table-column prop="stopProfit" label="止盈" width="100" />
                      <el-table-column prop="stopLoss" label="止损" width="100" />
                      <el-table-column prop="source" label="来源" width="80" />
                    </el-table>
                  </div>

                  <!-- 分时技法 -->
                  <div v-if="key === 'intradayTiming'">
                    <div v-if="parseFrameworkContent(framework).modules[key]?.buySignals?.length" style="margin-bottom: 12px">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">买入信号</p>
                      <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                        <li v-for="(s, i) in parseFrameworkContent(framework).modules[key].buySignals" :key="i">{{ s }}</li>
                      </ul>
                    </div>
                    <div v-if="parseFrameworkContent(framework).modules[key]?.sellSignals?.length">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">卖出信号</p>
                      <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                        <li v-for="(s, i) in parseFrameworkContent(framework).modules[key].sellSignals" :key="i">{{ s }}</li>
                      </ul>
                    </div>
                  </div>

                  <!-- 风控 -->
                  <div v-if="key === 'riskManagement'">
                    <div v-if="parseFrameworkContent(framework).modules[key]?.positionRules?.length" style="margin-bottom: 12px">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">仓位规则</p>
                      <el-table :data="parseFrameworkContent(framework).modules[key].positionRules" size="small" border>
                        <el-table-column prop="scenario" label="场景" width="150" />
                        <el-table-column prop="singlePosition" label="单只仓位" />
                        <el-table-column prop="totalPosition" label="整体仓位" />
                      </el-table>
                    </div>
                    <div v-if="parseFrameworkContent(framework).modules[key]?.stopLossRules?.length" style="margin-bottom: 12px">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">止损规则</p>
                      <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                        <li v-for="(r, i) in parseFrameworkContent(framework).modules[key].stopLossRules" :key="i">{{ r }}</li>
                      </ul>
                    </div>
                    <div v-if="parseFrameworkContent(framework).modules[key]?.stopProfitRules?.length" style="margin-bottom: 12px">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">止盈规则</p>
                      <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                        <li v-for="(r, i) in parseFrameworkContent(framework).modules[key].stopProfitRules" :key="i">{{ r }}</li>
                      </ul>
                    </div>
                    <div v-if="parseFrameworkContent(framework).modules[key]?.discipline?.length">
                      <p style="font-weight: 500; margin-bottom: 4px; font-size: 13px">交易纪律</p>
                      <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                        <li v-for="(r, i) in parseFrameworkContent(framework).modules[key].discipline" :key="i">{{ r }}</li>
                      </ul>
                    </div>
                  </div>

                </el-collapse-item>
              </template>
            </el-collapse>
            <el-button text type="primary" size="small" style="margin-top: 8px" @click="showFullFramework = false">收起</el-button>
          </div>
        </template>

        <!-- v1 旧格式兼容 -->
        <template v-else>
          <div v-if="!showFullFramework">
            <p style="margin-bottom: 8px">
              <strong>核心哲学：</strong>{{ parseFrameworkContent(framework).tradingPhilosophy || '-' }}
            </p>
            <div style="display: flex; gap: 16px; color: #606266; font-size: 13px">
              <span>进场体系: {{ (parseFrameworkContent(framework).entrySystem || []).length }}条</span>
              <span>出场体系: {{ (parseFrameworkContent(framework).exitSystem || []).length }}条</span>
              <span>风控规则: {{ (parseFrameworkContent(framework).riskControl || []).length }}条</span>
              <span>仓位管理: {{ (parseFrameworkContent(framework).positionManagement || []).length }}条</span>
            </div>
            <el-button text type="primary" size="small" style="margin-top: 8px" @click="showFullFramework = true">展开查看完整框架</el-button>
          </div>
          <div v-else>
            <el-descriptions :column="1" border size="small" style="margin-bottom: 16px">
              <el-descriptions-item label="核心哲学">{{ parseFrameworkContent(framework).tradingPhilosophy || '-' }}</el-descriptions-item>
            </el-descriptions>
            <div v-if="parseFrameworkContent(framework).marketAnalysis" style="margin-bottom: 16px">
              <p style="font-weight: bold; margin-bottom: 8px">市场分析方法</p>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="情绪周期">{{ parseFrameworkContent(framework).marketAnalysis.emotionCycle || '-' }}</el-descriptions-item>
                <el-descriptions-item label="主线识别">{{ parseFrameworkContent(framework).marketAnalysis.mainLineLogic || '-' }}</el-descriptions-item>
              </el-descriptions>
            </div>
            <div v-if="parseFrameworkContent(framework).entrySystem?.length" style="margin-bottom: 16px">
              <p style="font-weight: bold; margin-bottom: 8px">进场体系</p>
              <el-table :data="parseFrameworkContent(framework).entrySystem" size="small" border>
                <el-table-column prop="pattern" label="模式" width="150" />
                <el-table-column prop="condition" label="条件" />
                <el-table-column prop="action" label="操作" width="200" />
                <el-table-column prop="source" label="来源" width="100" />
              </el-table>
            </div>
            <div v-if="parseFrameworkContent(framework).exitSystem?.length" style="margin-bottom: 16px">
              <p style="font-weight: bold; margin-bottom: 8px">出场体系</p>
              <el-table :data="parseFrameworkContent(framework).exitSystem" size="small" border>
                <el-table-column prop="pattern" label="模式" width="150" />
                <el-table-column prop="condition" label="条件" />
                <el-table-column prop="action" label="操作" width="200" />
                <el-table-column prop="source" label="来源" width="100" />
              </el-table>
            </div>
            <div v-if="parseFrameworkContent(framework).positionManagement?.length" style="margin-bottom: 16px">
              <p style="font-weight: bold; margin-bottom: 8px">仓位管理</p>
              <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                <li v-for="(rule, i) in parseFrameworkContent(framework).positionManagement" :key="i">{{ rule }}</li>
              </ul>
            </div>
            <div v-if="parseFrameworkContent(framework).riskControl?.length" style="margin-bottom: 16px">
              <p style="font-weight: bold; margin-bottom: 8px">风控规则</p>
              <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                <li v-for="(rule, i) in parseFrameworkContent(framework).riskControl" :key="i">{{ rule }}</li>
              </ul>
            </div>
            <div v-if="parseFrameworkContent(framework).emotionDiscipline?.length" style="margin-bottom: 16px">
              <p style="font-weight: bold; margin-bottom: 8px">情绪纪律</p>
              <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                <li v-for="(rule, i) in parseFrameworkContent(framework).emotionDiscipline" :key="i">{{ rule }}</li>
              </ul>
            </div>
            <el-button text type="primary" size="small" @click="showFullFramework = false">收起</el-button>
          </div>
        </template>
      </div>

      <div v-else-if="framework && framework.status === 'processing'" style="text-align: center; padding: 20px 0">
        <el-icon class="is-loading" :size="28" style="color: #409eff"><Loading /></el-icon>
        <p style="color: #909399; margin-top: 8px">正在合成交易框架...</p>
      </div>

      <div v-else-if="framework && framework.status === 'failed'">
        <el-alert type="error" :closable="false">
          <template #title>{{ framework.errorMessage || '框架合成失败' }}</template>
        </el-alert>
      </div>

      <div v-else style="text-align: center; padding: 20px 0; color: #c0c4cc">
        暂无交易框架，提交交易心得后点击"重建框架"生成
      </div>
    </el-card>

    <!-- 提交交易心得 -->
    <el-card style="margin-bottom: 20px">
      <template #header>
        <div style="display: flex; align-items: center; gap: 16px">
          <span style="font-weight: bold">提交交易心得</span>
          <el-radio-group v-model="submitMode" size="small">
            <el-radio-button value="url">链接提取</el-radio-button>
            <el-radio-button value="manual">手动粘贴</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <div v-if="submitMode === 'url'">
        <div style="display: flex; gap: 12px">
          <el-input v-model="knowledgeUrl" placeholder="粘贴文章链接" clearable style="flex: 1" @keyup.enter="handleUrlSubmit" />
          <el-input v-model="urlCategory" placeholder="分类（可选）" clearable style="width: 120px" />
          <el-button type="primary" :loading="urlSubmitting" @click="handleUrlSubmit">提取并分析</el-button>
        </div>
        <p style="margin-top: 8px; font-size: 12px; color: #909399">支持淘股吧(tgb.cn)、韭研公社(jiuyangongshe.com)</p>
      </div>

      <el-form v-else label-width="80px">
        <div style="display: flex; gap: 16px; margin-bottom: 16px">
          <el-form-item label="标题" style="flex: 1; margin-bottom: 0" required>
            <el-input v-model="kTitle" placeholder="交易心得标题" clearable />
          </el-form-item>
          <el-form-item label="作者" style="width: 160px; margin-bottom: 0">
            <el-input v-model="kAuthor" placeholder="可选" clearable />
          </el-form-item>
          <el-form-item label="分类" style="width: 140px; margin-bottom: 0">
            <el-input v-model="kCategory" placeholder="可选" clearable />
          </el-form-item>
          <el-form-item label="来源" style="width: 140px; margin-bottom: 0">
            <el-input v-model="kSource" placeholder="可选" clearable />
          </el-form-item>
        </div>
        <el-form-item label="内容" required>
          <el-input v-model="kContent" type="textarea" :rows="8" placeholder="粘贴交易心得内容（至少10个字符）" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleManualSubmit">提交分析</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 处理状态 -->
    <el-card v-if="currentKnowledge && (currentKnowledge.status === 'pending' || currentKnowledge.status === 'processing')" style="margin-bottom: 20px">
      <div style="text-align: center; padding: 20px 0">
        <el-icon class="is-loading" :size="28" style="color: #409eff; margin-bottom: 8px"><Loading /></el-icon>
        <p style="color: #909399">正在提取交易原则，预计30秒左右...</p>
      </div>
    </el-card>

    <!-- 心得文章列表 -->
    <el-card v-loading="loading">
      <template #header>
        <span style="font-weight: bold">交易心得列表</span>
      </template>
      <el-table :data="knowledgeItems" style="width: 100%" row-key="id">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div style="padding: 12px 20px">
              <!-- 提取的交易原则 -->
              <div v-if="parsePrinciples(row.extractedPrinciples)">
                <div style="margin-bottom: 12px">
                  <p style="font-weight: bold; margin-bottom: 4px">交易风格</p>
                  <el-tag size="small">{{ parsePrinciples(row.extractedPrinciples).tradingStyle || '未知' }}</el-tag>
                </div>

                <div v-if="parsePrinciples(row.extractedPrinciples).corePrinciples?.length" style="margin-bottom: 12px">
                  <p style="font-weight: bold; margin-bottom: 4px">核心原则</p>
                  <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                    <li v-for="(p, i) in parsePrinciples(row.extractedPrinciples).corePrinciples" :key="i">{{ p }}</li>
                  </ul>
                </div>

                <!-- v2 新格式：按模块展示 -->
                <template v-if="isV2Principles(parsePrinciples(row.extractedPrinciples))">
                  <template v-for="mkey in MODULE_ORDER" :key="mkey">
                    <div v-if="hasModuleContent(parsePrinciples(row.extractedPrinciples).modules[mkey])" style="margin-bottom: 12px">
                      <p style="font-weight: bold; margin-bottom: 8px">{{ MODULE_META[mkey].name }}</p>

                      <!-- 大盘判断 -->
                      <template v-if="mkey === 'marketAssessment'">
                        <el-table v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].rules?.length" :data="parsePrinciples(row.extractedPrinciples).modules[mkey].rules" size="small" border>
                          <el-table-column prop="dimension" label="维度" width="120" />
                          <el-table-column label="强势">
                            <template #default="{ row: r }">
                              <span style="font-size: 12px">{{ (r.levels?.['强势']?.criteria || []).join('；') }}</span>
                              <span v-if="r.levels?.['强势']?.action" style="font-size: 12px; color: #409eff"> → {{ r.levels['强势'].action }}</span>
                            </template>
                          </el-table-column>
                          <el-table-column label="震荡">
                            <template #default="{ row: r }">
                              <span style="font-size: 12px">{{ (r.levels?.['震荡']?.criteria || []).join('；') }}</span>
                              <span v-if="r.levels?.['震荡']?.action" style="font-size: 12px; color: #409eff"> → {{ r.levels['震荡'].action }}</span>
                            </template>
                          </el-table-column>
                          <el-table-column label="弱势">
                            <template #default="{ row: r }">
                              <span style="font-size: 12px">{{ (r.levels?.['弱势']?.criteria || []).join('；') }}</span>
                              <span v-if="r.levels?.['弱势']?.action" style="font-size: 12px; color: #409eff"> → {{ r.levels['弱势'].action }}</span>
                            </template>
                          </el-table-column>
                        </el-table>
                      </template>

                      <!-- 板块筛选 -->
                      <template v-if="mkey === 'sectorScreening'">
                        <ul v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].screeningRules?.length" style="margin: 0 0 8px; padding-left: 20px; color: #606266; font-size: 13px">
                          <li v-for="(r, i) in parsePrinciples(row.extractedPrinciples).modules[mkey].screeningRules" :key="i">{{ r }}</li>
                        </ul>
                        <el-table v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].grading?.length" :data="parsePrinciples(row.extractedPrinciples).modules[mkey].grading" size="small" border style="margin-bottom: 8px">
                          <el-table-column prop="level" label="级别" width="80" />
                          <el-table-column prop="criteria" label="标准" />
                          <el-table-column prop="action" label="操作" width="200" />
                        </el-table>
                        <ul v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].rotationRules?.length" style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                          <li v-for="(r, i) in parsePrinciples(row.extractedPrinciples).modules[mkey].rotationRules" :key="i">{{ r }}</li>
                        </ul>
                      </template>

                      <!-- 资金行为 -->
                      <template v-if="mkey === 'capitalFlow'">
                        <el-table v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].phases?.length" :data="parsePrinciples(row.extractedPrinciples).modules[mkey].phases" size="small" border>
                          <el-table-column prop="phase" label="阶段" width="100" />
                          <el-table-column label="信号">
                            <template #default="{ row: r }">{{ (r.signals || []).join('；') }}</template>
                          </el-table-column>
                          <el-table-column prop="action" label="操作" width="200" />
                        </el-table>
                      </template>

                      <!-- K线形态 -->
                      <template v-if="mkey === 'patterns'">
                        <el-table v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].buyPatterns?.length" :data="parsePrinciples(row.extractedPrinciples).modules[mkey].buyPatterns" size="small" border style="margin-bottom: 8px">
                          <el-table-column prop="name" label="形态" width="120" />
                          <el-table-column prop="trigger" label="触发条件" />
                          <el-table-column prop="entry" label="入场点" width="150" />
                          <el-table-column prop="stopLoss" label="止损点" width="150" />
                        </el-table>
                        <ul v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].sellSignals?.length" style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                          <li v-for="(s, i) in parsePrinciples(row.extractedPrinciples).modules[mkey].sellSignals" :key="i">{{ s }}</li>
                        </ul>
                      </template>

                      <!-- 涨停战法 -->
                      <template v-if="mkey === 'tactics'">
                        <el-table v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].strategies?.length" :data="parsePrinciples(row.extractedPrinciples).modules[mkey].strategies" size="small" border>
                          <el-table-column prop="name" label="战法" width="120" />
                          <el-table-column prop="marketCondition" label="适用市况" width="100" />
                          <el-table-column label="条件">
                            <template #default="{ row: r }">{{ (r.conditions || []).join('；') }}</template>
                          </el-table-column>
                          <el-table-column prop="entry" label="入场" width="100" />
                          <el-table-column prop="stopProfit" label="止盈" width="80" />
                          <el-table-column prop="stopLoss" label="止损" width="80" />
                        </el-table>
                      </template>

                      <!-- 分时技法 -->
                      <template v-if="mkey === 'intradayTiming'">
                        <div v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].buySignals?.length" style="margin-bottom: 8px">
                          <span style="font-size: 13px; color: #67c23a; font-weight: 500">买入：</span>
                          <ul style="margin: 4px 0 0; padding-left: 20px; color: #606266; font-size: 13px">
                            <li v-for="(s, i) in parsePrinciples(row.extractedPrinciples).modules[mkey].buySignals" :key="i">{{ s }}</li>
                          </ul>
                        </div>
                        <div v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].sellSignals?.length">
                          <span style="font-size: 13px; color: #f56c6c; font-weight: 500">卖出：</span>
                          <ul style="margin: 4px 0 0; padding-left: 20px; color: #606266; font-size: 13px">
                            <li v-for="(s, i) in parsePrinciples(row.extractedPrinciples).modules[mkey].sellSignals" :key="i">{{ s }}</li>
                          </ul>
                        </div>
                      </template>

                      <!-- 风控 -->
                      <template v-if="mkey === 'riskManagement'">
                        <el-table v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].positionRules?.length" :data="parsePrinciples(row.extractedPrinciples).modules[mkey].positionRules" size="small" border style="margin-bottom: 8px">
                          <el-table-column prop="scenario" label="场景" width="150" />
                          <el-table-column prop="singlePosition" label="单只仓位" />
                          <el-table-column prop="totalPosition" label="整体仓位" />
                        </el-table>
                        <ul v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].stopLossRules?.length" style="margin: 0 0 8px; padding-left: 20px; color: #606266; font-size: 13px">
                          <li v-for="(r, i) in parsePrinciples(row.extractedPrinciples).modules[mkey].stopLossRules" :key="'sl'+i">止损: {{ r }}</li>
                        </ul>
                        <ul v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].stopProfitRules?.length" style="margin: 0 0 8px; padding-left: 20px; color: #606266; font-size: 13px">
                          <li v-for="(r, i) in parsePrinciples(row.extractedPrinciples).modules[mkey].stopProfitRules" :key="'sp'+i">止盈: {{ r }}</li>
                        </ul>
                        <ul v-if="parsePrinciples(row.extractedPrinciples).modules[mkey].discipline?.length" style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                          <li v-for="(r, i) in parsePrinciples(row.extractedPrinciples).modules[mkey].discipline" :key="'d'+i">{{ r }}</li>
                        </ul>
                      </template>
                    </div>
                  </template>
                </template>

                <!-- v1 旧格式兼容 -->
                <template v-else>
                  <div v-if="parsePrinciples(row.extractedPrinciples).entryRules?.length" style="margin-bottom: 12px">
                    <p style="font-weight: bold; margin-bottom: 8px">进场规则</p>
                    <el-table :data="parsePrinciples(row.extractedPrinciples).entryRules" size="small" border>
                      <el-table-column prop="pattern" label="模式" width="150" />
                      <el-table-column prop="condition" label="条件" />
                      <el-table-column prop="action" label="操作" width="200" />
                    </el-table>
                  </div>
                  <div v-if="parsePrinciples(row.extractedPrinciples).exitRules?.length" style="margin-bottom: 12px">
                    <p style="font-weight: bold; margin-bottom: 8px">出场规则</p>
                    <el-table :data="parsePrinciples(row.extractedPrinciples).exitRules" size="small" border>
                      <el-table-column prop="pattern" label="模式" width="150" />
                      <el-table-column prop="condition" label="条件" />
                      <el-table-column prop="action" label="操作" width="200" />
                    </el-table>
                  </div>
                  <div v-if="parsePrinciples(row.extractedPrinciples).riskManagement?.length" style="margin-bottom: 12px">
                    <p style="font-weight: bold; margin-bottom: 4px">风控规则</p>
                    <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                      <li v-for="(r, i) in parsePrinciples(row.extractedPrinciples).riskManagement" :key="i">{{ r }}</li>
                    </ul>
                  </div>
                  <div v-if="parsePrinciples(row.extractedPrinciples).emotionRules?.length" style="margin-bottom: 12px">
                    <p style="font-weight: bold; margin-bottom: 4px">情绪纪律</p>
                    <ul style="margin: 0; padding-left: 20px; color: #606266; font-size: 13px">
                      <li v-for="(r, i) in parsePrinciples(row.extractedPrinciples).emotionRules" :key="i">{{ r }}</li>
                    </ul>
                  </div>
                </template>

                <div v-if="parsePrinciples(row.extractedPrinciples).keyQuotes?.length" style="margin-bottom: 12px">
                  <p style="font-weight: bold; margin-bottom: 4px">金句摘录</p>
                  <div v-for="(q, i) in parsePrinciples(row.extractedPrinciples).keyQuotes" :key="i" style="padding: 6px 12px; margin-bottom: 4px; background: #f5f7fa; border-left: 3px solid #409eff; color: #606266; font-size: 13px; font-style: italic">
                    {{ q }}
                  </div>
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
        <el-table-column prop="category" label="分类" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.category" size="small" type="info">{{ row.category }}</el-tag>
            <span v-else style="color: #c0c4cc">-</span>
          </template>
        </el-table-column>
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
        <el-table-column label="操作" width="200" align="center">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="row.status === 'completed'" text type="warning" size="small" @click="handleReExtract(row)">重新提取</el-button>
            <el-button v-if="row.status === 'failed'" text type="warning" size="small" @click="handleRetry(row)">重试</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="total > pageSize" style="margin-top: 16px; display: flex; justify-content: flex-end">
        <el-pagination :current-page="currentPage" :page-size="pageSize" :total="total" layout="prev, pager, next" @current-change="handlePageChange" />
      </div>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑交易心得" width="600px">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="作者">
          <el-input v-model="editForm.author" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="editForm.category" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="editForm.content" type="textarea" :rows="10" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEditSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
