
# 项目说明

## 项目概述

量化股票监控系统，包含三大模块：
1. **股票监控**：检测股票前高位置，判断是否突破或突破失败后下跌，并给出提醒
2. **知识学习**：提交短线复盘文章，自动提取作者观点，每日汇总生成综合策略
3. **交易框架**：提交交易心得，提取交易原则，合成系统性交易框架，指导每日汇总分析

## 技术栈

- 后端：Python + FastAPI（端口 8072）
- 前端：Vue3 + Element Plus + ECharts + Pinia（端口 8071）
- 数据库：Docker MySQL 8.0（容器名 mysql8，端口 3306，数据库名 quant）
- 数据源：akshare（双数据源：腾讯优先，东方财富备用）
- 推送：Server酱（微信推送）
- 数据库迁移：Alembic

## 启动方式

- 后端：`cd backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8072 --reload`
- 前端：`cd frontend && npm run dev`
- 后端日志：`/tmp/quant-backend.log`
- 公网隧道：`cd script/cloudflared && bash frp.sh start`（首次部署用 `bash setup-ec2.sh`）

## 项目结构

```
quant/
├── backend/
│   ├── main.py                        # FastAPI入口
│   ├── requirements.txt
│   ├── alembic.ini                    # 数据库迁移配置
│   ├── alembic/versions/              # 迁移脚本
│   └── app/
│       ├── config.py                  # 配置
│       ├── database.py                # 数据库连接
│       ├── api/                       # 路由层
│       │   ├── router.py             # 路由汇聚
│       │   ├── stock.py              # 股票接口
│       │   ├── signal.py             # 信号接口（含突破分析API）
│       │   ├── quote.py              # 行情接口
│       │   ├── article.py            # 知识学习接口（文章提交/URL提取/汇总）
│       │   ├── knowledge.py          # 交易框架接口（心得提交/原则提取/框架合成）
│       │   ├── user_config.py        # 用户配置接口
│       │   └── system.py             # 系统接口
│       ├── services/                  # 业务逻辑层
│       │   ├── stock_service.py      # 股票同步与查询
│       │   ├── detection_service.py  # 前高检测引擎（只找最近有效高点+历史突破分析）
│       │   ├── signal_service.py     # 信号管理
│       │   ├── quote_service.py      # 行情数据（双数据源+增量拉取）
│       │   ├── article_service.py    # 知识学习（文章提取/Claude分析/每日汇总）
│       │   ├── knowledge_service.py  # 交易框架（心得处理/原则提取/框架合成）
│       │   ├── config_service.py     # 配置管理
│       │   └── notify_service.py     # Server酱推送
│       ├── models/                    # ORM模型
│       │   ├── stock.py
│       │   ├── daily_quote.py
│       │   ├── previous_high.py
│       │   ├── signal.py             # 含 successRate 字段
│       │   ├── breakout_analysis.py  # 突破分析缓存表
│       │   ├── article.py              # 文章表
│       │   ├── daily_summary.py        # 每日综合策略表
│       │   ├── trading_knowledge.py    # 交易心得表
│       │   ├── trading_framework.py    # 交易框架表（版本化）
│       │   └── user_config.py
│       ├── schemas/                   # Pydantic请求/响应
│       ├── tasks/                     # 定时任务
│       │   ├── scheduler.py          # 任务调度器
│       │   ├── fetch_quotes.py       # 行情获取任务
│       │   └── detect_signals.py     # 信号检测任务
│       └── utils/                     # 工具类
│           ├── logger.py
│           └── date_helper.py
├── version/                               # 版本归档（大改动记录）
│   ├── knowledge-system-v1.md            # 知识学习系统v1→v2演变记录
│   └── trading-framework-v1.md           # 交易框架JSON结构v1→v2演变记录
├── script/
│   └── cloudflared/                       # 公网隧道脚本
│       ├── setup-ec2.sh                  # 首次部署（EC2 frps + 安全组 + frpc）
│       ├── frp.sh                        # 日常启停管理
│       ├── frpc                          # frp 客户端二进制
│       ├── frpc.toml                     # frpc 配置
│       └── proxy.js                      # 本地合并代理
├── deploy.sh                              # 新服务器一键部署
├── run.sh                                 # 本地服务启停
├── env.sh                                 # 公共端口配置
├── frontend/
│   ├── vite.config.js                 # Vite配置（host: 0.0.0.0, allowedHosts: all）
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── api/                       # API调用层
│       ├── router/index.js            # 路由配置
│       ├── stores/                    # Pinia状态管理
│       ├── views/                     # 页面（Dashboard/StockList/StockDetail/SignalList/ArticleKnowledge/TradingKnowledge/Settings）
│       └── components/                # 组件（KLineChart/SignalCard/StatusBadge）
```

### 交易框架系统（knowledge_service.py）

- **数据流**：交易心得 → 提取交易原则(Claude, 60s) → 存DB → 合成交易框架(手动触发, 120s) → 存DB → 注入每日汇总
- **分步处理**：每步 prompt 小而聚焦，避免超时
  - 第1步：单篇心得提取原则 → 7模块结构（modules: marketAssessment/sectorScreening/capitalFlow/patterns/tactics/intradayTiming/riskManagement），空模块输出 `{}`
  - 第2步：所有原则按模块聚合摘要 → 合成7模块框架（decisionChain + modules，每模块含 name/purpose/规则字段）
