# Project Overview

**Project:** Personal Readiness Assistant
**Version:** V1.1
**产品定位：** 面向力量训练用户的 readiness-aware training decision assistant。

产品核心不是显示一个 readiness 分数，而是把 **recovery state + training history + programme context**
转化为两个可执行答案：**WHAT TO TRAIN** 与 **HOW HARD TO TRAIN**，并用 **Decision Trace**
解释这个决定是如何得出的。当前形态是 **high-fidelity functional Streamlit prototype**，
不是 production native app，也不是 App Store 级别的成品 UI。

# Git State

| 项目 | 值 |
|---|---|
| Branch | `v1.1-productization` |
| Latest product commit | `6548e08` `fix(ai): recognize readiness index scale in grounding` |
| 迁移 commit | `4f27d22` `feat(ai): migrate coach explanations to DeepSeek` |
| 上一阶段 product commit | `c41485d` `feat(coach): refine conversational interface` |
| Dependency cleanup commit | `fe732fc` `chore(ai): remove local qwen runtime dependencies` |
| Handoff commit | 见本文件所在 commit（`docs: update ai provider and privacy disclosure`） |
| Test baseline | `python -m pytest -v` → **133 passed** |
| Compile | `python -m compileall .` → PASS |
| GitHub remote (`origin`) | `https://github.com/ethanzhang0617-dot/personal-readiness-assistant.git` |
| Tags | 仅 `v1.0.0`（V1.1 未打 tag、未发 Release） |
| 未 push | 本阶段按要求未 push GitHub；本地领先 `origin/v1.1-productization` |

# Current Architecture

```
Streamlit presentation layer (app.py, styles.py, ui_components.py, mobile_shell/)
        ↓
Deterministic product logic
  readiness_engine.py              readiness domains / baseline / safety / index
  training_recommendation_engine.py session selection / prescription / exposure
  Decision Trace                   8 个确定性决策因子
        ↓
AI layer (explanation only)
  ai_facts.py   Personal Fact Router · Deterministic Fact Resolver · Grounding Guard
  ai_engine.py  DeepSeek explanation layer · validation · deterministic fallback
        ↓
Storage
  demo profiles (demo_data.py) · local profile · browser IndexedDB (browser_storage/)
  Export / Import backup (local_data.py)
```

**LLM 永远不是 source of truth。** 它只负责解释已经确定的结论。解释层在 V1.1 DeepSeek migration
中从本地 Qwen 换成 DeepSeek API（`deepseek-flash`、non-thinking）。Personal factual query 不调用任何模型。

## Repo Map（新会话快速定位）

| 文件 / 目录 | 责任 |
|---|---|
| `app.py` | Streamlit 页面渲染与路由（Today / Train / Check-in / Trends / Coach / More / Profile / Science & Logic / About）、页面级 helper、品牌文案 |
| `readiness_engine.py` | readiness domains、personal baseline、safety flags、readiness index、training load |
| `training_recommendation_engine.py` | session 选择、weekly exposure、prescription、workout template、RIR 指导 |
| `ai_facts.py` | 结构化事实层：unit registry、facts、intent router、grounded answer、纠正处理、grounding guard |
| `ai_engine.py` | DeepSeek provider（OpenAI-compatible chat completions）、请求构造、校验、确定性 fallback、AI 诊断 |
| `ui_components.py` | 可复用组件：status badge、metric tile、recommendation card、decision trace row、Coach context/suggestions 等 |
| `styles.py` | Design tokens（Python 单一来源）+ 页面 CSS + mobile shell CSS |
| `mobile_shell/` | 浏览器层 bridge：`viewport-fit=cover`、键盘状态、Coach 进入时回顶 |
| `browser_storage/` | Streamlit ↔ IndexedDB 自定义组件（无可见界面） |
| `profile_store.py` / `local_data.py` | profile 与本地数据序列化、导出/导入、Demo/Local 隔离 |
| `demo_data.py` / `science_content.py` | 固定 Demo 数据集 / Science & Logic 文案与引用 |
| `test_app.py` | 114 个 regression tests（唯一测试文件） |
| `scripts/design_system_preview.py` | 开发用设计系统预览（不是产品页面） |
| `scripts/deepseek_smoke.py` | 手工 live QA（唯一允许真实调用 API 的地方，不属于 pytest） |
| `docs/*.md` | baseline、UX audit、mobile shell、design system、AI grounding、DeepSeek migration、science reference audit、本 handoff |

