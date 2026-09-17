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
| Branch | `v1.3-adaptive-decision-loop` |
| 已冻结基线 | `v1.2-nextjs-migration` = `7d21568`（V1.2 RC）· `v1.1-productization` = `0c42048` · `main` = `fe09ab6` · tag 仅 `v1.0.0` |
| V1.3 Phase 1（已推送） | `673010f` `docs: document the adaptive decision loop phase 1` |
| V1.3 Phase 2（已推送） | `e09a88b` `docs: record adaptive loop phase 2` |
| V1.3 最终冲刺（本地，待 push） | 见本文件所在 commit |
| Test baseline | `python -m pytest -v` → **246 passed**（`test_app.py` 139 · `test_adaptive.py` 31 · `test_api.py` 39 · `test_calibration.py` 37） |
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

# Frontend Migration Status（V1.3 Phase 2 Adaptive Decision Loop，本地未 push）

* 分支：`v1.3-adaptive-decision-loop`（自 V1.2 RC `7d21568` 创建）。V1.2 RC 已冻结在 GitHub
  （`v1.2-nextjs-migration` = `7d21568`），main / v1.1 / v1.0.0 tag 均未触碰。
* Phase V1.3-1 = **Personal Response 基础层**（确定性、有界、可解释，无机器学习）：响应情节
  （session 记录时的会话前快照 + 实际完成 + 反馈 + 次日签到）、证据状态（Insufficient/Emerging/
  Established）、**最多一个档位**的 HOW HARD 调整、9 步 Decision Trace（READINESS 与 SESSION DEMAND
  之间新增 PERSONAL RESPONSE）、Train 的轻量训练后反馈、Insights 的 Personal Response 区块、
  Coach 的确定性 Personal Response 事实回答（**0 次 provider 调用**）、存储 v2→v3 迁移。
* 安全优先：RED / STOP / 数据不足 / Low 档永不调整；向上调整要求目标档位 Established（≥6 次）且
  今日 readiness 为 GREEN —— 因引擎的 demand 恰好等于 readiness 允许的档位，该分支当前**不可达**，
  已在文档与测试中如实标注。
* 演示（Profile → Demo controls，不进入日常流程）：Not enough history yet / Emerging / Poor tolerance
  to high demand（**High → Moderate 调整**）/ Established good tolerance。
* 测试：**188 / 188 PASS**（161 基线 + 18 自适应层 + 9 API）。前端 typecheck / lint / build 全绿；
  `pnpm check:store` 11/11 迁移断言通过；V1.3 端到端 **19/19**（Chromium 与 WebKit 各一轮）；
  跨引擎响应式 **54/54**。
* 细节见 `docs/V1_3_ADAPTIVE_DECISION_LOOP.md`。

## V1.3 Phase 2 — Personal Response Profile & Recommendation Confidence（本地未 push）

* **Personal Response Profile**：按 demand band（Low / Moderate / High）给出观测数、证据状态、
  `poorer / as expected / good` 计数、整体 pattern 与 recent pattern；**按 training focus 的 pattern
  只有在该 focus 已有 ≥3 个完整情节时才显示**，绝不编造类别。
* **Recommendation Confidence**：三态定性词汇 **Limited / Developing / Strong**（<3 相关情节 → Limited；
  3–5，或 6+ 但 pattern 不一致 → Developing；6+ 且一致 → Strong）。**不是概率、不是恢复分数、不显示百分比**，
  也不影响 readiness index、GREEN/AMBER/RED 或 safety routing。
* **Evidence coverage**：完整情节数、等待次日签到的情节数、最近一次完整情节、各 band 的观测数。
* **Consistency**：相关情节方向一致度（≥3 个情节且 ≥60% 同向 → Consistent，否则 Mixed）；tie-break 顺序固定，
  保证同一输入得到同一 leader。
* **Recency**：透明启发式（非指数衰减）——只有 `RECENT_WINDOW_DAYS = 56` 天内、最新 `MAX_RECENT_EPISODES = 12`
  个情节可以驱动今日判断；**旧情节不会消失**，仍留在 history、profile 计数与 Insights 中，只是不再影响今天。
