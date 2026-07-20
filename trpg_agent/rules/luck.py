"""幸运值系统 — 消耗幸运调整检定结果。

COC 7 版规则：调查员可以消耗幸运值，以 1:1 的比例降低检定骰值
（即每消耗 1 点幸运，检定结果减 1），从而将失败扭转为成功。
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LuckResult:
    """幸运消耗结果"""

    luck_before: int
    luck_after: int
    spent: int
    roll_before: int           # 原始骰值
    roll_after: int            # 调整后的骰值
    target: int                # 目标值
    was_success: bool          # 原始结果
    is_success: bool           # 调整后结果
    description: str


def spend_luck(
    current_luck: int,
    roll_value: int,
    target_value: int,
    *,
    rng: random.Random | None = None,
) -> LuckResult:
    """消耗幸运值降低检定骰值。

    调查员可以消耗任意数量的幸运值（不超过当前幸运值），
    每消耗 1 点幸运降低骰值 1 点。幸运不能降低到产生大成功（即骰值不能降到 <1）。

    Args:
        current_luck: 当前幸运值
        roll_value: 原始 d100 骰值
        target_value: 目标值（技能值或有效目标值）

    Returns:
        LuckResult 包含调整后的骰值和是否成功
    """
    was_success = roll_value <= target_value
    if was_success:
        return LuckResult(
            luck_before=current_luck,
            luck_after=current_luck,
            spent=0,
            roll_before=roll_value,
            roll_after=roll_value,
            target=target_value,
            was_success=True,
            is_success=True,
            description="检定已成功，无需消耗幸运。",
        )

    # 计算需要多少幸运才能成功
    needed = roll_value - target_value
    if needed <= 0:
        return LuckResult(
            luck_before=current_luck, luck_after=current_luck, spent=0,
            roll_before=roll_value, roll_after=roll_value, target=target_value,
            was_success=True, is_success=True,
            description="检定已成功，无需消耗幸运。",
        )

    # 可花费的幸运值（不能超过当前值，不能调整到 1 以下）
    max_spendable = min(current_luck, roll_value - 1)
    spent = min(needed, max_spendable)
    new_roll = roll_value - spent
    new_luck = current_luck - spent
    is_success = new_roll <= target_value

    if spent > 0 and is_success:
        desc = f"消耗 {spent} 点幸运，骰值 {roll_value} → {new_roll} ≤ {target_value}，扭转为成功。"
    elif spent > 0:
        desc = f"消耗 {spent} 点幸运仍不足以成功（骰值 {roll_value} → {new_roll}，目标 {target_value}）。"
    else:
        desc = f"幸运不足，无法调整（当前幸运 {current_luck}，需要至少 {needed} 点）。"

    return LuckResult(
        luck_before=current_luck,
        luck_after=new_luck,
        spent=spent,
        roll_before=roll_value,
        roll_after=new_roll,
        target=target_value,
        was_success=was_success,
        is_success=is_success,
        description=desc,
    )


def luck_recovery(current_luck: int, *, rng: random.Random | None = None) -> tuple[int, str]:
    """每次游戏结束时进行幸运恢复检定。

    掷 d100，若 > 当前幸运值则恢复 1d10 点幸运。
    """
    rng = rng or random.Random()
    roll = rng.randint(1, 100)
    if roll > current_luck:
        gained = rng.randint(1, 10)
        return current_luck + gained, f"幸运恢复检定成功（骰值 {roll} > {current_luck}），恢复 {gained} 点幸运。"
    return current_luck, f"幸运恢复检定失败（骰值 {roll} ≤ {current_luck}）。"
