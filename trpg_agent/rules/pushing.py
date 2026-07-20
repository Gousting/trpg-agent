"""孤注一掷（Pushing Rolls）— 失败检定的重试机制。

COC 7 版规则：调查员可以声明"孤注一掷"，重试失败的技能检定。
但必须描述不同的尝试方式，且失败的后果更加严重。
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .coc import resolve_coc, CocTestResult, SuccessLevel


@dataclass(frozen=True, slots=True)
class PushResult:
    """孤注一掷的结果"""

    original: CocTestResult       # 原始检定
    pushed: CocTestResult         # 重试检定
    was_pushed: bool              # 是否实际执行了重试
    description: str


def can_push(original: CocTestResult) -> bool:
    """判断是否可以孤注一掷。

    条件：
    - 检定失败（非大失败——大失败不能重试）
    - 技能值 > 0
    """
    if original.is_fumble:
        return False
    if original.success:
        return False
    return original.skill_value > 0


def push_roll(
    skill_value: int,
    difficulty: str = "常规",
    *,
    previous_result: CocTestResult | None = None,
    rng: random.Random | None = None,
) -> PushResult:
    """执行孤注一掷。

    先检查是否可以重试，然后重新掷骰。
    如果原始检定已经成功或是大失败，直接返回原结果。

    Args:
        skill_value: 技能值
        difficulty: 难度
        previous_result: 上一次检定的结果（用于判断是否可以重试）
        rng: 随机数生成器

    Returns:
        PushResult
    """
    rng = rng or random.Random()

    if previous_result is not None:
        if not can_push(previous_result):
            return PushResult(
                original=previous_result,
                pushed=previous_result,
                was_pushed=False,
                description=(
                    "大失败无法孤注一掷。"
                    if previous_result.is_fumble
                    else "检定已成功，无需孤注一掷。"
                ),
            )

    # 执行孤注一掷
    pushed = resolve_coc(skill_value, difficulty, rng=rng)

    # 孤注一掷失败 → 后果更严重
    if not pushed.success:
        if pushed.is_fumble:
            desc = (
                f"孤注一掷大失败（骰值 {pushed.roll}）！"
                f"后果极其严重——不仅失败，还可能造成额外伤害或失控。"
            )
        else:
            desc = (
                f"孤注一掷失败（骰值 {pushed.roll} > {pushed.target}）。"
                f"比普通失败更糟——KP 应给予额外的负面后果。"
            )
    else:
        level_text = pushed.level.value
        desc = f"孤注一掷成功——{level_text}（骰值 {pushed.roll} ≤ {pushed.target}）"

    orig = previous_result or CocTestResult(
        roll=0, skill_value=skill_value, difficulty=difficulty,
        target=skill_value, success=False, level=SuccessLevel.FAILURE,
        is_critical=False, is_fumble=False,
    )

    return PushResult(
        original=orig,
        pushed=pushed,
        was_pushed=True,
        description=desc,
    )
