<script setup>
const props = defineProps({
  type: { type: String, required: true },
})

const typeMap = {
  approaching: { label: '接近前高', color: '#e6a23c' },
  breakout: { label: '突破前高', color: '#67c23a' },
  failed: { label: '突破失败', color: '#f56c6c' },
  // 旧类型兼容
  breakout_confirm: { label: '突破确认', color: '#409eff' },
  false_breakout: { label: '假突破', color: '#f56c6c' },
  breakdown: { label: '突破失败下跌', color: '#909399' },
  active: { label: '有效', color: '#67c23a' },
  broken: { label: '已突破', color: '#409eff' },
  expired: { label: '已过期', color: '#909399' },
}

const info = typeMap[props.type] || { label: props.type, color: '#909399' }
</script>

<template>
  <el-tag :color="info.color" effect="dark" size="small" style="border: none">
    {{ info.label }}
  </el-tag>
</template>