# Readiness Engine

四个 domain：**Autonomic**（LnRMSSD、resting HR）、**Sleep & Recovery**（时长 + 质量）、
**Subjective Wellness**（fatigue / soreness / stress / motivation）、**Training Load**（见下）。

* 比较基准是**个人纵向基线**，不是人群统一阈值：`LnRMSSD = ln(RMSSD)`，`z = (today − personal mean) / personal SD`。
* 基线窗口：`BASELINE_NORMAL_DAYS = 28` 个有效观测 → confidence `NORMAL`；`BASELINE_LIMITED_DAYS = 14` → `LIMITED`；不足 → `INSUFFICIENT`。
* 状态语义：`GREEN` / `AMBER` / `RED` / `INSUFFICIENT DATA` / `STOP / PROFESSIONAL REVIEW`。
  少于 3 个 domain 可判定时整体为 `INSUFFICIENT DATA`；任一 safety flag → `STOP`。
* **Readiness Index** 是次级指标：`{GREEN:100, AMBER:60, RED:25}` 在可判定 domain 上的均值（不足 3 个 domain 时为 `None`）。
  **它不是 recovery percentage**，也不是疲劳/伤病预测。
* 阈值、聚合、index、confidence 都是透明 prototype heuristics，未经前瞻性验证（见 `assessment["limitations"]`）。

# Training Decision

* **WHAT TO TRAIN** 主要由：Goal · Programme / Split · 7-day exposure · Recent training · Local soreness 决定。
* **HOW HARD** 主要由：Readiness（session demand 调节）决定。
* 主推荐与替代方案都由 `training_recommendation_engine.recommend_training()` 生成；
  **选择替代方案不会覆盖 primary recommendation**。

# Decision Trace

固定顺序，全部来自确定性引擎输出：

`GOAL → PROGRAMME / SPLIT → 7-DAY EXPOSURE → RECENT TRAINING → LOCAL SORENESS → READINESS → SESSION DEMAND → RECOMMENDATION`

Decision Trace **不是** LLM chain-of-thought，也不是 debug log；它是产品可公开解释的决策因子。

# Exposure Semantics（重要 contract）

* 窗口：`weekly_training_exposure()` 使用 `0 <= age < 7` 天 = **last 7 days including today**（含今日的最近 7 天），
  **不是 calendar week**。
* 单位：**weighted working sets**。映射：**direct set = 1.0，mapped secondary set = 0.5**；
  未映射动作按每个动作一次显式 fallback 计入 primary muscle group 或可映射的 session focus。
* muscle taxonomy（7 组）：`Chest, Back, Shoulders, Arms, Quads, Hamstrings / Glutes, Core`。
* **禁止**：`sets → days`、`exposure → sessions`、`rolling 7 days → calendar week`。
* UI 与 Coach 均写作 “7-day exposure”；`ai_facts.EXPOSURE_PERIOD = "the last seven days including today"`。

# Training Load

* 定义：**session duration × session RPE**，按日汇总（同一天多节课相加；比较窗口内没有完成训练的日期记 0 AU）。
* 单位：**AU**。窗口：最近 **7 个完整日历日** vs 之前 **21 个完整日历日**（`LOAD_RECENT_DAYS=7`、`LOAD_REFERENCE_DAYS=21`，calendar-day based）。
* 覆盖不足时返回 `INSUFFICIENT`，不会把缺失日期当作休息日。
* **Training Load（AU）绝不能与 Session Duration（minutes）混淆**：duration 是分钟，load 是 AU。

# AI Coach

* **Personal factual queries** 走 `ai_facts.route_question()` → `grounded_answer()`，
  **完全不调用模型**，例如 `How much have I trained back this week?`、`What's my training load today?`、
  `What's my readiness today?`、`How many days have I trained back this week?`。
* **Explanation / discussion questions**（Why / Explain / Can I train harder、RIR 等一般知识）可以走 DeepSeek，
  经 `validate_llm_response()` + `guard_llm_response()` + `guard_explanation_grounding()` 后才展示，
  否则回退到确定性回答。
