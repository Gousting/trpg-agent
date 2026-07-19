# TRPG Agent — 文件状态清单

基于 DMbot (Pr0degie/dungeonmaster) 搬运，为中文 COC 跑团适配。

## 状态标记

- ✅ 直接可用 / 已完成中文化
- 🔧 需要中文翻译（代码逻辑干净，德语文本需替换）
- 🚧 需要架构适配（Discord/WH40k/德语解耦后可用）
- ❌ 待重写/废弃

---

## Phase 1 完成

| 文件 | 状态 | 说明 |
|------|------|------|
| `llm/sanitize.py` | ✅ | 中文 KP 回答清洗 (12 项正则模式) |
| `prompts/kp_core_zh.md` | ✅ | 守秘人核心人格 (52 行, 2587 字) |
| `rules/coc.py` | ✅ | COC 7 版检定引擎 (常规/困难/极难) |
| `rules/engine.py` | ✅ | 通用掷骰引擎 |
| `llm/client.py` | ✅ | Ollama 异步客户端 |
| `llm/persona.py` | ✅ | 中文 prompt 加载 |
| `llm/prompt_assembly.py` | ✅ | Prompt 组装 (前情提要) |
| `data/systems/coc_7e.json` | ✅ | COC 规则系统 Profile |
| `tests/test_unit.py` | ✅ | 39 项单元测试 |
| `tests/test_pipeline.py` | ✅ | 全链路集成测试 |

## Phase 2 完成

| 文件 | 状态 | 说明 |
|------|------|------|
| `session.py` | ✅ | Session 管理器 (角色加载/历史/上下文/prompt/检定路由) |
| `memory/game_state.py` | ✅ | COC 游戏状态 (Investigator/Npc/Quest/GameState) |
| `memory/history.py` | ✅ | 对话历史 (重写为 HistoryStore 类) |
| `data/sessions/default/characters.json` | ✅ | 示例角色卡 (3 调查员 + 2 NPC) |
| `tests/test_session.py` | ✅ | 5 轮集成测试 (记忆+检定路由) |

## Phase 3 完成

| 文件 | 状态 | 说明 |
|------|------|------|
| `llm/roll_router.py` | ✅ | 检定分类器 (中文化, constrained JSON) |

## 未处理 — DMbot 遗留文件

### LLM 模块

| 文件 | 状态 | 说明 |
|------|------|------|
| `llm/consistency.py` | 🔧 | 一致性守卫，德语动词判断→中文方案 |
| `llm/echo_guard.py` | 🔧 | 回声守卫 |
| `llm/intro_guard.py` | 🔧 | 开场守卫 |
| `llm/director_msgs.py` | 🔧 | DM 开场引导 |
| `llm/stream_assembler.py` | 🚧 | 流式组装器，依赖 sanitize/marker/textsplit |

### 规则模块

| 文件 | 状态 | 说明 |
|------|------|------|
| `rules/marker.py` | 🔧 | 标记解析 |
| `rules/characters.py` | 🚧 | 角色系统，psyker→删 |
| `rules/combat.py` | 🚧 | 战斗模块，Warp Charge→删 |
| `rules/summary.py` | 🔧 | 规则摘要，德语→中文 |

### 记忆模块

| 文件 | 状态 | 说明 |
|------|------|------|
| `memory/state.py` | ❌ | 已被 game_state.py 替代，可废弃 |
| `memory/chekhov.py` | 🔧 | Chekhov 清单，待 Phase 4 |
| `memory/npc_memory.py` | 🔧 | NPC 记忆，待 Phase 4 |
| `memory/recap.py` | 🔧 | Recap 生成，待 Phase 4 |
| `memory/gametime.py` | 🔧 | 游戏内时间 |

### 其他

| 文件 | 状态 | 说明 |
|------|------|------|
| `orchestrator.py` | 🚧 | DMBrain，Discord 解耦后可用 |
| `logsetup.py` | ✅ | 日志配置 |
| `turn_timing.py` | ✅ | 回合计时 |
| `shutdown.py` | ✅ | 优雅关闭 |
| `tts/textsplit.py` | 🔧 | TTS 文本分割，待 Phase 5 |

### Prompt 文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `prompts/campaign_tone_de.md` | ❌ | WH40k 基调，丢弃 |
| `prompts/chekhov_extract_de.md` | 🔧 | Chekhov 提取，待 Phase 4 |
| `prompts/npc_memory_extract_de.md` | 🔧 | NPC 记忆提取，待 Phase 4 |
| `prompts/dm_core_de.md` | ❌ | 已被 kp_core_zh.md 替代 |
