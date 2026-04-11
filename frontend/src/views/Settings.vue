<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAllConfigs, updateConfig } from '../api/userConfig'
import { runTask, getTaskStatus } from '../api/system'
import { getStrategyRules, updateStrategyRule } from '../api/strategy'

const loading = ref(false)
const configs = ref({})
const taskJobs = ref([])
const taskLoading = ref({})

// 检测参数
const detectionParams = ref({
  lookbackDays: 120,
  windowSize: 5,
  minGap: 10,
  minDropPct: 0.03,
  approachPct: 0.95,
  confirmDays: 3,
  falseBreakdownPct: 0.03,
  breakoutTolerance: 0.005,
})

// 推送配置
const notifyEnabled = ref(true)
const serverChanKey = ref('')
const notifyTypes = ref(['approaching', 'breakout', 'false_breakout', 'breakdown'])

const allSignalTypes = [
  { value: 'approaching', label: '接近前高' },
  { value: 'breakout', label: '突破前高' },
  { value: 'breakout_confirm', label: '突破确认' },
  { value: 'false_breakout', label: '假突破' },
  { value: 'breakdown', label: '突破失败下跌' },
]

async function loadConfigs() {
  loading.value = true
  try {
    const [configRes, taskRes] = await Promise.all([
      getAllConfigs(),
      getTaskStatus().catch(() => ({ jobs: [] })),
    ])

    taskJobs.value = taskRes.jobs || []

    const items = configRes.items || []
    for (const item of items) {
      configs.value[item.configKey] = item.configValue
    }

    // 解析各项配置
    if (configs.value.detection_params) {
      try {
        detectionParams.value = { ...detectionParams.value, ...JSON.parse(configs.value.detection_params) }
      } catch { /* 使用默认值 */ }
    }
    if (configs.value.notify_enabled !== undefined) {
      try {
        notifyEnabled.value = JSON.parse(configs.value.notify_enabled)
      } catch { /* 使用默认值 */ }
    }
    if (configs.value.server_chan_key) {
      try {
        serverChanKey.value = JSON.parse(configs.value.server_chan_key) || ''
      } catch {
        serverChanKey.value = configs.value.server_chan_key
      }
    }
    if (configs.value.notify_types) {
      try {
        notifyTypes.value = JSON.parse(configs.value.notify_types)
      } catch { /* 使用默认值 */ }
    }
  } catch (e) {
    // 静默
  } finally {
    loading.value = false
  }
}

async function saveDetectionParams() {
  try {
    await updateConfig('detection_params', JSON.stringify(detectionParams.value))
    ElMessage.success('检测参数已保存')
  } catch (e) {
    // 静默
  }
}

async function saveNotifyConfig() {
  try {
    await Promise.all([
      updateConfig('notify_enabled', JSON.stringify(notifyEnabled.value)),
      updateConfig('server_chan_key', JSON.stringify(serverChanKey.value)),
      updateConfig('notify_types', JSON.stringify(notifyTypes.value)),
    ])
    ElMessage.success('推送配置已保存')
  } catch (e) {
    // 静默
  }
}

async function handleRunTask(taskName) {
  taskLoading.value[taskName] = true
  try {
    await runTask(taskName)
    ElMessage.success(`任务 ${taskName} 执行完成`)
  } catch (e) {
    // 静默
  } finally {
    taskLoading.value[taskName] = false
  }
}

async function handleTestNotify() {
  taskLoading.value.test = true
  try {
    await runTask('send_notifications')
    ElMessage.success('测试推送已发送')
  } catch (e) {
    // 静默
  } finally {
    taskLoading.value.test = false
  }
}

// 策略规则管理
const strategyRules = ref([])
const strategyLoading = ref(false)
const editDialogVisible = ref(false)
const editingRule = ref(null)
const editingValue = ref(0)
const editSubmitting = ref(false)

async function loadStrategyRules() {
  strategyLoading.value = true
  try {
    const res = await getStrategyRules()
    strategyRules.value = res.items || []
  } catch (e) {
    // 静默
  } finally {
    strategyLoading.value = false
  }
}

function openEditDialog(rule) {
  editingRule.value = rule
  editingValue.value = rule.ruleValue
  editDialogVisible.value = true
}

async function submitRuleEdit() {
  if (!editingRule.value) return
  editSubmitting.value = true
  try {
    await updateStrategyRule(editingRule.value.ruleKey, editingValue.value)
    ElMessage.success('规则已更新，下次预测时生效')
    editDialogVisible.value = false
    await loadStrategyRules()
  } catch (e) {
    ElMessage.error('更新失败')
  } finally {
    editSubmitting.value = false
  }
}

function formatDate(val) {
  if (!val) return '-'
  return val.replace('T', ' ').substring(0, 19)
}

onMounted(() => {
  loadConfigs()
  loadStrategyRules()
})
</script>