* 模型：`deepseek-flash`（non-thinking），OpenAI-compatible `POST https://api.deepseek.com/chat/completions`。
  可用 secrets 覆盖 `DEEPSEEK_MODEL`、`DEEPSEEK_BASE_URL`，或用 `DISABLE_AI_COACH=true` 强制关闭
  （旧键 `DISABLE_EMBEDDED_LLM` 仍被接受，向后兼容）。
* 只有在 Coach 真正需要生成解释时才构造 provider 并发起请求；Today / Train / Check-in / Trends / More
  不创建 AI client、不调用 API。Personal factual query 即使在 Coach 内也不调用。

# AI Provider（V1.1 DeepSeek migration）

| 项目 | 值 |
|---|---|
| Provider | DeepSeek（OpenAI-compatible chat completions） |
| Model | `deepseek-flash`（UI 只显示 `AI explanation · DeepSeek`，不硬编码版本号） |
| Thinking | 显式 `"thinking": {"type": "disabled"}`，不依赖默认值 |
| Transport | `requests`（Streamlit 已有依赖）直接 POST，无 LangChain / LlamaIndex / agent framework |
| API key | Streamlit secrets `DEEPSEEK_API_KEY` → 其次环境变量 `DEEPSEEK_API_KEY` |
| Key 安全 | 不 hardcode、不 commit、不打印、不写 browser storage、不发前端；错误信息经 `_redact()` 过滤 `sk-*` |
| 输出上限 | `MAX_OUTPUT_TOKENS = 400`；`REQUEST_TIMEOUT_SECONDS = 20.0` |
| 实测延迟 | 中位数 2.9 s（2.36–3.85 s），12 个真实样本 |
| 请求体防护 | 不打印 provider body；HTTP 状态只保留状态码 |
| 失败行为 | 缺 key / 401 / 429 / 5xx / timeout / 网络 / 非法或空响应 / 草稿被 guard 拒绝 → 确定性回答 + 用户可见提示，绝不 crash |
| Diagnostics | 仅记录 token 计数与耗时；不持久化 prompt |

上下文最小化：只发送 profile 基础字段（name / goal / level / split）+ `ai_facts.facts_for_prompt(facts)`
（readiness、recommendation、7-day exposure、近期 sessions、soreness、signals、training load）+ 最近 8 条
对话（每条截断 500 字符）。**不发送**完整 30+ 天原始记录、IndexedDB dump、backup、其他 profile 数据。

隐私边界：用户保存的历史仍在浏览器 IndexedDB；只有当用户提出解释类问题时，摘要上下文与最近对话才发送给
配置的 DeepSeek API。个人事实性问题零 provider 调用。

回归契约（新增）：

* `Why this workout?` 这类解释问题在缺 key、超时、provider 报错、响应非法时都必须回退到确定性回答。
* `How much have I trained back this week?` 及所有 personal factual / correction 轮次对 provider 的调用数必须为 **0**。
* 模型草稿若新增未记录数字、改单位、改周期、替换 primary recommendation 或编造 rationale，必须被 guard 拦截。

# Frontend Migration Status（V1.2 Phase 2 已完成功能 parity，本地未 push）

* 分支：`v1.2-nextjs-migration`（自 `v1.1-productization` 的 `0c42048` 创建）。Phase 1 已推送（`84fee69`）。
  **Streamlit V1.1 未被删除、仍可运行**，仍是 reference implementation。
* **Phase 2 起，用户自己的数据由浏览器持有**（IndexedDB，按 profile 分开存储），API 变成**无状态计算层**：
  客户端把 state 随请求发出，服务端 materialise 后调用现有引擎，不落任何服务端数据库。
* Phase 2 新增端点：`GET /api/scenarios` · `/api/profile/options` · `/api/state/base` · `/api/science/logic`；
  `POST /api/state/today` · `/api/state/check-in` · `/api/state/profile` · `/api/state/session` ·
  `/api/state/coach` · `/api/state/insights`。
* 网页端新增：`/check-in`（完整晨检，含单位、校验、局部酸痛、safety 屏）、Train 的 session 切换 +
  workout template + 完成训练记录、Insights 趋势图（window 7/28/all + 4 条曲线 + 基线），
  Profile 可编辑 + 周目标 + demo 场景/档案切换、Profile → Data（数据来源、隐私、导入导出、About）。
* 两处纯数据抽取，使 API 不再 import Streamlit：`scenario_data.py`（SCENARIOS + `scenario_values`）、
  `product_options.py`（goal/level/split/activity/sex 选项）。`app.py` 改为 import 这两者，行为不变。
