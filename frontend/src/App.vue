<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSignalStore } from './stores/signal'

const router = useRouter()
const route = useRoute()
const signalStore = useSignalStore()
const isCollapse = ref(false)

const knowledgePaths = ['/knowledge', '/trading', '/cases']
const knowledgeSubMenuOpen = computed(() => knowledgePaths.includes(route.path))

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
        :default-openeds="knowledgeSubMenuOpen ? ['knowledge-sub'] : []"
        :collapse="isCollapse"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        :collapse-transition="false"
        @select="handleMenuSelect"
      >
        <el-menu-item index="/">
          <el-icon><Odometer /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>

        <el-menu-item index="/watchlist">
          <el-icon><Star /></el-icon>
          <template #title>自选股池</template>
        </el-menu-item>

        <el-menu-item index="/prediction">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>预测看板</template>
        </el-menu-item>

        <el-menu-item index="/daily-prediction">
          <el-icon><TrendCharts /></el-icon>
          <template #title>今日预测</template>
        </el-menu-item>

        <el-menu-item index="/signals">
          <el-icon><Bell /></el-icon>
          <template #title>
            <span>突破信号</span>
            <el-badge
              v-if="signalStore.unreadCount > 0"
              :value="signalStore.unreadCount"
              :max="99"
              style="margin-left: 8px"
            />
          </template>
        </el-menu-item>

        <el-menu-item index="/strong">
          <el-icon><Promotion /></el-icon>
          <template #title>强势股</template>
        </el-menu-item>

        <el-menu-item index="/brief">
          <el-icon><Document /></el-icon>
          <template #title>盘前纪要</template>
        </el-menu-item>

        <el-sub-menu index="knowledge-sub">
          <template #title>
            <el-icon><Reading /></el-icon>
            <span>知识库</span>
          </template>
          <el-menu-item index="/knowledge">
            <el-icon><Memo /></el-icon>
            <template #title>文章学习</template>
          </el-menu-item>
          <el-menu-item index="/trading">
            <el-icon><Notebook /></el-icon>
            <template #title>交易框架</template>
          </el-menu-item>
          <el-menu-item index="/cases">
            <el-icon><Collection /></el-icon>
            <template #title>案例库</template>
          </el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/backtest">
          <el-icon><TrendCharts /></el-icon>
          <template #title>回测报告</template>
        </el-menu-item>

        <el-menu-item index="/rule-review">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>规则复盘</template>
        </el-menu-item>

        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>设置</template>
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
