# 交易框架系统 JSON 结构 — 版本归档

## 版本信息
- **版本**: v1（扁平结构，已废弃）
- **日期**: 2026-03-01
- **状态**: 废弃，由 v2（7模块结构）替代

---

## v1 方案：扁平 JSON 结构

### 提取原则格式（extractedPrinciples）
```json
{
  "tradingStyle": "短线/波段/趋势/综合",
  "corePrinciples": ["核心原则"],
  "entryRules": [
    {"pattern": "进场模式", "condition": "触发条件", "action": "具体操作"}
  ],
  "exitRules": [
    {"pattern": "出场模式", "condition": "触发条件", "action": "具体操作"}
  ],
  "riskManagement": ["风控规则"],
  "emotionRules": ["情绪纪律"],
  "sectorInsights": [{"sector": "板块", "logic": "板块逻辑"}],
  "keyQuotes": ["金句"]
}
```

### 框架格式（frameworkContent）
```json
{
  "tradingPhilosophy": "核心交易哲学",
  "marketAnalysis": {
    "emotionCycle": "情绪周期判断方法",
    "mainLineLogic": "主线识别方法"
  },
  "entrySystem": [
    {"pattern": "进场模式", "condition": "触发条件", "action": "具体操作", "source": "来自谁"}
  ],
  "exitSystem": [
    {"pattern": "出场模式", "condition": "触发条件", "action": "具体操作", "source": "来自谁"}
  ],
  "positionManagement": ["仓位管理规则"],
  "riskControl": ["风控规则"],
  "emotionDiscipline": ["情绪纪律"]
}
```

### 暴露的问题

1. **结构过于扁平**：entrySystem/exitSystem 只是列表，无法区分"K线形态买入"和"涨停战法买入"等不同维度
2. **没有市况分级**：无法表达"强势市做什么、弱势市做什么"的分级决策
3. **没有量化阈值**：规则描述偏定性，缺少可执行的量化条件
4. **无法承载系统性知识**：如《股票短线交易的24堂精品课》级别的多层级内容，用扁平列表无法组织
5. **模块边界模糊**：进场/出场混在一起，实际交易中"大盘判断→板块筛选→个股择时"是有决策链的

---

## v2 方案：7 模块层级结构

### 设计思路
按交易决策链组织 7 个模块，每个模块有明确的 purpose 和结构化子字段，支持市况分级和量化阈值。

### 决策链
`大盘判断 → 板块筛选 → 资金行为 → K线形态 → 涨停战法 → 分时技法 → 风控管理`

### 提取原则格式（extractedPrinciples v2）
- 顶层保留 `tradingStyle`、`corePrinciples`、`keyQuotes`
- 新增 `modules` 对象，含 7 个模块 key
- 简单心得大部分模块为空对象 `{}`，只填有内容的模块
- 7 个模块：marketAssessment / sectorScreening / capitalFlow / patterns / tactics / intradayTiming / riskManagement

### 框架格式（frameworkContent v2）
- 顶层保留 `tradingPhilosophy`
- 新增 `decisionChain` 数组（决策链顺序）
- `modules` 对象中每个模块含 `name`、`purpose` 和结构化规则字段

### 兼容性处理
- **DB 表结构不变**：`frameworkContent` 和 `extractedPrinciples` 仍为 Text 存 JSON
- **后端合成 prompt**：检测 `principles.get("modules")` 区分新旧格式，旧格式走 `_summarizePrinciplesV1()` 兼容摘要
- **前端渲染**：`isV2Framework()` / `isV2Principles()` 判断格式，新格式用 el-collapse 7模块布局，旧格式保留原渲染逻辑

### 文件变更清单
- 修改：`backend/app/services/knowledge_service.py`（重写 `buildExtractPrompt` + `buildFrameworkPrompt`，新增 `_summarizePrinciplesV1` + `_summarizePrinciplesV2`）
- 修改：`frontend/src/views/TradingKnowledge.vue`（框架展示改 el-collapse 7模块，提取结果按模块渲染，新旧格式双路径兼容）
- 不变：DB 模型、schemas、API、router