* Coach 契约不变：事实性/纠正轮次 **0 次 provider 调用**，解释类才可能调 DeepSeek；
  对话按 profile 持久化在本浏览器。starter 措辞改为 router 能解析的 `How much have I trained back this week?`
  （**未修改 router**）。
* Phase 2 验证：`pytest` → **161 / 161 PASS**（149 → 161，新增 12 项 API 测试）·
  前端 `pnpm typecheck` / `lint` / `build` 全部 PASS · 浏览器端到端 **20/20** ·
  档案切换 **6/6** · 视觉 QA 8 路由 × 2 视口 **横向溢出 0px**。
* 仍未 parity（已记录，见 `docs/V1_2_FUNCTIONAL_PARITY.md`）：图表无 hover tooltip、
  Trends 的 "sessions in the last 14 days" 指标、import 的两步确认、独立 About 路由、
  本地多档案账号管理（create/delete local profile）与 demo regenerate 工具。
* 正常产品演示**不再需要 Streamlit**；仍留在 Streamlit 的只有开发者/诊断类工具。
* 新增：`backend/`（FastAPI：`main.py` · `api/routes.py` · `services/*` · `schemas/models.py`）、
  `frontend/`（Next.js 16 App Router + React 19 + TypeScript + Tailwind 4 + shadcn/ui 风格原语）、`test_api.py`。
* 复用且未修改：readiness / recommendation / training load / exposure / Decision Trace / safety /
  `ai_facts` / `ai_engine`(DeepSeek) / `science_content` / `demo_data`。FastAPI 只做编排。
* 唯一被移动的文案：`EVIDENCE_BOUNDARIES` 提取为 `science_content` 中的常量，Streamlit 页面与 API 共用同一份文本
  （可见文案逐字不变）。
* API：`GET /api/health` · `/api/profiles` · `/api/profile` · `/api/today` · `/api/readiness` ·
  `/api/training/recommendation` · `/api/training/exposure` · `/api/training/history` · `/api/decision-trace` ·
  `/api/science/references`；`POST /api/check-in` · `POST /api/coach/message`。全部返回结构化 JSON。
* Coach 契约不变：事实性 / 纠正 / 安全轮次 **0 次 provider 调用**；只有解释类问题可调 DeepSeek；
  key 仅存在于服务端进程（`/api/health` 只报告"是否已配置"）。
* 测试基线：**139 → 149 passed**（新增 `test_api.py` 10 项；`test_app.py` 未改动）。
  前端 `pnpm typecheck` / `pnpm lint` / `pnpm build` 全部 PASS。
* 视觉 QA（Playwright + 真实 dev server + 真实 API）：390×844 与 1440×900、六个路由横向溢出 **0px**，
  底部导航 73px 贴合安全区，Today 首屏即包含 PRIMARY CTA（未与导航重叠）。
* 仍未 parity（仍在 Streamlit）：check-in 提交与校验 UI、完成训练日志、profile 编辑与周目标、
  IndexedDB 持久化与导出/导入、多日趋势图、Demo 场景切换、开发者诊断面板。
* 细节见 `docs/V1_2_FRONTEND_MIGRATION.md`。本阶段**未 push、未合 main、未打 tag**。

# Science & References（V1.1 audit，2026-09-16）

* 参考书目 **12 → 13 篇**（新增 Buchheit 2014 · PMID 24578692 · DOI 10.3389/fphys.2014.00073），
  **0 篇移除、7 篇修正、0 篇无法验证**。全部 13 篇的题录经 PubMed、Europe PMC、Crossref 三方核验，
  13 个 DOI 均由 Crossref 解析无误。
* 主要修正：Schoenfeld 2019 的**截短标题**补回官方完整标题（volume-equated 语义关键）；
  Schoenfeld 2017 标题大小写；Bourdon / Greig / Zhang / Robinson / Düking 的 "et al." 补全为完整作者列表；
  全部条目补充已验证 DOI。
* 每篇参考新增 **DOI 链接**，Science & Logic 页新增 **Evidence boundaries** 区块。
* 声明分类：A 直接支持 8 · B 证据知情的解释 6 · C 产品启发式 13 · **D 过度声明 0**。
* 产品启发式清单（阈值带、domain 聚合、Readiness Index 映射、7/21 天 load 窗口、session-demand 映射、
  RIR 区间、fractional set 权重、exposure 窗口、recommendation 顺序、safety routing）全部在审计文档中
  逐条标注为 **未直接验证**。
