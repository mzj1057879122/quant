import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '仪表盘' },
  },
  {
    path: '/stocks',
    name: 'StockList',
    component: () => import('../views/StockList.vue'),
    meta: { title: '股票列表' },
  },
  {
    path: '/stocks/:code',
    name: 'StockDetail',
    component: () => import('../views/StockDetail.vue'),
    meta: { title: '个股详情' },
  },
  {
    path: '/signals',
    name: 'SignalList',
    component: () => import('../views/SignalList.vue'),
    meta: { title: '突破信号' },
  },
  {
    path: '/strong',
    name: 'StrongStock',
    component: () => import('../views/StrongStock.vue'),
    meta: { title: '强势股' },
  },
  {
    path: '/watchlist',
    name: 'WatchlistPool',
    component: () => import('../views/WatchlistPool.vue'),
    meta: { title: '自选股池' },
  },
  {
    path: '/prediction',
    name: 'PredictionBoard',
    component: () => import('../views/PredictionBoard.vue'),
    meta: { title: '预测看板' },
  },
  {
    path: '/daily-prediction',
    name: 'DailyPrediction',
    component: () => import('../views/DailyPrediction.vue'),
    meta: { title: '今日预测' },
  },
  {
    path: '/brief',
    name: 'MorningBrief',
    component: () => import('../views/MorningBrief.vue'),
    meta: { title: '盘前纪要' },
  },
  {
    path: '/knowledge',
    name: 'ArticleKnowledge',
    component: () => import('../views/ArticleKnowledge.vue'),
    meta: { title: '知识学习' },
  },
  {
    path: '/trading',
    name: 'TradingKnowledge',
    component: () => import('../views/TradingKnowledge.vue'),
    meta: { title: '交易框架' },
  },
  {
    path: '/cases',
    name: 'CaseStudy',
    component: () => import('../views/CaseStudy.vue'),
    meta: { title: '案例分析' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { title: '系统设置' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '量化监控'} - 量化股票监控系统`
  next()
})

export default router