<template>
  <div v-loading="loading">
    <el-row :gutter="20">
      <!-- 检测参数 -->
      <el-col :span="12">
        <el-card style="margin-bottom: 20px">
          <template #header>
            <span style="font-weight: 500">检测算法参数</span>
          </template>
          <el-form label-width="140px" size="default">
            <el-form-item label="回溯天数">
              <el-input-number v-model="detectionParams.lookbackDays" :min="30" :max="500" :step="10" />
            </el-form-item>
            <el-form-item label="滑动窗口大小">
              <el-input-number v-model="detectionParams.windowSize" :min="2" :max="20" />
            </el-form-item>
            <el-form-item label="高点最小间距">
              <el-input-number v-model="detectionParams.minGap" :min="3" :max="50" />
            </el-form-item>
            <el-form-item label="最小回撤幅度">
              <el-input-number v-model="detectionParams.minDropPct" :min="0.01" :max="0.2" :step="0.01" :precision="2" />
            </el-form-item>
            <el-form-item label="接近前高阈值">
              <el-input-number v-model="detectionParams.approachPct" :min="0.8" :max="0.99" :step="0.01" :precision="2" />
            </el-form-item>
            <el-form-item label="突破确认天数">
              <el-input-number v-model="detectionParams.confirmDays" :min="1" :max="10" />
            </el-form-item>
            <el-form-item label="假突破下跌幅度">
              <el-input-number v-model="detectionParams.falseBreakdownPct" :min="0.01" :max="0.2" :step="0.01" :precision="2" />
            </el-form-item>
            <el-form-item label="突破容差">
              <el-input-number v-model="detectionParams.breakoutTolerance" :min="0" :max="0.05" :step="0.001" :precision="3" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveDetectionParams">保存参数</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 推送配置 -->
      <el-col :span="12">
        <el-card style="margin-bottom: 20px">
          <template #header>
            <span style="font-weight: 500">微信推送配置</span>
          </template>
          <el-form label-width="140px" size="default">
            <el-form-item label="开启推送">
              <el-switch v-model="notifyEnabled" />
            </el-form-item>
            <el-form-item label="Server酱 Key">
              <el-input v-model="serverChanKey" placeholder="请输入SendKey" show-password />
            </el-form-item>
            <el-form-item label="推送信号类型">
              <el-checkbox-group v-model="notifyTypes">
                <el-checkbox
                  v-for="t in allSignalTypes"
                  :key="t.value"
                  :value="t.value"
                  :label="t.label"
                />
              </el-checkbox-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveNotifyConfig">保存配置</el-button>
              <el-button :loading="taskLoading.test" @click="handleTestNotify">测试推送</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 手动任务 -->
        <el-card>
          <template #header>
            <span style="font-weight: 500">手动操作</span>
          </template>
          <div style="display: flex; flex-direction: column; gap: 12px">
            <el-button
              :loading="taskLoading.fetch_quotes"
              style="width: 100%"
              @click="handleRunTask('fetch_quotes')"
            >
              <el-icon><Download /></el-icon> 拉取行情数据
            </el-button>
            <el-button
              :loading="taskLoading.detect_signals"
              style="width: 100%"
              @click="handleRunTask('detect_signals')"
            >
              <el-icon><Cpu /></el-icon> 执行信号检测
            </el-button>
            <el-button
              :loading="taskLoading.send_notifications"
              style="width: 100%"
              @click="handleRunTask('send_notifications')"
            >
              <el-icon><ChatDotRound /></el-icon> 发送推送通知
            </el-button>
          </div>

          <!-- 定时任务状态 -->
          <div v-if="taskJobs.length > 0" style="margin-top: 20px">
            <el-divider content-position="left">定时任务状态</el-divider>
            <div v-for="job in taskJobs" :key="job.id" style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px">
              <span>{{ job.name }}</span>
              <span style="color: #909399">{{ job.nextRunTime || '未调度' }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 策略规则管理 -->
    <el-card v-loading="strategyLoading" style="margin-top: 20px">
      <template #header>
        <span style="font-weight: 500">策略规则管理</span>
      </template>
      <el-table :data="strategyRules" border size="small" style="width: 100%">
        <el-table-column prop="ruleKey" label="规则名" min-width="180" />
        <el-table-column prop="ruleDesc" label="说明" min-width="220" show-overflow-tooltip />
        <el-table-column prop="ruleValue" label="当前值" width="110" align="right">
          <template #default="{ row }">
            <span style="font-weight: 500">{{ row.ruleValue }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="130" />
        <el-table-column label="最后更新" width="160">
          <template #default="{ row }">
            {{ formatDate(row.updatedAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEditDialog(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑规则弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑规则" width="420px" :close-on-click-modal="false">
      <template v-if="editingRule">
        <el-descriptions :column="1" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="规则名">{{ editingRule.ruleKey }}</el-descriptions-item>
          <el-descriptions-item label="说明">{{ editingRule.ruleDesc }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ editingRule.category }}</el-descriptions-item>
        </el-descriptions>
        <el-form label-width="80px">
          <el-form-item label="数值">
            <el-input-number v-model="editingValue" :precision="4" :step="0.01" style="width: 200px" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="submitRuleEdit">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>
