# TRPG Agent — 中文 COC 跑团 KP

本地 AI 主持人，跑《克苏鲁的呼唤》。你说，它听，然后以守秘人的身份回答——全部本地运行，零 API 成本。

> **状态：Phase 2 完成** — 游戏状态、多轮记忆、Session 管理器就绪。5 轮实测验证记忆跨轮保持。

## 怎么跑

```bash
git clone https://github.com/Gousting/trpg-agent.git
cd trpg-agent
uv sync
cp .env.example .env   # 编辑 OLLAMA_HOST 指向你的 Ollama
uv run python tests/test_session.py   # Phase 2 多轮记忆测试
```

前提：Ollama 运行中，已 pull 模型（默认 gemma4:12b）。

```bash
uv run pytest tests/ -v   # 39 项单元测试
```

## 架构

借鉴 [DMbot](https://github.com/Pr0degie/dungeonmaster) 的架构范式——"LLM 提议叙事，代码拥有硬状态"。

```
玩家输入 → [Ollama] → 中文 KP 回答 → sanitize 清洗 → 输出
                ↑
         system prompt（KP 人格 + 世界状态 + 前情提要）
                ↑
         Session 管理器（角色卡 + 对话历史 + 上下文窗口）
```

**Phase 2 新增：**

- **`session.py`** — Session 管理器。加载角色卡、管理对话历史、监控上下文窗口（超限触发 recap 压缩）、组装完整 system prompt
- **`memory/game_state.py`** — COC 游戏状态。调查员（HP/SAN/Luck）、NPC（态度量表）、场景/任务、原子持久化
- **`memory/history.py`** — 对话历史存储。JSONL 追加写入，支持查询/裁剪/清空

## 文件状态

| 模块 | 状态 | 说明 |
|------|------|------|
| `llm/sanitize.py` | ✅ | 中文 KP 回答清洗 (12 项正则) |
| `prompts/kp_core_zh.md` | ✅ | 守秘人核心人格 (2587 字) |
| `rules/coc.py` | ✅ | COC 检定引擎 |
| `rules/engine.py` | ✅ | 通用掷骰引擎 |
| `llm/client.py` | ✅ | Ollama 异步客户端 |
| `session.py` | ✅ | Session 管理器 (Phase 2) |
| `memory/game_state.py` | ✅ | COC 游戏状态 (Phase 2) |
| `memory/history.py` | ✅ | 对话历史 (Phase 2) |
| `tests/test_unit.py` | ✅ | 39 项单元测试 |
| `tests/test_session.py` | ✅ | 5 轮记忆集成测试 |
| 其他 24 个文件 | 🔧 | 搬运自 DMbot，待后续 Phase 中文化 |

## 迭代路线

详见 [ROADMAP.md](ROADMAP.md)。
Phase 1 纯文字闭环 ✅ · Phase 2 游戏状态与多轮记忆 ✅ · Phase 3 掷骰路由 → Phase 6 平板客户端。

## 许可

MIT
