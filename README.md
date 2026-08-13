# HumanAgent - 自适应自演化生活智能Agent

> 区别于市面所有固定逻辑的AI生活管家，核心亮点是**用户行为自适应、规则自观测、系统自演化**——越用越懂你。

## 一、项目架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    React 前端 (Vite + Chart.js)                  │
│  角色选择 │ Dashboard │ 时间规划 │ 消费记账 │ 物品 │ 学习 │ 出行 │ 规则管理  │
├─────────────────────────────────────────────────────────────────┤
│              API 层 (FastAPI + JWT认证 + 依赖注入)                │
├─────────────────────────────────────────────────────────────────┤
│                    生活执行层 (5大业务Agent)                      │
│  时间规划 │ 消费记账 │ 物品收纳 │ 学习督导 │ 出行处理               │
│         ↑ LangGraph 多智能体编排 ↑                               │
├─────────────────────────────────────────────────────────────────┤
│                    自适应演化层 (核心壁垒)                         │
│  行为采集(含反馈) → 统计分析 → 规则挖掘 → 置信度计算 → 版本追踪     │
│  双模演化：🌙夜间增量(低Token) + 🔬每周全量深度复盘                 │
│  Prompt量化考核(完成率/超支/有效学习) + 指标下滑自动回退            │
│  规则冲突仲裁(高优先级覆盖低优先级)                               │
├─────────────────────────────────────────────────────────────────┤
│            沉淀持久化层 (PostgreSQL/SQLite + pgvector)            │
│  8张业务表 + 行为日志表(含结果反馈) + 用户规则库(版本追踪)          │
└─────────────────────────────────────────────────────────────────┘
```

## 二、技术栈

| 组件 | 选型 | 说明 |
|---|---|---|
| 前端 | React 18 + Vite + Chart.js | 单页应用，响应式设计 |
| 后端 | Python 3.11+ / FastAPI / Uvicorn | 异步高性能 |
| 多智能体 | LangGraph | 状态机驱动的多Agent协作 |
| LLM | OpenAI兼容接口 | 可接DeepSeek/通义千问等 |
| 数据库 | SQLite(开发) / PostgreSQL+pgvector(生产) | 关系数据+向量检索 |
| ORM | SQLAlchemy 2.0 (异步) | 成熟稳定 |
| 认证 | JWT (python-jose) | Token有效期7天 |
| 密码 | bcrypt | 安全哈希 |
| 部署 | Docker Compose | 一键启动 |

## 三、核心创新：自适应演化层

### 3.1 行为日志反馈闭环

所有业务操作均记录结果反馈字段，补齐演化数据闭环：

| 维度 | 反馈字段 |
|---|---|
| 时间规划 | 完成状态 / 实际耗时(分钟) / 用户自评(1-5) / 是否拖延 |
| 学习督导 | 正确率(0-1) / 专注时长(分钟) |
| 消费记账 | 是否刚需 / 是否冲动消费 |
| 物品收纳 | 使用动作(use/expire/discard) |

### 3.2 统计学置信度

废弃LLM随机生成置信度，改用统计学公式：

```
置信度 = 符合规律样本数 ÷ 总观测样本数
```

- 最少 **15条** 观测样本才生成正式规则
- 样本越多，置信度越高（上限0.95）
- 每个规则附带 `sample_count` 和 `version`

### 3.3 双模演化

| 模式 | 触发方式 | 说明 | Token消耗 |
|---|---|---|---|
| 🌙 增量演化 | 每日夜间/手动 | 仅处理当日新增行为数据，更新已有规则置信度 | 低 |
| 🔬 全量深度演化 | 每周/手动 | 全盘复盘习惯，生成新规则，Prompt考核 | 高 |

### 3.4 Prompt量化考核与自动回退

考核指标：
- **日程完成率** — 已完成日程 / 总日程
- **月度消费超支次数** — 冲动消费标签计数
- **有效学习时长** — 专注≥30分钟且正确率≥0.6的会话数

自动回退条件：完成率 < 50% 或 超支 > 10次 → 自动回退上一版Prompt

### 3.5 规则冲突仲裁

- 高优先级规则覆盖低优先级规则
- 优先级：1(低) / 2(中) / 3(高)
- 冲突时记录日志便于用户查看

### 3.6 用户规则管理

- 启用/禁用规则
- 修改规则参数（名称/描述/优先级/表达式）
- 优先级置顶
- 删除规则
- 历史版本回滚

## 四、快速开始

### 方式一：Docker（推荐）

```bash
cp .env.example .env  # 填入 LLM_API_KEY
docker compose up -d
# 前端: http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 方式二：本地开发

```bash
# 1. 安装依赖
uv sync

# 2. 配置
cp .env.example .env  # 编辑 .env 填入LLM相关配置

# 3. 启动后端
uv run python -c "import uvicorn; uvicorn.run('app.main:app', host='127.0.0.1', port=8001, http='h11')"

# 4. 启动前端（另开终端）
cd frontend && npm install && npm run dev
```

## 五、API概览

### 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/auth/roles` | 获取5个固定角色 |
| POST | `/api/auth/select` | 选择角色（返回JWT） |
| GET | `/api/auth/me` | 当前用户信息 |

