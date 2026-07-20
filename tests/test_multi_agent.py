"""多智能体 COC 跑团 — 一个 KP 模型 + 多个玩家模型自动跑团。

用法:
    uv run python tests/test_multi_agent.py
    # 或指定参数
    uv run python tests/test_multi_agent.py --turns 20 --kp qwen3.6:27b --players qwen3:14b,gemma4:12b

前提: Ollama 运行中，至少 2 个模型可用。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

# 项目根目录
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trpg_agent.session import Session
from trpg_agent.llm.client import OllamaClient
from trpg_agent.memory.game_state import Investigator


# ═══════════════════════════════════════════════════════════════════
# 调查员定义（性格驱动行为差异）
# ═══════════════════════════════════════════════════════════════════

DEFAULT_INVESTIGATORS = [
    {
        "name": "陈明",
        "hp": 12, "max_hp": 12, "san": 60, "max_san": 60, "luck": 50,
        "skills": {"侦查": 60, "图书馆": 50, "说服": 40, "格斗": 50, "潜行": 45},
        "inventory": ["手电筒", "警徽"],
        "personality": "退役刑警，沉默寡言但观察力极强。说话简短直接，遇到危险第一反应是保护队友。",
    },
    {
        "name": "林晓",
        "hp": 10, "max_hp": 10, "san": 70, "max_san": 70, "luck": 45,
        "skills": {"医学": 65, "急救": 60, "心理学": 50, "闪避": 40, "神秘学": 30},
        "inventory": ["急救包", "笔记本"],
        "personality": "年轻法医，好奇心旺盛到近乎鲁莽。喜欢追根究底、记笔记，紧张时会碎碎念。",
    },
    {
        "name": "王刚",
        "hp": 15, "max_hp": 15, "san": 40, "max_san": 40, "luck": 55,
        "skills": {"格斗": 70, "投掷": 50, "攀爬": 55, "恐吓": 45, "急救": 30},
        "inventory": ["棒球棍", "打火机", "香烟"],
        "personality": "码头工人，身强力壮但神经大条。用拳头思考，天不怕地不怕，但对超自然事物本能排斥。",
    },
]

OPENING_SCENE = (
    "1928年深秋，阿卡姆市郊外废弃的松林疗养院。"
    "你们各自收到一封没有署名的信，约在此地见面。"
    "疗养院大门虚掩，二楼窗户透出微弱的油灯光芒。"
    "空气中有股说不出的腐臭味。"
)


# ═══════════════════════════════════════════════════════════════════
# Ollama 工具
# ═══════════════════════════════════════════════════════════════════

async def list_models(host: str) -> list[str]:
    """列出 Ollama 可用模型名，按大小降序。"""
    async with httpx.AsyncClient(timeout=5) as cl:
        resp = await cl.get(f"{host}/api/tags")
        models = resp.json().get("models", [])
        models.sort(key=lambda m: m["size"], reverse=True)
        return [m["name"] for m in models]


# ═══════════════════════════════════════════════════════════════════
# 智能体 prompt
# ═══════════════════════════════════════════════════════════════════

PLAYER_SYSTEM = """你是 {name}，正在参与一个克苏鲁的呼唤桌面角色扮演游戏。

## 你的角色
- 性格：{personality}
- 当前状态：HP {hp}/{max_hp}, SAN {san}/{max_san}, LUCK {luck}
- 技能：{skills}
- 携带物品：{inventory}
- 异常状态：{conditions}

## 游戏规则
1. 主持人的最新叙述描述了当前的场景和局势
2. 你只描述 {name} 的行动——不说话替别人，不替 KP 描述结果
3. 用第一人称，1-3句话，直接描述行动
4. 不要以"我想"、"我要"、"我决定"开头
5. 行动要符合你的性格和技能
6. 可以对其他调查员说话或互动
7. 你不知道超出角色认知的信息"""

KP_SYSTEM = """你是克苏鲁的呼唤（COC 7版）的主持人。

{scene}

## 规则
1. 你只操控世界、NPC和环境——不对调查员说话、思考或行动
2. 描述场景、NPC反应和事件结果，让调查员的行动推动剧情
3. 保持恐怖氛围，不要急着揭示真相
4. 用中文，散文风格，不要用项目符号"""


# ═══════════════════════════════════════════════════════════════════
# 核心循环
# ═══════════════════════════════════════════════════════════════════

async def player_act(
    client: OllamaClient,
    inv_data: dict,
    inv_state: Investigator,
    kp_narration: str,
) -> str:
    """玩家模型根据 KP 叙述生成行动。"""
    prompt = PLAYER_SYSTEM.format(
        name=inv_data["name"],
        personality=inv_data["personality"],
        hp=inv_state.hp, max_hp=inv_state.max_hp,
        san=inv_state.san, max_san=inv_state.max_san,
        luck=inv_state.luck,
        skills=json.dumps(inv_state.skills, ensure_ascii=False),
        inventory=", ".join(inv_state.inventory) if inv_state.inventory else "无",
        conditions=", ".join(inv_state.conditions) if inv_state.conditions else "无",
    )
    user_msg = f"""主持人的最新叙述：
