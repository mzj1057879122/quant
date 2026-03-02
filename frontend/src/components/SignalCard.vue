<script setup>
import StatusBadge from './StatusBadge.vue'

defineProps({
  signal: { type: Object, required: true },
})

defineEmits(['click'])
</script>

<template>
  <el-card shadow="hover" style="margin-bottom: 12px; cursor: pointer" @click="$emit('click', signal)">
    <div style="display: flex; align-items: center; justify-content: space-between">
      <div style="display: flex; align-items: center; gap: 12px">
        <StatusBadge :type="signal.signalType" />
        <span style="font-weight: 500">{{ signal.stockCode }} {{ signal.stockName }}</span>
      </div>
      <div style="color: #909399; font-size: 13px">
        {{ signal.signalDate }}
      </div>
    </div>
    <div style="margin-top: 8px; color: #606266; font-size: 14px">
      {{ signal.description }}
    </div>
    <div style="margin-top: 8px; display: flex; gap: 24px; font-size: 13px; color: #909399">
      <span>前高: {{ signal.previousHighPrice }}</span>
      <span>收盘: {{ signal.closePrice }}</span>
      <span v-if="signal.successRate != null" :style="{ color: signal.successRate >= 50 ? '#67c23a' : '#f56c6c' }">
        成功率: {{ signal.successRate }}%
      </span>
    </div>
  </el-card>
</template>
