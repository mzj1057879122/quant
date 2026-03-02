# 量化股票监控系统

A股短线交易辅助系统，集成前高突破检测、知识学习和交易框架三大模块，帮助短线交易者系统化地监控股票信号、积累交易知识、构建个人交易体系。

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Vue3 前端 (:8071)                      │
│         Element Plus + ECharts + Pinia                   │
├─────────────────────────────────────────────────────────┤
│                  FastAPI 后端 (:8072)                     │
│     ┌──────────┬──────────────┬──────────────┐          │
│     │ 股票监控  │   知识学习    │  交易框架     │          │
│     │          │              │              │          │
│     │ 前高检测  │ 文章提取      │ 心得提取      │          │
│     │ 信号管理  │ 观点分析      │ 原则合成      │          │
│     │ 行情拉取  │ 每日汇总      │ 框架演进      │          │
│     └──────────┴──────────────┴──────────────┘          │
├─────────────────────────────────────────────────────────┤
│  MySQL 8.0 (Docker)  │  akshare (数据源)  │  Claude (AI) │
└─────────────────────────────────────────────────────────┘
```

## 三大模块

### 1. 股票监控 — 前高突破检测

自动识别股票的前高阻力位，实时监控突破状态并推送提醒。

- **前高识别**：在回溯周期内找到最近一个有效高点（需满足：窗口内最大值 + 之后回撤超 5%）
- **三种信号**：
  - `approaching` — 当前价接近前高（达到阈值 95%）
  - `breakout` — 价格突破前高
  - `failed` — 突破后回落失败
- **历史突破分析**：遍历全部历史日线，统计每次接近前高后的突破成功率
- **微信推送**：通过 Server酱 实时推送信号到微信

### 2. 知识学习 — 多作者观点提取

提交短线复盘文章（支持淘股吧 URL 自动提取），AI 分析提取核心观点，每日横向对比生成综合策略。

- **单篇分析**：提交文章 → Claude 提取作者对个股/板块的观点、逻辑、策略
- **每日汇总**：横向对比当日多位作者的共识与分歧 + 纵向关联前 2 天策略演变
- **淘股吧支持**：粘贴 URL 自动提取标题、作者、日期、正文

### 3. 交易框架 — 个人交易体系构建

提交交易心得，AI 提取交易原则，逐步合成系统性交易框架，并注入每日策略分析。

- **七大模块决策链**：大盘判断 → 板块筛选 → 资金行为 → K线形态 → 涨停战法 → 分时技法 → 风控管理
- **版本化管理**：框架随心得积累持续演进，保留历史版本
- **框架注入**：每日汇总时自动将最新交易框架注入分析 prompt

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Element Plus + ECharts + Pinia |
| 后端 | Python + FastAPI |
| 数据库 | MySQL 8.0 (Docker) |
| 数据源 | akshare（腾讯优先，东方财富备用） |
| AI 分析 | Claude CLI (sonnet) |
| 推送 | Server酱（微信） |
| 数据库迁移 | Alembic |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Docker（运行 MySQL）
- Claude CLI（用于 AI 分析功能）

### 1. 启动数据库

```bash
docker run -d \
  --name mysql8 \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=your_password \
  -e MYSQL_DATABASE=quant \
  mysql:8.0
```

### 2. 配置后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 创建 .env 文件
cat > .env << EOF
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=quant
SERVER_CHAN_KEY=your_serverchan_key
EOF

# 执行数据库迁移
alembic upgrade head
```

### 3. 启动后端

```bash
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8072 --reload
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:8071` 即可使用。

## 项目结构

```
quant/
├── backend/
│   ├── main.py                     # FastAPI 入口
│   ├── requirements.txt
│   ├── alembic.ini                 # 数据库迁移配置
│   ├── alembic/versions/           # 迁移脚本
│   └── app/
│       ├── config.py               # 环境配置
│       ├── database.py             # 数据库连接
│       ├── api/                    # 路由层
│       ├── services/               # 业务逻辑层
│       │   ├── detection_service.py   # 前高检测引擎
│       │   ├── quote_service.py       # 行情数据（双数据源）
│       │   ├── article_service.py     # 知识学习
│       │   ├── knowledge_service.py   # 交易框架
│       │   └── notify_service.py      # 推送服务
│       ├── models/                 # SQLAlchemy ORM 模型
│       ├── schemas/                # Pydantic 请求/响应
│       ├── tasks/                  # 定时任务（行情拉取、信号检测）
│       └── utils/                  # 工具类
├── frontend/
│   └── src/
│       ├── api/                    # API 调用层
│       ├── views/                  # 页面组件
│       │   ├── Dashboard.vue          # 仪表盘
│       │   ├── StockList.vue          # 股票列表
│       │   ├── StockDetail.vue        # 股票详情（K线图）
│       │   ├── SignalList.vue         # 信号列表
│       │   ├── ArticleKnowledge.vue   # 知识学习
│       │   ├── TradingKnowledge.vue   # 交易框架
│       │   └── Settings.vue           # 系统设置
│       ├── components/             # 通用组件（K线图、信号卡片等）
│       ├── stores/                 # Pinia 状态管理
│       └── router/                 # 路由配置
└── version/                        # 版本归档（架构演变记录）
```

## API 说明

所有接口前缀：`/api/v1/`

| 模块 | 路径 | 说明 |
|------|------|------|
| 股票 | `/api/v1/stocks` | 股票列表、同步、搜索 |
| 行情 | `/api/v1/quotes` | 日线数据拉取 |
| 信号 | `/api/v1/signals` | 信号列表、突破分析 |
| 文章 | `/api/v1/articles` | 文章提交、URL提取、每日汇总 |
| 框架 | `/api/v1/knowledge` | 心得提交、原则提取、框架合成 |
| 配置 | `/api/v1/config` | 检测参数、推送配置 |

## 核心检测参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| lookbackDays | 250 | 回溯天数 |
| windowSize | 5 | 滑动窗口大小 |
| minDropPct | 5% | 最小回撤幅度 |
| approachPct | 95% | 接近前高阈值 |
| observeDays | 20 | 突破后观察天数 |

## 数据源策略

行情数据采用双数据源容灾机制：

1. **优先**：腾讯（`stock_zh_a_daily`）
2. **备用**：东方财富（`stock_zh_a_hist`）

增量拉取，批量请求随机间隔 5-10 秒防封。