---
{kp_narration}
---
请描述 {inv_data['name']} 的下一步行动。"""

    try:
        response = await client.chat(
            prompt,
            [{"role": "user", "content": user_msg}],
            options={"temperature": 0.85, "num_predict": 200},
        )
        return response.strip()
    except Exception as e:
        return f"（{inv_data['name']} 犹豫了一下）"


async def kp_narrate(
    client: OllamaClient,
    session: Session,
    player_action: str,
    speaker: str,
    scene_text: str,
) -> str:
    """KP 模型根据玩家行动生成叙述。"""
    prompt = KP_SYSTEM.format(scene=scene_text)
    messages = session.build_messages(player_action, speaker=speaker)
    messages.insert(0, {"role": "system", "content": prompt})

    try:
        response = await client.chat(
            prompt,
            messages,
            options={"temperature": 0.75, "num_predict": 500},
        )
        return response.strip()
    except Exception:
        return "（KP 陷入了沉思……）"


def build_scene_text(session: Session) -> str:
    """生成当前场景描述文本。"""
    parts = [session.state.scene_summary()]
    if session.state.recap:
        parts.insert(0, f"前情提要：{session.state.recap}")
    return "\n\n".join(parts)


async def run_game(
    host: str,
    kp_model: str,
    player_models: list[str],
    turns: int,
    data_dir: Path | None = None,
) -> None:
    """主游戏循环。"""
    # ── 初始化 ──────────────────────────────────────
    print("🔌 连接 Ollama...")
    available = await list_models(host)
    print(f"   可用模型: {', '.join(available[:8])}")

    # 验证模型
    for m in [kp_model] + player_models:
        if m not in available:
            print(f"❌ 模型 '{m}' 不可用")
            return
        base = m.split(":")[0]
        if base != m and m not in available:
            matched = [a for a in available if a.startswith(base)]
            print(f"⚠️  '{m}' 不可用，可用: {matched}")

    # 智能体
    kp_client = OllamaClient(host, kp_model, num_ctx=8192)
    player_clients = {
        inv["name"]: OllamaClient(host, inv["model"], num_ctx=4096)
        for inv in DEFAULT_INVESTIGATORS
    }

    # Session
    session = Session("multi_agent_demo", data_dir=data_dir)
    for inv_data in DEFAULT_INVESTIGATORS:
        inv = Investigator(
            name=inv_data["name"],
            hp=inv_data["hp"], max_hp=inv_data["max_hp"],
            san=inv_data["san"], max_san=inv_data["max_san"],
            luck=inv_data["luck"],
            skills=inv_data["skills"],
            inventory=list(inv_data.get("inventory", [])),
        )
        session.state.investigators.append(inv)
    session.state.location = "废弃的松林疗养院门前"

    # ── 标题 ────────────────────────────────────────
    print()
    print("=" * 64)
    print("🎭  多智能体 COC 跑团")
    print(f"   KP: {kp_model}")
    for inv in DEFAULT_INVESTIGATORS:
        print(f"   🎲 {inv['name']} ({inv['model']}) — {inv['personality'][:30]}...")
    print(f"   回合数: {turns}")
    print("=" * 64)

    # ── KP 开场 ─────────────────────────────────────
    opening_prompt = KP_SYSTEM.format(
        scene=f"开场场景：{OPENING_SCENE}\n\n调查员：{', '.join(inv['name'] for inv in DEFAULT_INVESTIGATORS)}"
    )
    opening_msg = "请开始游戏，描述调查员们到达疗养院时的场景。"
    opening = await kp_client.chat(
        opening_prompt,
        [{"role": "user", "content": opening_msg}],
        options={"temperature": 0.8, "num_predict": 400},
    )
    opening = opening.strip()
    session.record_turn("(游戏开始)", opening)
    last_narration = opening
    print(f"\n📖 KP 开场:\n{opening}\n")

    # ── 游戏循环 ────────────────────────────────────
    player_order = [inv["name"] for inv in DEFAULT_INVESTIGATORS]
    for turn in range(turns):
        speaker = player_order[turn % len(player_order)]
        inv_data = next(inv for inv in DEFAULT_INVESTIGATORS if inv["name"] == speaker)
        inv_state = session.state.find_investigator(speaker)

        # 玩家行动
        action = await player_act(
            player_clients[speaker], inv_data, inv_state, last_narration,
        )
        print(f"🎲 {speaker}:\n   {action}\n")

        # KP 回应
        scene = build_scene_text(session)
        narration = await kp_narrate(
            kp_client, session, action, speaker, scene,
        )
        session.record_turn(action, narration, speaker=speaker)
        last_narration = narration
        print(f"📖 KP:\n{narration}\n")
        print("-" * 48 + "\n")

    # ── 结束 ────────────────────────────────────────
    session.save_game("demo_final")
    print("=" * 64)
    print(session.loaded_state_summary())
    print("=" * 64)
    print(f"\n💾 存档: demo_final ({session.state.turn_count} 轮)")


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="多智能体 COC 跑团")
    parser.add_argument("--host", default="http://192.168.0.104:11434",
                        help="Ollama 地址")
    parser.add_argument("--kp", default="qwen3.6:27b",
                        help="KP 模型名")
    parser.add_argument("--players", default="qwen3:14b,gemma4:12b",
                        help="玩家模型名（逗号分隔）")
    parser.add_argument("--turns", type=int, default=10,
                        help="总回合数")
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="数据目录")
    args = parser.parse_args()

    player_models = [m.strip() for m in args.players.split(",")]

    # 分配模型给调查员（模型数少于调查员时循环使用）
    for i, inv in enumerate(DEFAULT_INVESTIGATORS):
        inv["model"] = player_models[i % len(player_models)]

    asyncio.run(run_game(
        host=args.host,
        kp_model=args.kp,
        player_models=player_models,
        turns=args.turns,
        data_dir=args.data_dir,
    ))


if __name__ == "__main__":
    main()