* 详细表格见 `docs/V1_1_SCIENCE_REFERENCE_AUDIT.md`（含 per-reference 状态、"supports / does not support"、
  Product Heuristic Inventory、Claim → Source Matrix、剩余科学局限）。
* **本轮未改动任何 engine**：`readiness_engine.py`、`training_recommendation_engine.py`、
  training load / exposure 逻辑、thresholds、Decision Trace、safety logic、AI router、grounding guard 全部原样。

# AI-01（历史关键 bug 与修复）

**原始错误：** 用户问 `How much have I trained back this week?`，模型回答 “trained back for 12 days this week”，
把 weekly exposure（weighted working sets）错误表达成 days；追问后还跳到无关的 session duration。

**当前修复：** 意图路由（Personal Factual Query / Correction / Explanation / General / Unresolved）·
结构化事实层（每个数值带 unit / period / source）· 显式单位注册表 · source-of-truth 重新读取 ·
纠正与质疑处理 · grounding guard（新增数字 / 错误单位 / 周期漂移一律回退）。

**回归契约：** `How much have I trained back this week?` 的回答必须包含真实数值与 `weighted working sets`，
且**不得**出现 “12 days” 这类 unit 漂移。

# Coach Current UX

`AI COACH` eyebrow → `AI Coach` 标题 + 一行副文案 → **TODAY CONTEXT**（单一轻量表面：readiness 徽章 · 今日 session · session demand）→
**SUGGESTED**（4 条会话起始行，`→` 前缀、左对齐、分隔线、44px 行高）→ `How the Coach works`（无边框 disclosure）→
对话区 → **一体化 Composer**（圆角容器 + 内嵌炭黑发送键，移动端 44×44）。

* 个人事实回答显示 **VERIFIED DATA** 微徽章（该回答没有调用 DeepSeek）；AI 解释显示的 provider 信息
  降级为小字元数据，形如 `AI explanation · DeepSeek`。
* 进入 Coach 且对话为空时停留在页面顶部（不自动滚到底部）。
* Coach 的 visual 结构未在 DeepSeek migration 中改动；只替换 provider metadata、spinner 文案与隐私披露。

# Current UI（逐页现状）

* **TODAY** — Greeting · Readiness hero（状态徽章 + 状态文案 + 一句解释 + INDEX + baseline confidence）·
  Today's Training（**WHAT TO TRAIN** / **HOW HARD** 双列 + 时长 + 类型）· Primary CTA `View workout`（炭黑，≥48px）·
  WHY TODAY（TRAINING DIRECTION / SESSION DEMAND，来自 decision trace）· KEY SIGNALS（HRV / Resting HR / Sleep / Training Load，
  2×2 metric grid）· 折叠的 Readiness details 与 Decision Trace。
* **TRAIN** — PRIMARY RECOMMENDATION 卡（WHAT / HOW HARD / RIR guidance）· ALTERNATIVES（明确第二优先级，可选择预览）·
  HOW TO EXECUTE IT（动作名 + 剂量行的纯列表）· AVOID TODAY（中性）· DECISION TRACE（8 步，`decision_trace_row`）· LOG WORKOUT 表单。
* **CHECK-IN** — Recovery（HRV / RHR / sleep duration / sleep quality）· How You Feel（每个量表都有方向说明：
  fatigue / soreness / stress 越高越多，motivation 与 sleep quality 越高越好）· Local soreness（两列网格，可留空）· Safety check ·
  提交 CTA `Calculate readiness`。
* **TRENDS** — 时间窗（Last 7 / 28 / All **check-ins**，按记录数而非自然日）· HRV / Resting HR / Sleep / Training load 四个图表
  （非零轴、滚动均值虚线、个人基线参考线、Latest + Your baseline 摘要行）· Training history 与 Readiness history 使用紧凑历史行（不再用被裁切的 dataframe）。
* **COACH** — 见上。
* **MORE** — ACTIVE PROFILE 主卡（姓名 + DEMO / LOCAL 徽章 + 目标）· `Change profile` 选择器（移动端可切换 Demo 与本地档案）·
  设置行（Profile / Data / Science & Logic / About）· 本地数据控制与说明。

# Design System

