<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getLatestRuleReview, getRuleReviewList } from '../api/ruleReview'

const latest = ref(null)
const historyList = ref([])
const loading = ref(false)
const expandedRows = ref([])

let confidenceChart = null
let directionChart = null
let signalChart = null

const alertLevelMap = {
  none: { label: '正常', type: 'success' },
  warn: { label: '警告', type: 'warning' },
  critical: { label: '严重', type: 'danger' },
}

function alertLevelLabel(level) {
  return alertLevelMap[level]?.label || level
}
function alertLevelType(level) {
  return alertLevelMap[level]?.type || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const [latestRes, listRes] = await Promise.all([
      getLatestRuleReview(),
      getRuleReviewList({ days: 30 }),
    ])
    latest.value = latestRes.data
    historyList.value = listRes.data || []
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  if (!latest.value) return
  const stats = latest.value.stats || {}

  // 按置信度胜率
  const confDom = document.getElementById('confidenceChart')
  if (confDom) {
    if (confidenceChart) confidenceChart.dispose()
    confidenceChart = echarts.init(confDom)
    const confData = stats.byConfidence || []
    confidenceChart.setOption({
      tooltip: { trigger: 'axis', formatter: (params) => {
        const d = params[0]
        return `${d.name}<br/>胜率: ${d.value}%<br/>样本量: ${confData[d.dataIndex]?.count || 0}`
      }},
      xAxis: { type: 'category', data: confData.map(d => d.label || d.confidence) },
      yAxis: { type: 'value', name: '胜率(%)', min: 0, max: 100 },
      series: [{
        type: 'bar',
        data: confData.map(d => d.winRate),
        itemStyle: {
          color: (params) => {
            const v = params.value
            if (v >= 60) return '#67c23a'
            if (v >= 40) return '#e6a23c'
            return '#f56c6c'
          }
        },
        label: { show: true, position: 'top', formatter: '{c}%' },
      }],
    })
  }

  // 按预测方向胜率
  const dirDom = document.getElementById('directionChart')
  if (dirDom) {
    if (directionChart) directionChart.dispose()
    directionChart = echarts.init(dirDom)
    const dirData = stats.byDirection || []
    const dirLabelMap = { bullish: '看多', bearish: '看空', neutral: '中性' }
    directionChart.setOption({
      tooltip: { trigger: 'axis', formatter: (params) => {
        const d = params[0]
        return `${d.name}<br/>胜率: ${d.value}%<br/>样本量: ${dirData[d.dataIndex]?.count || 0}`
      }},
      xAxis: { type: 'category', data: dirData.map(d => dirLabelMap[d.direction] || d.direction) },
      yAxis: { type: 'value', name: '胜率(%)', min: 0, max: 100 },
      series: [{
        type: 'bar',
        data: dirData.map(d => d.winRate),
        itemStyle: {
          color: (params) => {
            const v = params.value
            if (v >= 60) return '#67c23a'
            if (v >= 40) return '#e6a23c'
            return '#f56c6c'
          }
        },
        label: { show: true, position: 'top', formatter: '{c}%' },
      }],
    })
  }

  // 按信号类型胜率
  const sigDom = document.getElementById('signalChart')
  if (sigDom) {
    if (signalChart) signalChart.dispose()
    signalChart = echarts.init(sigDom)
    const sigData = stats.bySignalType || []
    signalChart.setOption({
      tooltip: { trigger: 'axis', formatter: (params) => {
        const d = params[0]
        return `${d.name}<br/>胜率: ${d.value}%<br/>样本量: ${sigData[d.dataIndex]?.count || 0}`
      }},
      xAxis: {
        type: 'category',
        data: sigData.map(d => d.label || d.signalType),
        axisLabel: { rotate: 20, fontSize: 11 }
      },
      yAxis: { type: 'value', name: '胜率(%)', min: 0, max: 100 },
      series: [{
        type: 'bar',
        data: sigData.map(d => d.winRate),
        itemStyle: {
          color: (params) => {
            const v = params.value
            if (v >= 60) return '#67c23a'
            if (v >= 40) return '#e6a23c'
            return '#f56c6c'
          }
        },
        label: { show: true, position: 'top', formatter: '{c}%' },
      }],
    })
  }
}

function toggleExpand(row) {
  const idx = expandedRows.value.indexOf(row.id)
  if (idx >= 0) {
    expandedRows.value.splice(idx, 1)
  } else {
    expandedRows.value.push(row.id)
  }
}

function isExpanded(row) {
  return expandedRows.value.includes(row.id)
}

function formatAnomalies(anomalies) {
  if (!anomalies) return []
  if (Array.isArray(anomalies)) return anomalies
  if (typeof anomalies === 'string') {
    try { return JSON.parse(anomalies) } catch { return [anomalies] }
  }
  return []
}

function formatSuggestions(suggestions) {
  if (!suggestions) return []
  if (Array.isArray(suggestions)) return suggestions
  if (typeof suggestions === 'string') {
    try { return JSON.parse(suggestions) } catch { return [suggestions] }
  }
  return []
}

