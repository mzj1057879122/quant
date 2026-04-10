<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSignalStore } from './stores/signal'

const router = useRouter()
const route = useRoute()
const signalStore = useSignalStore()
const isCollapse = ref(false)

const menuItems = [
  { index: '/', icon: 'DataAnalysis', title: '仪表盘' },
  { index: '/stocks', icon: 'List', title: '股票列表' },
  { index: '/signals', icon: 'Bell', title: '信号列表' },
  { index: '/strong', icon: 'TrendCharts', title: '强势股' },
  { index: '/knowledge', icon: 'Reading', title: '知识学习' },
  { index: '/trading', icon: 'Notebook', title: '交易框架' },
  { index: '/cases', icon: 'Collection', title: '案例分析' },
  { index: '/settings', icon: 'Setting', title: '系统设置' },
]

function handleMenuSelect(index) {
  router.push(index)
}

onMounted(() => {
  signalStore.fetchUnreadCount()
})
</script>

<template>
  <el-container style="min-height: 100vh">
    <el-aside :width="isCollapse ? '64px' : '200px'" style="background-color: #304156; transition: width 0.3s">
      <div style="height: 60px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 16px; font-weight: bold; white-space: nowrap; overflow: hidden">
        <el-icon size="24" style="margin-right: 8px"><TrendCharts /></el-icon>
        <span v-show="!isCollapse">量化监控</span>
      </div>
      <el-menu
        :default-active="route.path"
        :collapse="isCollapse"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        :collapse-transition="false"
        @select="handleMenuSelect"
      >
        <el-menu-item v-for="item in menuItems" :key="item.index" :index="item.index">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>
            <span>{{ item.title }}</span>
            <el-badge
              v-if="item.index === '/signals' && signalStore.unreadCount > 0"
              :value="signalStore.unreadCount"
              :max="99"
              style="margin-left: 8px"
            />
          </template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header style="background: #fff; display: flex; align-items: center; box-shadow: 0 1px 4px rgba(0,0,0,0.08); padding: 0 20px">
        <el-icon size="20" style="cursor: pointer" @click="isCollapse = !isCollapse">
          <Fold v-if="!isCollapse" />
          <Expand v-else />
        </el-icon>
        <span style="margin-left: 16px; font-size: 18px; font-weight: 500">{{ route.meta.title || '量化股票监控系统' }}</span>
      </el-header>

      <el-main style="padding: 20px; background: #f5f7fa">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