* **Adaptation history**：客户端 state 内 `adaptation_log`（按日期 upsert，上限 90），记录 base/final demand、
  adjustment、result（reduced / raised / within_tier / no_change）、confidence、evidence、相关情节数与原因；
  只记录"有意义的决策事件"，不记录内部计算。
* **不可达的向上调整已诚实处理**：Phase 1 的 `Moderate → High` 档位提升在真实产品路径中不可达（引擎的 demand
  本身就是 readiness 允许的档位），Phase 2 **删除该规则**，改为**档位内个性化**（within-tier）：证据 Strong +
  持续耐受良好 + readiness GREEN + 无 safety/酸痛问题时，给出"在既有 RIR 区间内取更靠硬端"的**可选**提示；
  条件不满足时用产品语言说明原因；确实没有安全档位内选项时使用明确的 ceiling 文案。
  **产品不再宣称任何无法执行的向上适应**，测试与文档同步。
* **演示修正**：`demo_seed(profile, case, base_demand)` 现在按"产品今天实际开出的 demand"写入演示情节
  （Phase 1 把部分案例写成 `Reduced / autoregulated`，导致当前 High 推荐的相关情节为 0、演示显示
  "Limited evidence" 却声称在展示 established pattern）。四个演示态：Not enough history（Limited）/
  Emerging pattern（Developing）/ Poor tolerance（Developing + High→Moderate）/ Established good tolerance
  （Strong + within-tier，档位不变）。
* **前端**：Today 仅在 Personal Response 真正影响决策时显示一行紧凑的 `Recommendation confidence`；
  Decision Trace 的 PERSONAL RESPONSE 步骤新增 Evidence / Pattern / Confidence / Adjustment 结构化明细；
  Insights 新增 Personal Response Profile / Evidence Coverage / Recent Response Episodes / Adaptation History；
  Coach 新增确定性提问 starter（信心、支撑情节数、是否调整过、为何不增加）。
* **修复的真实缺陷**：前端 `refreshToday` 之前丢弃了 `/api/state/today` 返回的 state，导致
  `adaptation_log` 永远进不了浏览器存储（Adaptation History 会一直是空的）。现在刷新时会把返回的 state
  并入并按 profile 持久化，同时保留被展示层隐藏的昨日 `check_in`，避免计算往返抹掉用户数据。
* **存储**：schema 仍为 **v3**（`adaptation_log` 是纯增量可选字段，默认 `[]`，不升版本、不重置、
  V1.2 与 V1.3 Phase 1 数据原样保留）；`pnpm check:store` 11 → **14/14**。
* **测试**：**209 / 209 PASS**（188 基线 + 12 自适应层 + 9 API）；`test_adaptive.py` 31 项、
  `test_api.py` 39 项。前端 typecheck / lint / build 全绿；V1.3 Phase 2 端到端 **31/31**、
  Phase 1 端到端 **19/19**、V1.2 功能 parity **20/20**（Chromium 与 WebKit 各一轮）；
  跨引擎响应式 **54/54**；视觉 QA 45 个 路由×视口 组合全部通过（横向溢出 0px）。
* 细节见 `docs/V1_3_ADAPTIVE_DECISION_LOOP.md`（§14–§20）。

## V1.3 最终冲刺 — In-session Calibration 与 What-if / Decision Explorer（本地未 push）

* **In-session Calibration**：Train 上出现明确的 **active session**（开始 → 进行中 → 完成 → 反馈）。
  开始时会显示 session / how hard / effort guidance / duration，并带一条独立的 **session trace**
  （PRE-SESSION DECISION → PERSONAL RESPONSE → STARTING GUIDANCE → IN-SESSION OBSERVATION →
  CALIBRATION → FINAL SESSION GUIDANCE，不并入 Today 的 Decision Trace）。
* **只问一次的可选 checkpoint**：effort（easier / as expected / harder）、representative set 的实际
  RIR（0–5 或 not sure）、performance feeling。**不再问 sleep / HRV / stress / motivation**。
