<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  quotes: { type: Array, default: () => [] },
  previousHighs: { type: Array, default: () => [] },
  signals: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chartInstance = null

function renderChart() {
  if (!chartRef.value || !props.quotes.length) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  // 按日期升序排列
  const sortedQuotes = [...props.quotes].sort((a, b) => new Date(a.tradeDate) - new Date(b.tradeDate))

  const dates = sortedQuotes.map(q => q.tradeDate)
  const ohlc = sortedQuotes.map(q => [
    parseFloat(q.openPrice),
    parseFloat(q.closePrice),
    parseFloat(q.lowPrice),
    parseFloat(q.highPrice),
  ])
  const volumes = sortedQuotes.map(q => q.volume)

  // 前高标注线
  const markLines = props.previousHighs
    .filter(ph => ph.status === 'active')
    .map(ph => ({
      yAxis: parseFloat(ph.highPrice),
      name: `前高 ${ph.highDate}`,
      label: {
        formatter: `前高 ${parseFloat(ph.highPrice)}`,
        position: 'end',
      },
      lineStyle: {
        color: '#f56c6c',
        type: 'dashed',
        width: 2,
      },
    }))

  // 信号标记点
  const markPoints = props.signals.map(s => {
    const colorMap = {
      approaching: '#e6a23c',
      breakout: '#67c23a',
      failed: '#f56c6c',
      // 旧类型兼容
      breakout_confirm: '#409eff',
      false_breakout: '#f56c6c',
      breakdown: '#909399',
    }
    const symbolMap = {
      approaching: 'triangle',
      breakout: 'arrow',
      failed: 'pin',
      // 旧类型兼容
      breakout_confirm: 'diamond',
      false_breakout: 'pin',
      breakdown: 'pin',
    }
    return {
      coord: [s.signalDate, parseFloat(s.triggerPrice)],
      value: s.signalType,
      itemStyle: { color: colorMap[s.signalType] || '#409eff' },
      symbol: symbolMap[s.signalType] || 'circle',
      symbolSize: 12,
    }
  })

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    grid: [
      { left: '8%', right: '4%', top: '8%', height: '55%' },
      { left: '8%', right: '4%', top: '70%', height: '20%' },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        gridIndex: 0,
        axisLabel: { show: false },
      },
      {
        type: 'category',
        data: dates,
        gridIndex: 1,
        axisLabel: { fontSize: 10 },
      },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitLine: { lineStyle: { color: '#f0f0f0' } } },
      { scale: true, gridIndex: 1, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], start: 60, end: 100, top: '94%' },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a',
        },
        markLine: {
          symbol: 'none',
          data: markLines,
        },
        markPoint: {
          data: markPoints,
          label: { show: false },
        },
      },
      {
        name: '成交量',
        type: 'bar',
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: {
          color: (params) => {
            const idx = params.dataIndex
            return ohlc[idx][1] >= ohlc[idx][0] ? '#ef5350' : '#26a69a'
          },
        },
      },
    ],
  }

  chartInstance.setOption(option, true)
}

function handleResize() {
  chartInstance?.resize()
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', handleResize)
})

watch(() => [props.quotes, props.previousHighs, props.signals], renderChart, { deep: true })

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<template>
  <div ref="chartRef" style="width: 100%; height: 500px"></div>
</template>