单一来源：`styles.DESIGN_TOKENS`（Python → CSS 变量）。

* Background 暖白 `#f8f7f4`；Surface 白 / `#fbfaf7`；Text 近黑 `#16181a` + 次级中性灰；Border 极浅 `#eeeeea`。
* **Green** 只表示 positive readiness/status；**Amber** 只表示 caution / moderate；**Red** 只用于 RED / STOP / destructive；
  **Charcoal / near-black `#1a1c1e`** 才是普通 primary action 的颜色。**Red 不能作为普通 CTA**。
* Typography：系统字体栈；page title `clamp(1.55–2rem)`（移动端 1.5rem），hero title `clamp(1.35–1.7rem)`，正文 `.9rem`。
* Spacing 刻度 `2xs .25 / xs .5 / sm .7 / md 1 / lg 1.15 / xl 1.4 / 2xl 1.9rem`；Radius `sm 10 / md 12 / lg 16 / pill 999`；卡片弱边框、几乎不用阴影。
* Bottom nav：激活项为柔和浅色 pill + 深色粗体文字（不是实心黑块），高度 64px（56 内容 + 8 floor）。

# Storage

* 本地数据保存在**浏览器 IndexedDB**（`browser_storage/` 自定义组件）；Demo profile 与 My Local Profile 完全隔离：
  Demo seed data 不写入本地存储、不会覆盖本地数据，本地档案也不会继承 Demo 历史。
* 已验证：写入 → 刷新 → hydrate 恢复；Export / Import backup 存在。
* 不要把 “data never leaves your device” 当作承诺：Streamlit runtime 参与计算，措辞应说明数据保存在本浏览器、
  并且依赖启动时的运行环境（当前无远程个人数据库、无 API key）。

# Mobile Shell

* 自定义底部导航（5 个主目的地）+ `More` 工具行；移动端隐藏 Streamlit chrome（header / toolbar / Deploy / 菜单 / sidebar / expand-sidebar）。
* Safe area：`mobile_shell/frontend/shell.js` 注入 `viewport-fit=cover`，CSS 使用 `max(env(safe-area-inset-bottom), 8px)`；
  键盘打开时释放导航带（`ara-keyboard-open`）。
* 内容 clearance：滚动容器高度 = `100dvh − --ara-shell-bottom`，因此**固定导航不会覆盖任何内容**。
* Coach composer 与导航不再争抢空间（重叠 0）。
* Regression requirement：**no content hidden behind nav**、**no horizontal overflow**、safe-area 逻辑不得破坏。

# Test Baseline

`python -m compileall .` → PASS；`python -m pytest -v` → **161 / 161 passed**
（139 项 Streamlit/engine 回归 + 22 项 FastAPI 适配层，见 `test_api.py`）。

关键 regression 区域：mobile shell 间距契约与 chrome 选择器 · Today 首屏（Readiness / Training / Session Demand / CTA）·
Train 的 primary 与 alternatives 层级 + 8 步 decision trace · 档案切换与 Demo/Local 隔离 · IndexedDB 写入/刷新/恢复 ·
AI-01 事实性（CASE 1–15 + guard）· Coach 纠正与质疑 · 跨页术语 · Design System tokens 与状态语义 ·
DeepSeek 请求构造与非 thinking 配置 · 缺 key / 超时 / 网络 / 401 / 429 / 5xx / 非法响应 fallback ·
上下文最小化与 profile 隔离 · 事实性问题零 provider 调用 · 幻觉草稿被 guard 拦截 ·
readiness 量表上下文（`71/100` 接受、`83/100` 与 `100 minutes`/`100 bpm` 仍拒绝、`100` 不入全局白名单）。

单元测试一律使用注入的 fake transport（`monkeypatch.setattr(ai_engine.requests, "post", ...)`），
**不会真实调用 API**。真实调用只允许出现在 `scripts/deepseek_smoke.py` 的手工 QA 中。

# Local Run

```bash
# 产品（默认 http://localhost:8501）
python -m streamlit run app.py

# 开发用设计系统预览（不在产品导航内）
python -m streamlit run scripts/design_system_preview.py

# 可选：DeepSeek live smoke check（需要 DEEPSEEK_API_KEY，唯一允许真实调用 API 的地方）
DEEPSEEK_API_KEY=... python scripts/deepseek_smoke.py

# 变更前的基本验证
python -m compileall .
python -m pytest -v
```