* **三种结果，全部有界**：HOLD（与计划一致）；EASE（safety flag、局部酸痛 ≥4/5、RIR 低于处方区间、
  或 performance 比预期差）；OPTIONAL PUSH（readiness GREEN 且无 block，且 easier + RIR 高于处方上限 +
  performance 至少与预期一致）。**"仅 harder than expected" 视为一次硬 moment，保持 HOLD。**
* **绝对边界**：不改 demand tier（`Moderate → High`、`Low → Moderate` 均禁止）、不改 training focus /
  programme / 动作 / 组数、不加量、不抬周目标、不覆盖 safety / 酸痛 / exposure。对外公布的 scope 字符串为
  `Within the effort range already prescribed — no tier, focus, exercise or volume change`。
* **Response Episode 扩展**：BEFORE → RECOMMENDED → **CALIBRATED** → PERFORMED → POST-SESSION →
  AFTER；没有 checkpoint 的旧情节 `calibrated = null`，**不重写任何历史数据**。
* **Calibration 不会绕过学习闭环**：checkpoint **不直接**更新 Personal Response；仍然只有"反馈 + 次日
  签到"都齐的完整情节才算证据（Phase 1 契约不变）。
* **Calibration history**：每次 checkpoint 存一条精简记录（日期 / session / 起始指导 / effort / 实际 RIR /
  performance / result / reason / 更新后指导），Insights 显示最近几条与一句趋势。
* **What-if / Decision Explorer**：Today 的 "Why this recommendation" 内一个折叠面板（**不是**主导航）。
  三个 lever（更多局部酸痛 / 更差的恢复之夜 / 没有近期 poorer 响应历史），**一次只改一个输入**，
  由**同一套 deterministic engines** 重算，显示 Current / 改动内容 / Alternative / 变化点 / 原因。
  文案明确"这是规则探索器，不是预测"。
* **只读**：`POST /api/state/what-if` **不返回 state**，profile / check-in / session / Response Episode /
  Personal Response / adaptation history 均不被修改（全部在深拷贝上计算）。
* **演示（均可通过真实规则复现）**：`High` + 更高酸痛 → 同一 demand、换成更安全的 session；
  `Reduced / autoregulated`（个性化后）+ 忽略 poorer 历史 → 回到 base `Normal`。
* **Coach**：新增确定性 calibration 事实回答（今天的 calibration / 最近是否经常需要降低强度 / 刚记录的 RIR /
  为何让我降低强度），**0 次 provider 调用**；文档中的中文问法也能命中同一确定性分支（产品文案仍为英文）。
* **存储**：schema 仍为 **v3**。新增 `active_session`（默认 `null`）与每个 session 的
  `response_calibration`（默认 `null`），均为纯增量字段，不升版本、不重置；`pnpm check:store` 14 → **17/17**。
* **最终冲刺中发现并修复的真实 bug**（详见 `docs/V1_3_FINAL_QA.md` §4）：
  1. `RPE 3–4 / 10` 被解析成 `3–4 RIR` 区间（有氧路径会被拿 RIR 区间比较）—— 现在 RIR 单位是必需的；
  2. calibration 的 reason 被 `str.capitalize()` 把 "RIR" 小写成 "rir" —— 改为只大写首字母；
  3. `"increase"` 被当成关键字 `"ease"`，导致 "Why didn't you increase…" 被 calibration 分支拦截 —— 改为
     英文关键字按词边界匹配（中文仍按子串）；
  4. `calibration_service.history()` 把 pydantic `SessionRow` 当 dict 用，导致 14 个 API 测试报
     `AttributeError` —— 改为 `model_dump()` 归一化。
* **测试**：**246 / 246 PASS**（新增 `test_calibration.py` 37 项）。前端 lint / typecheck / build /
  `check:store` 全绿；最终 V1.3 journey **38/38**、Phase 1 **19/19**、Phase 2 **31/31**、
  V1.2 parity **20/20**、跨引擎 **54/54**、路由×视口 **45/45**、最终界面×5 视口 **45/45**、
  import **10/10**、API down **6/6**、API up **2/2**；console blocking errors **NONE**。
* 细节见 `docs/V1_3_ADAPTIVE_DECISION_LOOP.md`（§21–§33）与 `docs/V1_3_FINAL_QA.md`。