function shortText(text, maxLen = 60) {
  if (!text) return '-'
  if (typeof text === 'object') text = JSON.stringify(text)
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

onMounted(loadData)
</script>

<template>
  <div v-loading="loading">
    <!-- 顶部操作栏 -->
    <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center">
      <span style="font-size: 15px; color: #606266">最近 30 天规则复盘</span>
      <el-button type="primary" :loading="loading" @click="loadData">刷新</el-button>
    </div>

    <!-- 最新复盘统计卡片 -->
    <template v-if="latest">
      <el-row :gutter="16" style="margin-bottom: 20px">
        <el-col :span="6">
          <el-card shadow="never">
            <div style="font-size:13px;color:#909399">整体胜率</div>
            <div style="font-size:32px;font-weight:bold;"
              :style="{ color: (latest.overall_win_rate >= 0.6) ? '#67c23a' : (latest.overall_win_rate >= 0.4 ? '#e6a23c' : '#f56c6c') }">
              {{ latest.overall_win_rate !== null && latest.overall_win_rate !== undefined
                ? (latest.overall_win_rate * 100).toFixed(1) + '%'
                : '-' }}
            </div>
            <div style="font-size:12px;color:#c0c4cc;margin-top:4px">{{ latest.review_date }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never">
            <div style="font-size:13px;color:#909399">样本量</div>
            <div style="font-size:32px;font-weight:bold;color:#303133">
              {{ latest.sample_count ?? '-' }}
            </div>
            <div style="font-size:12px;color:#c0c4cc;margin-top:4px">有效预测数</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never">
            <div style="font-size:13px;color:#909399">告警等级</div>
            <div style="font-size:28px;font-weight:bold;margin-top:4px">
              <el-tag :type="alertLevelType(latest.alert_level)" size="large" style="font-size:16px">
                {{ alertLevelLabel(latest.alert_level) }}
              </el-tag>
            </div>
            <div style="font-size:12px;color:#c0c4cc;margin-top:6px">none=正常 / warn=警告 / critical=严重</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never">
            <div style="font-size:13px;color:#909399">主要异常</div>
            <div style="font-size:13px;color:#303133;margin-top:8px;line-height:1.6">
              <template v-if="formatAnomalies(latest.anomalies).length">
                <div v-for="(a, i) in formatAnomalies(latest.anomalies).slice(0, 2)" :key="i"
                  style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                  · {{ typeof a === 'object' ? (a.desc || a.message || JSON.stringify(a)) : a }}
                </div>
                <div v-if="formatAnomalies(latest.anomalies).length > 2" style="color:#909399">
                  +{{ formatAnomalies(latest.anomalies).length - 2 }} 条...
                </div>
              </template>
              <span v-else style="color:#909399">无</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 三个柱状图并排 -->
      <el-row :gutter="16" style="margin-bottom: 20px">
        <el-col :span="8">
          <el-card shadow="never" header="按置信度胜率">
            <div id="confidenceChart" style="height: 240px" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="never" header="按预测方向胜率">
            <div id="directionChart" style="height: 240px" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="never" header="按信号类型胜率">
            <div id="signalChart" style="height: 240px" />
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-empty v-else-if="!loading" description="暂无复盘数据" style="margin-bottom: 20px" />

    <!-- 历史复盘列表 -->
    <el-card shadow="never" header="历史复盘（近30天）">
      <el-table :data="historyList" size="small" row-key="id" style="width:100%">
        <el-table-column prop="review_date" label="日期" width="110" sortable />
        <el-table-column label="胜率" width="90">
          <template #default="{ row }">
            <span :style="{ color: row.overall_win_rate >= 0.6 ? '#67c23a' : row.overall_win_rate >= 0.4 ? '#e6a23c' : '#f56c6c', fontWeight: 600 }">
              {{ row.overall_win_rate !== null && row.overall_win_rate !== undefined
                ? (row.overall_win_rate * 100).toFixed(1) + '%'
                : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="样本量" width="80" prop="sample_count" />
        <el-table-column label="告警等级" width="100">
          <template #default="{ row }">
            <el-tag :type="alertLevelType(row.alert_level)" size="small">
              {{ alertLevelLabel(row.alert_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="主要异常" min-width="200">
          <template #default="{ row }">
            <span style="color:#606266">
              {{ shortText(
                formatAnomalies(row.anomalies).map(a => typeof a === 'object' ? (a.desc || a.message || JSON.stringify(a)) : a).join(' / ')
              ) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="建议摘要" min-width="200">
          <template #default="{ row }">
            <span style="color:#606266">
              {{ shortText(
                formatSuggestions(row.suggestions).map(s => typeof s === 'object' ? (s.text || s.content || JSON.stringify(s)) : s).join(' / ')
              ) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="toggleExpand(row)">
              {{ isExpanded(row) ? '收起' : '详情' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 展开详情区 -->
      <template v-for="row in historyList" :key="'expand-' + row.id">
        <div v-if="isExpanded(row)"
          style="background:#f5f7fa;border:1px solid #ebeef5;border-radius:4px;padding:16px;margin-top:8px">
          <el-row :gutter="16">
            <el-col :span="12">
              <div style="font-weight:600;margin-bottom:8px;color:#303133">异常详情</div>
              <div v-if="formatAnomalies(row.anomalies).length">
                <div v-for="(a, i) in formatAnomalies(row.anomalies)" :key="i"
                  style="padding:6px 0;border-bottom:1px solid #ebeef5;color:#606266;font-size:13px">
                  {{ i + 1 }}. {{ typeof a === 'object' ? (a.desc || a.message || JSON.stringify(a)) : a }}
                </div>
              </div>
              <el-empty v-else :image-size="40" description="无异常" />
            </el-col>
            <el-col :span="12">
              <div style="font-weight:600;margin-bottom:8px;color:#303133">优化建议</div>
              <div v-if="formatSuggestions(row.suggestions).length">
                <div v-for="(s, i) in formatSuggestions(row.suggestions)" :key="i"
                  style="padding:6px 0;border-bottom:1px solid #ebeef5;color:#606266;font-size:13px">
                  {{ i + 1 }}. {{ typeof s === 'object' ? (s.text || s.content || JSON.stringify(s)) : s }}
                </div>
              </div>
              <el-empty v-else :image-size="40" description="无建议" />
            </el-col>
          </el-row>
        </div>
      </template>
    </el-card>
  </div>
</template>

<style scoped>
</style>