注意：没有 `DEEPSEEK_API_KEY` 时 App 完全可用，解释类问题显示 *AI explanation is temporarily unavailable*
并给出确定性回答。`DISABLE_AI_COACH=true`（secrets 或环境变量）可显式关闭解释层。
runner 需要能访问 `https://api.deepseek.com`（当前开发机未做 live 验证，见 Known Limitations）。

# Known Limitations（诚实清单）

* **真机未验证**：iOS Safari / Android Chrome 上的安全区、键盘、动态工具栏行为仅通过 Chromium 仿真验证过。
* **Streamlit Cloud 部署未验证**：本阶段没有做真实 Cloud 部署；`requirements.txt` 使用 `streamlit>=1.42,<2` 的宽范围，
  云端可能解析到与本机 1.56 不同的版本，移动外壳选择器需要重新确认。移除 torch/transformers 后
  install 体积与启动时间应显著下降，但**本机没有做前后对比测量**，不要引用未测量数字。
* **框架级视觉上限**：native slider / select 形态、次级控件尺寸、桌面端 Streamlit chrome、框架 spinner。
* **DeepSeek live 调用已验证**（2026-09-16，20 次真实调用）：认证 · base URL · `deepseek-flash` alias ·
  non-thinking 参数均被真实端点接受；延迟中位数 **2.9 s**（范围 2.36–3.85 s），token 约
  812–1019 prompt / 96–195 completion；事实与纠正轮次实测 **0 次 provider 调用**。
  仍未验证的部分只剩：依赖体积/启动时间的前后对比、带 secret 的 Streamlit Cloud 部署、真实手机行为。
* **解释类回答**：guard 优先于文采（grounding > eloquence）。度量上更强的模型（DeepSeek）应降低回退率，
  但 guard 不会被削弱或删除；若真实 provider 的措辞频繁触发 guard，正确做法是调整 prompt，而不是放宽 guard。
* **成本**：没有任何服务端配额或持久化计数。当前保护只有 bounded history、bounded output、context minimization
  与"事实性问题零调用"；公开 demo 长期运行仍需要额外的配额方案。
* **已知未修的两个观察项**（已记录、当前不改行为）：`Can I swap the cable row for a machine row?` 被
  alternative 规则拒绝（仅 1 个 live 样本）；`Should I reduce volume if my back is still sore tomorrow?`
  因 "sore" 被路由成 PERSONAL_FACT（既有路由设计，未来需区分"假设/未来建议"与"当前个人事实"）。
* **产品边界**：不是医疗设备，不做 fatigue / injury prediction，不提供 recovery percentage，不做诊断。

# Visual Status

V1.1 已完成较完整的 visual polish（颜色角色、排版、卡片、间距、导航、图表外观、Coach 结构）。
仍然存在的 Streamlit framework constraints：native slider / select 形态、次级控件尺寸（滑块刻度、帮助图标、图表工具条）、
桌面端 Streamlit chrome（Deploy / 菜单）、框架自带 spinner、以及运行时的 chat 布局 spacer。
因此当前产品定义为 **high-fidelity functional prototype**，不是 App Store 级别的 production UI。

# Non-Negotiable Product Contracts

1. Deterministic Engine 是 source of truth。
2. LLM 不得发明任何个人指标。
3. Personal factual query 必须使用已验证的结构化数据（不调用模型）。
4. Weekly exposure 不得表达成 days。
5. Training Load 不得表达成 minutes。
6. Session Duration 不得表达成 AU。
7. 7-day exposure 不得称为 calendar week。
8. Readiness 不得称为 recovery percentage。
9. GREEN / AMBER / RED / STOP 语义保持一致。
10. Red 不是普通 CTA 颜色。
11. Demo 与 Local profile 数据保持隔离。
12. Today / Train / Check-in / Trends / More 不得创建 AI client 或调用 DeepSeek API。
13. UI 工作期间不得随意修改核心 engine。
14. Decision Trace 是确定性解释，不是 AI chain-of-thought。
15. Explanation provider 只能是 DeepSeek；**不允许** DeepSeek → Qwen → fallback 的多级回退，只能是
    DeepSeek → deterministic fallback。
