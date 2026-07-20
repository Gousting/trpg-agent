"""COC 7 版战斗系统 — 回合制结算，包括格斗/射击/闪避/伤害。

纯函数，无状态。参考 COC 7 版规则书第 4 章。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from .engine import roll


class ActionType(Enum):
    """战斗行动类型"""
    FIGHTING = "格斗"        # 格斗（近战）反击
    FIGHTING_BACK = "反击"   # 格斗反击（对抗）
    FIREARMS = "射击"       # 枪械/远程
    DODGE = "闪避"          # 闪避
    MANEUVER = "战技"       # 战技（擒抱等）


@dataclass(frozen=True, slots=True)
class AttackResult:
    """一次攻击的结算结果"""

    attacker: str
    defender: str
    action: ActionType
    attack_roll: int           # 攻击骰值 (1-100)
    attack_skill: int          # 攻击技能值
    attack_success: bool
    attack_level: str          # "大成功" / "极难成功" / "困难成功" / "常规成功" / "失败" / "大失败"

    defense_roll: int | None = None       # 防守骰值（如闪避）
    defense_skill: int | None = None      # 防守技能值
    defense_success: bool = False

    damage_roll: int = 0
    damage_bonus: int = 0
    total_damage: int = 0

    description: str = ""


def _coc_success_level(face: int, skill: int) -> tuple[bool, str]:
    """判断 COC 成功等级。

    Returns:
        (success, level_name)
    """
    if face == 1:
        return True, "大成功"
    if skill < 50 and face >= 96:
        return False, "大失败"
    if face == 100:
        return False, "大失败"
    if face <= skill // 5:
        return True, "极难成功"
    if face <= skill // 2:
        return True, "困难成功"
    if face <= skill:
        return True, "常规成功"
    return False, "失败"


def resolve_attack(
    attacker: str,
    defender: str,
    attack_type: ActionType,
    attack_skill: int,
    *,
    defense_type: ActionType | None = None,
    defense_skill: int | None = None,
    damage_dice: str = "1d3",
    damage_bonus: int = 0,
    impale: bool = False,       # 贯穿（极难成功时的额外伤害）
    rng: random.Random | None = None,
) -> AttackResult:
    """结算单次攻击。

    COC 战斗流程：
    1. 攻击方掷 d100 ≤ 攻击技能
    2. 防守方可选：闪避 或 反击（格斗对抗）
    3. 命中时掷伤害
    4. 极难成功触发贯穿（impale）

    Args:
        attacker: 攻击方名字
        defender: 防守方名字
        attack_type: 攻击动作类型
        attack_skill: 攻击技能值
        defense_type: 防守动作类型（None 表示不防守）
        defense_skill: 防守技能值
        damage_dice: 伤害骰表达式（如 "1d6", "1d3+1"）
        damage_bonus: 伤害加值
        impale: 是否允许贯穿
        rng: 随机数生成器

    Returns:
        AttackResult
    """
    rng = rng or random.Random()

    # 攻击掷骰
    atk_face = rng.randint(1, 100)
    atk_success, atk_level = _coc_success_level(atk_face, attack_skill)

    # 防守掷骰
    def_roll = None
    def_success = False
    if defense_type is not None and defense_skill is not None:
        def_roll = rng.randint(1, 100)
        def_success, _ = _coc_success_level(def_roll, defense_skill)

        # 闪避：防守成功则攻击完全落空
        # 反击：对抗——双方都成功则比较成功等级
        if defense_type == ActionType.DODGE:
            if def_success:
                atk_success = False  # 闪避成功，攻击落空
        elif defense_type == ActionType.FIGHTING_BACK:
            if def_success and not atk_success:
                pass  # 防守成功但攻击本就不中
            elif def_success and atk_success:
                # 双方都成功：比较成功等级 → 简化：50% 概率攻击命中
                if rng.random() < 0.5:
                    atk_success = False

    # 伤害掷骰
    total_damage = 0
    damage_roll = 0
    if atk_success and atk_level != "大失败":
        dmg_result = roll(damage_dice, rng)
        damage_roll = dmg_result.total

        # 贯穿：极难成功时武器伤害取满
        if impale and atk_level == "极难成功":
            # 取骰子最大值
            damage_roll = _max_damage(damage_dice)

        total_damage = max(0, damage_roll + damage_bonus)

    # 生成描述
    if atk_level == "大失败":
        desc = f"{attacker} 攻击大失败（骰值 {atk_face}）！武器可能脱手或伤及自身。"
    elif not atk_success and def_roll is not None and def_success:
        if defense_type == ActionType.DODGE:
            desc = f"{defender} 闪避成功（骰值 {def_roll}），躲开了 {attacker} 的攻击（骰值 {atk_face}）。"
        else:
            desc = f"{defender} 反击成功（骰值 {def_roll}），格挡住了 {attacker} 的攻击（骰值 {atk_face}）。"
    elif not atk_success:
        desc = f"{attacker} 攻击未命中（骰值 {atk_face}，技能 {attack_skill}）。"
    else:
        level_text = f"（{atk_level}）" if atk_level != "常规成功" else ""
        desc = f"{attacker} 攻击命中{level_text}（骰值 {atk_face}），造成 {total_damage} 点伤害"
        if impale and atk_level == "极难成功":
            desc += " [贯穿]"

    return AttackResult(
        attacker=attacker,
        defender=defender,
        action=attack_type,
        attack_roll=atk_face,
        attack_skill=attack_skill,
        attack_success=atk_success and atk_level != "大失败",
        attack_level=atk_level,
        defense_roll=def_roll,
        defense_skill=defense_skill,
        defense_success=def_success,
        damage_roll=damage_roll,
        damage_bonus=damage_bonus,
        total_damage=total_damage,
        description=desc,
    )


def _max_damage(dice_expr: str) -> int:
    """计算骰子表达式的最大可能值。"""
    total = 0
    bonus = 0
    if "+" in dice_expr:
        dice_expr, bonus_str = dice_expr.rsplit("+", 1)
        bonus = int(bonus_str.strip())
    elif "-" in dice_expr:
        dice_expr, bonus_str = dice_expr.rsplit("-", 1)
        bonus = -int(bonus_str.strip())

    parts = dice_expr.strip().split("d")
    if len(parts) == 2:
        count = int(parts[0])
        sides = int(parts[1])
        total = count * sides
    return total + bonus