* Phase 4 = **发布就绪**（无新功能）：运行时配置（`frontend/.env.example` 单一样本；后端环境变量见
  `docs/V1_2_DEPLOYMENT.md`）、CORS 生产配置说明、跨引擎 QA、API/AI 不可用行为、导入安全、部署文档、
  以及必需的 ZIP 交付包。
* **测试中发现并修复的移动端问题**：表单控件在小屏统一 16px（避免 iOS 聚焦缩放）；原生 `<select>`
  改用固定高度（**WebKit 忽略 min-height，Safari 上只有 23px**）；分段控件、酸痛选择框、周目标输入框、
  档案 chip、返回链接统一到 44px 触控目标。
* Phase 4 验证（生产构建 + `next start` 实测）：跨引擎 **54/54**（Chromium + WebKit × 3 视口 × 9 路由，
  0 控制台错误）· 功能回归 Chromium **20/20**、WebKit **20/20** · 导入导出 **10/10** ·
  API 不可用 **6/6** · AI 不可用 **7/7** · Python **161/161** · 前端 typecheck / lint / build 全绿。
* **真机未验证**：无物理 iOS/Android 设备；WebKit 26.5 是 Safari 兼容引擎，不等同于真机 Safari。
  Firefox 在本机无法启动（macOS 沙箱拒绝其 plugin-container），属环境限制。
* 交付物：`Personal_Readiness_Assistant_V1.2_Phase4_Release_Candidate.zip`（已做密钥扫描与解包核验）。
* 细节见 `docs/V1_2_RELEASE_QA.md` 与 `docs/V1_2_DEPLOYMENT.md`。

* Phase 3 = **纯展示层打磨**：设计系统（graphite/off-white 中性色、四级字阶、统一间距节奏、
  Lucide 图标、统一 focus、reduced-motion）、用 `Section` 取代"卡片墙"、Today 重构为旗舰页
  （1440×900 单屏不滚动）、Coach 改为嵌入式助理版式、Insights 以 training load 领衔并新增
  "Sessions, last 14 days"、图表增加坐标刻度/当前值/hover 提示/无障碍标签、Check-in 改为
  分段控件、Profile 分组化、新增 `/profile/about`、import 改为"选择→校验→摘要→确认替换"。
* Phase 3 验证：**45/45**（5 视口 × 9 路由）无横向溢出且无控件被底栏遮挡；功能回归 **20/20**；
  Python **161/161**；前端 typecheck / lint / build 全绿；dev 日志无 React 警告。
* 细节见 `docs/V1_2_UI_POLISH.md`。

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

# Release Packaging Policy（长期有效，所有后续阶段必须遵守）

每个开发阶段（含 Adaptive Decision Loop 及之后所有阶段）结束时，**必须**产出一个干净的、
可直接下载的 ZIP 交付包，并在最终报告中列出：ZIP 文件名、ZIP 体积、密钥扫描结果、
压缩包内容核验结果、以及"是否已交付给用户可下载"。

ZIP 生成方式：`git archive --format=zip -9 -o <输出路径> HEAD`（先提交、工作树 clean，
这样归档内容**等于**最终工作树）。

ZIP 必须排除：`.git/` · `.venv/` · `node_modules/` · `.next/` · `__pycache__/` ·
`.pytest_cache/` · `.streamlit/secrets.toml` · `.env` · `.env.*`（`*.example` 示例文件保留）·
真实 API key / credentials / tokens / 浏览器缓存 / 日志 / 本地数据库 / 临时文件 / 测试截图。

创建 ZIP 前必须扫描**归档的确切文件集**（含 `DEEPSEEK_API_KEY` 赋值、`sk-*`、Bearer token、
password/credential、私钥块、AWS/GitHub token 等模式），发现真实密钥则**停止**且不得打包。
扫描不得打印任何密钥值。创建后必须：列出顶层条目、确认禁止目录与密钥文件不存在、
确认必需源文件与示例配置存在、并解包到临时目录做基本健全性检查
（至少 `python3 -m compileall .` 与 `python3 -m pytest` 在解包副本中通过）。