16. DeepSeek API key 不得 hardcode / commit / 打印 / 写入 browser storage / 发往前端。
17. 发送给 provider 的 personal context 必须是最小化摘要；不得发送完整原始历史、backup 或其他 profile 数据。
18. guard（`validate_llm_response` / `guard_llm_response` / `guard_explanation_grounding`）不得因为模型更强而被删除或放宽。
19. Readiness Index 量表上界（`100`）**只能紧跟在已核实的 index 数值之后出现**（`71/100`、`71 on a 0–100 scale`）。
    禁止把它变成全局白名单：`100 minutes`、`100 weighted working sets`、`100 bpm`、`100 ms`、
    以及 `83/100` 这类新 index 数值仍必须被拒绝。`facts_numbers()` 必须继续跳过 `index_scale`。

# Do Not Resurrect Without Explicit Decision

* **streamlit-shadcn-ui**：已评估并放弃（1.4.0 要求 Streamlit ≥ 1.60，当前基线 1.56；Shadow DOM + 自带 Tailwind 无法消费本项目 tokens；32px/25px 触控目标与移动端契约冲突）。
* 不要无限继续在 Streamlit 上做 CSS polish 以追求 native 观感。
* 不要加入 cloud backend / login / Supabase / Firebase。
* 不要接入 wearable（Apple Health / Garmin / WHOOP / Oura）——那是后期数据入口，不是当前核心。
* 不要让 LLM 成为 source of truth，也不要把 “AI 自动生成训练计划” 当作当前产品方向。
* 不要为了让 demo 好看而修改 scientific thresholds。
* 不要仅为引入 UI component library 而升级 Streamlit。
* **不要把本地模型（Qwen / transformers / torch）重新加回 runtime**：解释层已迁移到 DeepSeek API，
  本地推理路径已删除。若未来需要离线模型，必须作为显式的新决策重新评估，而不是"顺手加回来"。
* 不要因为 DeepSeek 更强就删除或放宽 grounding guard，也不要让 provider 成为 source of truth。
* 不要在 pytest 中调用真实 DeepSeek API。

# Product Roadmap

**CURRENT — V1.1**
Explainable Daily Training Decision；high-fidelity Streamlit functional prototype。

**DONE — V1.1 DeepSeek migration**
解释层已从本地 Qwen 迁移到 DeepSeek API（non-thinking）。deterministic decision engine、
Personal Fact Resolver、Grounding Guard 全部保留。详见 `docs/V1_1_DEEPSEEK_MIGRATION.md`。
**Live 验证已完成**：认证 / base URL / `deepseek-flash` alias / non-thinking 全部实测通过，
延迟中位数 2.9 s。live QA 发现的 readiness 量表 guard 误报（`71/100` 被当成幻觉数字）已修复，
EXPLANATION 接受率 0/5 → 4/5。剩余问题见 `docs/V1_1_DEEPSEEK_MIGRATION.md` 的 observed issues。

**FUTURE PRODUCT STEP — V1.2 Adaptive Decision Loop（尚未实现）**
Post-session feedback · Actual session response · Personal Response Profile · Recommendation Confidence ·
In-session Calibration · What-if / Counterfactual Decision Explorer。

# Adaptive Decision Loop Vision（FUTURE / NOT IMPLEMENTED）

```
Understand today → Recommend → Perform session → Observe actual response
→ Learn personal response → Improve next decision
```

产品演进主线：**Personal Baseline → Personal Response**。以上均未实现。

# Wearable Roadmap（FUTURE / NOT IMPLEMENTED）

Apple Health / Garmin / WHOOP / Oura 属于后期数据入口，核心价值是**降低手动输入摩擦**，
不是产品创新本身。当前 demo 不实现任何 wearable 集成。

# Production Frontend（FUTURE / NOT DECIDED）

可能的演进方向：React / Next.js frontend → API layer → 复用现有 Python engines。
原因是 Streamlit 已接近 presentation-layer 的视觉上限。**当前没有进行 migration，也没有决定必须执行。**

# New Codex Session Boot Procedure

新会话开始后：

1. 读取 `docs/CODEX_HANDOFF.md`（本文件）。
2. `git status`
3. `git branch --show-current`
4. `git log -3 --oneline`
5. 确认最新 baseline（branch / commit / tests）。
6. `python -m compileall .`
7. `python -m pytest -v`
8. 确认 test baseline（当前应为 161 passed，其中 `test_api.py` 22 项）。
9. **不要修改任何代码。**
10. 先汇报理解，然后等待用户的下一条指令。