- **决策链**：大盘判断 → 板块筛选 → 资金行为 → K线形态 → 涨停战法 → 分时技法 → 风控管理
- **兼容旧格式**：后端 `_summarizePrinciplesV1()` 兼容旧提取结果，前端 `isV2Framework()`/`isV2Principles()` 双路径渲染
- **框架注入**：每日汇总时自动获取最新框架，注入到策略汇总 prompt 中
- **版本化**：框架有版本号递增，保留历史版本
- **数据库表**：`trading_knowledge`（交易心得+提取原则）、`trading_framework`（交易框架版本），表结构不变，JSON 内部结构升级
- **版本演变**：v1扁平结构(entryRules/exitRules) → v2七模块层级结构（详见 `version/trading-framework-v1.md`）
```

## API路由前缀

- 所有后端接口前缀：`/api/v1/`
- 前端Vite代理：`/api` -> `http://127.0.0.1:8072`

## 核心业务逻辑

### 前高检测（detection_service.py）

- **前高识别**：只找最近一个有效高点（阻力位），条件：窗口内最大值 + 之后回撤超5% + 后续至少有 windowSize 天数据
- **信号类型**：3种 — `approaching`（接近前高）、`breakout`（突破）、`failed`（突破失败）
- **历史分析**：遍历全部历史日线，滚动追踪局部高点，统计每次接近后的突破成功率
- **分析结果**：缓存在 `breakout_analysis` 表，包含成功率、历史事件详情（JSON）

### 检测参数

```python
DEFAULT_PARAMS = {
    "lookbackDays": 250,    # 回溯天数
    "windowSize": 5,        # 窗口大小
    "minDropPct": 0.05,     # 最小回撤5%
    "approachPct": 0.95,    # 接近阈值
    "observeDays": 20,      # 突破后观察天数
}
```

### 行情数据拉取（quote_service.py）

- **双数据源**：优先腾讯（`stock_zh_a_daily`），失败自动切东方财富（`stock_zh_a_hist`）
- **增量拉取**：从库中最新日期的下一天开始拉取，已有数据不覆盖
- **防封策略**：批量拉取时随机间隔5-10秒，数据源切换间等待1-2秒

### 知识学习系统（article_service.py）

- **两步流程**：单篇提取（轻量快速）→ 每日汇总（综合深度）
- **单篇分析**：提交文章后，Claude sonnet 提取作者对个股/板块的观点、逻辑、策略，约20秒完成
- **每日汇总**：手动触发，横向对比当日多作者共识与分歧 + 纵向关联前2天策略演变，输出综合策略
- **Claude CLI调用**：`claude -p <prompt> --model sonnet --max-turns 1`，纯分析零工具调用，结果存DB不写文件
- **淘股吧提取**：通过 `div.article-text.p_coten#first` 定位正文，自动提取标题/作者/日期/正文
- **数据库表**：`article`（单篇文章+分析结果）、`daily_summary`（每日综合策略）
- **版本演变**：v1知识文件读写模式 → v2多作者观点提取模式（详见 `version/knowledge-system-v1.md`）

## 命名规范

- 数据库字段：小写加下划线，例如 username、phone、order_num
- 代码变量：驼峰命名法，例如 stockCode、previousHigh
- 禁止出现特殊符号

## 日志规范

- 成功日志：简洁，不需要详细信息
- 错误日志：必须详细，包含完整的错误堆栈和上下文信息

## 公网访问（frp 内网穿透）

- **架构**：公网用户 → AWS EC2(frps:8073) → frp隧道 → 内网服务器(前端:8071 / 后端:8072)
- **EC2**：`18.237.153.223`（us-west-2, t3.micro, rds-query），AWS profile: `zejian.ma`
- **frps**：运行在 EC2 上，控制端口 7000，HTTP vhost 端口 8073
- **frpc**：运行在内网服务器，连接 EC2 frps，注册两个 HTTP 代理（前端 + 后端 /api）
- **公网地址**：`http://18.237.153.223:8073`
- **安全组**：已开放 7000（frp控制）和 8073（HTTP访问）
- **认证**：frp token `quant2024secret`
- **Vite 配置**：已添加 `allowedHosts: 'all'` 允许非 localhost 域名访问

### 踩坑记录
- **Sealos SSH 不支持 TCP 转发**：Sealos Devbox 的 Go SSH 服务器端口监听正常但数据转发被 reset，反向隧道(-R)和本地转发(-L)均不可用
- **内网限制 Cloudflare**：cloudflared 隧道本地代理通了但公网访问被内网出口拦截
- **Sealos 进程存活**：SSH 断开后 nohup/setsid 进程均被清理，不适合跑持久服务

## 已知问题与解决记录

- **akshare北交所SSL报错**：`ak.stock_info_a_code_name()` 会请求北交所（www.bse.cn）导致SSL错误，已改为分开拉取沪深股票（`stock_info_sh_name_code` + `stock_info_sz_name_code`），跳过北交所
- **前端远程访问**：Vite默认绑定127.0.0.1，已在vite.config.js中添加 `host: '0.0.0.0'` 允许远程访问
- **东方财富API被封**：`push2his.eastmoney.com` 从服务器访问不通（云服务器IP被封），已改为双数据源机制，腾讯优先
- **Alembic % 转义**：数据库密码含 `%` 字符导致 configparser 插值报错，在 `env.py` 中用 `.replace("%", "%%")` 解决
- **Vite 7.x allowedHosts**：Vite 7 默认拦截非 localhost 的 Host 头请求返回 403，需配置 `allowedHosts: 'all'`

## 版本归档规范

- 每次大改动（架构调整、模块重构、方案变更）必须归档到 `version/` 目录
- 文件命名：`{模块名}-v{版本号}.md`，如 `knowledge-system-v1.md`
- 内容包含：旧方案描述、为什么废弃（暴露的问题）、新方案设计、文件变更清单
- 同时更新 CLAUDE.md 中对应模块的说明

## 对话语言

- 所有对话和注释使用中文