当前基线交付物：`Personal_Readiness_Assistant_V1.3_FINAL_Portfolio_Build.zip`（见 `docs/V1_3_FINAL_QA.md`
所在 commit 的最终报告中的体积与条目数）。它取代此前所有 V1.3 开发期 ZIP
（`Personal_Readiness_Assistant_V1.3_Phase1_Adaptive_Loop.zip`、
`Personal_Readiness_Assistant_V1.3_Phase2_Personal_Response.zip`）。

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

`python -m compileall .` → PASS；`python -m pytest -v` → **246 / 246 passed**
（139 项 Streamlit/engine 回归 + 31 项 V1.3 自适应层 `test_adaptive.py` + 39 项 FastAPI 适配层
`test_api.py` + 37 项最终冲刺 `test_calibration.py`）。

前端：`pnpm lint` · `pnpm typecheck` · `pnpm build` · `pnpm check:store`（17/17）全部 PASS。

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
20. **Base recommendation 与 final recommendation 永远分开呈现**，不得合并成一个不可解释的输出；
    base 始终是引擎自己的结论。
21. **Personal Response 不得改变 WHAT TO TRAIN、safety routing、training load、weekly exposure 或科学阈值**；
    最多只能在 readiness 已允许的程度上调整 HOW HARD，且最多一个档位。
22. **Recommendation Confidence 只能是定性状态**（Limited / Developing / Strong），
    不得显示为百分比、概率、临床信心、伤病或恢复概率，也不得影响 readiness index 或 GREEN/AMBER/RED。
23. **不得宣称产品无法执行的适应行为**。V1.3 Phase 2 已删除不可达的向上档位提升；
    任何"升档"文案都必须先证明该路径真实可达，否则必须改为档位内个性化或明确的不增加说明。
24. **演示数据必须服从产品规则**：demo case 只能展示真实规则会产生的状态，不得用与当前 demand 不匹配的数据
    伪装出某个证据状态。
25. Recency policy 只影响"哪些情节可以驱动今天"，**不得静默丢弃旧情节**——旧情节必须继续出现在 history、
    profile 计数与 Insights 中。
26. **In-session Calibration 只有三种结果**（HOLD / EASE / OPTIONAL PUSH），且**永远不得**改变 demand
    tier、training focus、programme、动作、组数、周目标，也不得覆盖 safety / 酸痛 / exposure。
27. **Calibration 不得绕过学习闭环**：checkpoint 不直接更新 Personal Response；只有"训练后反馈 + 次日签到"
    都齐的**完整**情节才能成为证据。
28. **What-if / Decision Explorer 必须使用同一套 deterministic engines**，一次只改一个输入；不得引入第二个
    推荐模型，不得让 LLM 计算结果；**不得返回或持久化任何 state**（只读模拟）。
29. **不得把 What-if 描述成预测**：文案是"当前规则下如果这个条件不同会如何决策"，禁止"系统预测你会…"。
30. **Calibration / What-if 都是透明的产品启发式**，必须如实标注，不得用引用为其具体规则背书，也不得产出
    恢复百分比、耐受分数或伤病概率。

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
* **不要把 Phase 1 的向上档位提升（`Moderate → High`）加回来**：它在真实产品路径中不可达，
  Phase 2 已用 within-tier personalization 与明确的不增加说明替代。要重新引入，必须先证明
  readiness 允许该档位，并作为显式产品决策重新评估。
* **不要给 Recommendation Confidence 加上百分比或数值分数**，也不要把它接进 readiness 计算。
* 不要在 UI 里重新计算 Personal Response 的任何数值；所有结论必须来自后端结构化字段。
* **不要给 In-session Calibration 增加第四种结果**，也不要让它改变 demand tier / focus / programme /
  动作 / 组数，或覆盖 safety / 酸痛 / exposure。
* **不要让 Calibration 直接写入 Personal Response**：学习闭环只认"反馈 + 次日签到"的完整情节。
* **不要让 What-if 返回 state、写回任何数据，或引入第二个推荐模型**；也不要把它包裝成预测。
* 不要为了展示效果而让 demo 出现真实规则无法产生的 calibration / what-if 结果。

# Product Roadmap

**CURRENT — V1.1**
Explainable Daily Training Decision；high-fidelity Streamlit functional prototype。

