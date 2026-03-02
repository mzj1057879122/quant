# 知识学习系统 — 版本归档

## 版本信息
- **版本**: v1（初版，已废弃）
- **日期**: 2026-02-28
- **状态**: 废弃，由 v2 替代

---

## v1 方案：知识文件读写模式

### 设计思路
用户粘贴文章 → 后端调用 Claude CLI → Claude 读取6个知识记忆文件 → 分析对比 → 更新知识文件 → 返回摘要。

### 架构
```
用户提交文章 → 后端存DB → 后台启动 Claude CLI(opus) → Claude读取/更新知识文件 → 返回摘要
                              ↓                                           ↓
                         前端轮询状态(3s) ←←←←←←←←←←←←←←←←←←← 更新DB状态+结果
```

### 知识文件
存储路径：`/home/zejianma/.claude/projects/-home-zejianma-quant/memory/`
- `MEMORY.md` — 索引 + 文章计数
- `trading/strategy.md` — 核心策略框架
- `trading/sectors.md` — 板块认知
- `trading/patterns.md` — 规律模式
- `trading/logic_archive.md` — 逻辑演变
- `trading/lessons.md` — 经验教训

### Claude CLI 调用方式
```python
claude -p "{巨大prompt}" --model opus
# prompt 包含文章全文 + 6步处理指令
# Claude 自己读6个文件 → 分析 → 写回文件 → 输出摘要
```

### 暴露的问题

#### 1. 性能致命缺陷
- **opus 模型太慢**：每次工具调用（读/写文件）几十秒，6个文件读+写 = 十几次工具调用
- **超时严重**：300秒超时仍然不够，实际需要5分钟以上
- **尝试的优化**：改 sonnet + Python预读文件 + 让Claude输出JSON + Python写文件 → 仍然因为输出完整文件内容的JSON太大导致耗时过长（141秒）

#### 2. 设计逻辑缺陷
- **单篇更新知识库没意义**：每篇文章都去改一堆知识文件，文件越来越大，后续处理越来越慢
- **不支持多作者对比**：一篇一篇独立处理，无法横向对比不同作者观点
- **没有时间维度**：无法关联前几天的策略演变
- **不符合实际使用场景**：用户一天会提交多篇不同作者的文章，需要的是综合分析而非逐篇更新知识库

#### 3. 技术问题记录
- `asyncio.get_event_loop().create_task()` 在 sync 端点的工作线程中报错 → 改为 async 端点
- Claude CLI 检测到 `CLAUDECODE` 环境变量拒绝启动 → 启动子进程时清除该变量
- `-p -` stdin 管道方式在 Python asyncio 中不工作 → 改为 `-p` 参数直接传
- uvicorn 热重载杀掉正在运行的 Claude 进程导致文章卡在 processing → 加了启动时恢复逻辑

### 已实现的代码（保留）
以下代码在 v1 中已实现，v2 中可复用：
- `backend/app/models/article.py` — article 表 ORM（字段：id, title, author, content, source, sourceUrl, articleDate, status, resultSummary, updatedFiles, errorMessage, processDuration, createdAt, updatedAt）
- `backend/app/schemas/article.py` — 请求/响应模型
- `backend/app/api/article.py` — API路由（提交/URL提取/查询/列表/重试/删除）
- `backend/app/services/article_service.py` 中的 `extractFromTgb()` — 淘股吧文章提取（用 `div.article-text.p_coten#first` 定位正文）
- `frontend/src/views/ArticleKnowledge.vue` — 页面框架（URL提交/手动提交/轮询/历史列表）

---

## v2 方案：多作者观点提取 + 每日综合策略

### 设计思路
将"知识文件维护"改为"结构化观点提取 + 每日汇总"，所有结果存DB，不再读写文件。

### 架构
```
文章A(作者1) → 单篇分析(~20s) → 存DB(resultSummary)
文章B(作者2) → 单篇分析(~20s) → 存DB(resultSummary)
文章C(作者3) → 单篇分析(~20s) → 存DB(resultSummary)
                                        ↓
                              用户点击"生成每日汇总"
                                        ↓
              读取当日所有文章分析 + 前2天的每日汇总(daily_summary表)
                                        ↓
                           Claude sonnet 综合分析(~30s)
                                        ↓
                              存入 daily_summary 表
```

### 核心改进
1. **两步分离**：单篇提取（轻量快速） vs 每日汇总（综合深度）
2. **纯分析无IO**：Claude 只做思考输出JSON，文件读写全交给Python，超时从300秒降到60秒
3. **多作者对比**：横向对比同一天不同作者的共识与分歧
4. **时间维度**：纵向关联前2天的策略，跟踪预判验证和情绪演变
5. **结果存DB**：所有分析结果存数据库，前端可展示、可查询、可追溯

### 单篇分析输出结构
```json
{
  "marketView": "作者对大盘/情绪的整体判断",
  "stockViews": [
    {"name": "豫能控股", "code": "001896", "opinion": "看多", "logic": "...", "strategy": "...", "risk": "..."}
  ],
  "sectorViews": [
    {"name": "电力/算力", "opinion": "看多", "logic": "...", "keyStocks": ["豫能控股", "拓维信息"]}
  ],
  "keyPredictions": ["短线风格可能回归...", "钨矿板块处于加速赶顶..."],
  "tradingAdvice": "作者给出的具体操作建议"
}
```

### 每日汇总输出结构
```json
{
  "consensus": "多作者共识要点",
  "divergence": "作者间分歧点",
  "stockViews": [{"name": "豫能控股", "bullCount": 2, "bearCount": 0, "synthesis": "...", "suggestedAction": "..."}],
  "sectorViews": [...],
  "strategy": "明日综合应对策略",
  "evolution": "与前两天策略对比：哪些预判被验证、哪些失效、情绪怎么变"
}
```

### 数据库变更
- `article` 表保留不变
- 新增 `daily_summary` 表（summary_date, article_count, consensus, divergence, stock_views, sector_views, strategy, evolution, raw_output, status, error_message, process_duration, created_at, updated_at）

### 文件变更清单
- 新建：`backend/app/models/daily_summary.py`, `backend/app/schemas/daily_summary.py`
- 重写：`backend/app/services/article_service.py`（单篇prompt + 汇总prompt + 去掉知识文件逻辑）
- 修改：`backend/app/api/article.py`（新增汇总端点）, `frontend/src/views/ArticleKnowledge.vue`（新增汇总区域）