### 业务模块

| 模块 | 路径 | 说明 |
|---|---|---|
| 时间规划 | `/api/schedules` | 日程CRUD + 完成反馈 |
| 消费记账 | `/api/consumes` | 记账 + 月度统计 + 预算 |
| 物品收纳 | `/api/items` | 物品管理 + 过期预警 |
| 学习督导 | `/api/studies` | 学习计划 + 记录 + 统计 |
| 出行处理 | `/api/travels` | 出行计划 + 状态 |
| Agent对话 | `/api/agent/chat` | 统一入口，自动路由 |
| 数据统计 | `/api/stats/dashboard` | Dashboard综合统计 |

### 自适应演化

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/evolution/run?mode=incremental` | 触发增量演化 |
| POST | `/api/evolution/run?mode=full` | 触发全量深度演化 |
| GET | `/api/evolution/rules` | 规则列表 |
| PUT | `/api/evolution/rules/{id}` | 修改规则 |
| POST | `/api/evolution/rules/{id}/toggle` | 启用/禁用 |
| DELETE | `/api/evolution/rules/{id}` | 删除规则 |
| POST | `/api/evolution/rules/{id}/pin` | 设置优先级 |
| POST | `/api/evolution/rules/{id}/rollback` | 版本回滚 |
| GET | `/api/evolution/snapshot` | 生效规则快照 |

## 六、请求示例

```bash
# 选择角色
curl -X POST http://localhost:8001/api/auth/select \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1}'

# 添加日程（含反馈）
curl -X POST http://localhost:8001/api/schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"高数","start_time":"2026-08-15 09:00:00","end_time":"2026-08-15 10:00:00"}'

# 完成日程（含自评/耗时）
curl -X POST http://localhost:8001/api/schedules/1/complete \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quality":4,"duration_min":55,"is_delayed":false}'

# 触发全量演化
curl -X POST "http://localhost:8001/api/evolution/run?mode=full" \
  -H "Authorization: Bearer $TOKEN"

# 查看规则
curl http://localhost:8001/api/evolution/rules \
  -H "Authorization: Bearer $TOKEN"
```

## 七、数据库模型

| 表 | 说明 |
|---|---|
| `users` | 用户 + 沟通风格画像 |
| `schedules` | 日程 |
| `schedule_items` | 碎片任务 |
| `consume_records` | 消费记录 |
| `budgets` | 动态预算 |
| `items` | 物品 |
| `study_plans` | 学习计划 |
| `study_records` | 学习记录 |
| `travel_plans` | 出行计划 |
| `behavior_logs` | 行为日志（含结果反馈字段） |
| `user_rules` | 用户专属规则库（版本追踪） |

## 八、项目结构

```
app/
├── main.py              # FastAPI入口
├── config.py            # 配置
├── db.py                # 数据库连接
├── seed.py              # 初始化5个角色
├── api/                 # API路由
│   ├── auth.py          # 角色选择认证
│   ├── schedules.py     # 时间规划
│   ├── consumes.py      # 消费记账
│   ├── items.py         # 物品收纳
│   ├── studies.py       # 学习督导
│   ├── travels.py       # 出行处理
│   ├── agent.py         # Agent对话
│   ├── evolution.py     # 演化API（含规则管理）
│   └── stats.py         # Dashboard统计
├── agents/              # 多智能体
│   ├── orchestrator.py  # LangGraph编排器
│   ├── state.py         # 共享状态
│   ├── time_plan/       # 时间规划Agent
│   ├── consume/         # 消费记账Agent
│   ├── item/            # 物品收纳Agent
│   ├── study/           # 学习督导Agent
│   └── travel/          # 出行Agent
├── evolution/           # 自适应演化层
│   ├── miner.py         # 统计学规则挖掘
│   ├── engine.py        # 演化引擎（双模+考核+仲裁）
│   └── analyzer.py      # 行为分析
├── models/              # ORM模型
├── services/            # 业务服务
│   └── behavior_collector.py  # 行为采集（含反馈）
├── templates/           # 模板
└── static/              # 静态资源
frontend/                # React前端
├── src/
│   ├── components/      # 组件
│   ├── pages/           # 页面
│   ├── api/             # API客户端
│   ├── context/         # 全局状态
│   └── App.tsx          # 根组件
└── package.json
```

## 九、5个固定角色

| ID | 名称 | 类型 | 作息 |
|---|---|---|---|
| 1 | 学生小明 | 学生 | 7:00-23:00 |
| 2 | 职场小李 | 职场人 | 6:00-22:00 |
| 3 | 自由职业者 | 自由 | 9:00-1:00 |
| 4 | 考研党 | 学生 | 5:00-23:00 |
| 5 | 全职妈妈 | 自由 | 6:00-22:00 |

## 十、后续扩展方向

- [ ] 接入真实LLM工具调用 (LangChain Tools)
- [ ] 微信/支付宝账单自动导入
- [ ] 定时演化调度 (APScheduler)
- [ ] LangSmith全链路监控
- [ ] 多语言支持
- [ ] 移动端适配