**DONE — V1.1 DeepSeek migration**
解释层已从本地 Qwen 迁移到 DeepSeek API（non-thinking）。deterministic decision engine、
Personal Fact Resolver、Grounding Guard 全部保留。详见 `docs/V1_1_DEEPSEEK_MIGRATION.md`。
**Live 验证已完成**：认证 / base URL / `deepseek-flash` alias / non-thinking 全部实测通过，
延迟中位数 2.9 s。live QA 发现的 readiness 量表 guard 误报（`71/100` 被当成幻觉数字）已修复，
EXPLANATION 接受率 0/5 → 4/5。剩余问题见 `docs/V1_1_DEEPSEEK_MIGRATION.md` 的 observed issues。

**DONE — V1.2 产品化与前端迁移**
Next.js + FastAPI 迁移完成，四个 Phase 全部通过；V1.2 RC 冻结在 `v1.2-nextjs-migration` = `7d21568`。
详见 `docs/V1_2_FRONTEND_MIGRATION.md`、`docs/V1_2_RELEASE_QA.md`。

**DONE — V1.3 Phase 1 Adaptive Decision Loop（已推送 `673010f`）**
Response Episodes · Post-session feedback · Next-day linking · Personal Response ·
有界向下调整（≤1 档）· Decision Trace 的 PERSONAL RESPONSE 步骤 · Coach 确定性事实回答。

**DONE — V1.3 Phase 2 Personal Response Profile & Recommendation Confidence（本地，未 push）**
Personal Response Profile（按 demand band，按 focus 需 ≥3 情节）· Recommendation Confidence
（Limited / Developing / Strong，定性、非概率）· Evidence Coverage · Consistency · Recency policy ·
Adaptation History · 不可达向上调整的诚实替代（within-tier personalization）。

**DONE — V1.3 最终冲刺（本地，待 push）**
In-session Calibration（HOLD / EASE / OPTIONAL PUSH，active session + session trace）·
What-if / Decision Explorer（同一引擎、一次只改一个输入、只读）· 闭环整合 · 最终文档与 QA。
**V1.3 到此结项。**

**NEXT — PORTFOLIO CREATION（不是产品开发）**
不再有 V1.3 产品阶段；V1.4 未获批准，不得开始。

# Adaptive Decision Loop（V1.3 已全部实现并结项）

```
Understand today → Recommend → Perform session → Observe actual response
→ Learn personal response → Improve next decision
```

产品演进主线：**Personal Baseline → Personal Response**。
Phase 1（响应情节 / 有界调整 / Decision Trace / Coach）、Phase 2（Profile / Confidence /
Coverage / Consistency / Recency / Adaptation History / within-tier）与最终冲刺的
In-session Calibration + What-if Explorer **均已实现**。

# Wearable Roadmap（FUTURE / NOT IMPLEMENTED）

Apple Health / Garmin / WHOOP / Oura 属于后期数据入口，核心价值是**降低手动输入摩擦**，
不是产品创新本身。当前 demo 不实现任何 wearable 集成。

# Production Frontend（DONE — V1.2）

已完成：Next.js 16 App Router frontend → FastAPI 无状态计算层 → 复用现有 Python engines
（readiness / recommendation / exposure / safety / Decision Trace / `ai_facts` / `ai_engine` 全部未修改）。
Streamlit V1.1 **仍然保留且可运行**，是 reference implementation，不再是日常演示路径。
细节见 `docs/V1_2_FRONTEND_MIGRATION.md` 与 `docs/V1_2_DEPLOYMENT.md`。

# New Codex Session Boot Procedure

新会话开始后：

1. 读取 `docs/CODEX_HANDOFF.md`（本文件）。
2. `git status`
3. `git branch --show-current`
4. `git log -3 --oneline`
5. 确认最新 baseline（branch / commit / tests）。
6. `python -m compileall .`
7. `python -m pytest -v`
8. 确认 test baseline（当前应为 **246 passed**：`test_app.py` 139 · `test_adaptive.py` 31 ·
   `test_api.py` 39 · `test_calibration.py` 37）。
9. **不要修改任何代码。**
10. 先汇报理解，然后等待用户的下一条指令。
