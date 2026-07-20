"""COC 7 版理智系统 — SAN 检定、疯狂阶段、恢复。

纯函数，无状态。接受 Investigator 引用，修改其 san 值。
参考 COC 7 版规则书第 6 章。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from .coc import resolve_coc, CocTestResult


class InsanityType(Enum):
    """疯狂类型"""
    NONE = "无"
    TEMPORARY = "临时疯狂"       # 单次损失 ≥5 SAN
    INDEFINITE = "不定疯狂"      # SAN 归零或单日损失 ≥20%


class SanLoss(Enum):
    """SAN 损失等级（COC 7 版规则书表）"""
    TRIVIAL = (0, (1,))          # 日常惊吓
    MINOR = (1, (1, 2))          # 看到尸体
    MODERATE = (2, (1, 3))       # 看到血腥现场
    MAJOR = (3, (1, 4))          # 看到怪物
    SEVERE = (4, (1, 6))         # 目睹同伴死亡
    EXTREME = (5, (2, 10))       # 直面旧日支配者
    CALAMITOUS = (6, (4, 20))    # 克苏鲁本尊

    def __init__(self, _order: int, loss_range: tuple[int, int]):
        self.loss_range = loss_range

    def roll_loss(self, rng: random.Random | None = None) -> int:
        """随机掷 SAN 损失值。"""
        rng = rng or random.Random()
        lo, hi = self.loss_range
        return rng.randint(lo, hi)


# 临时疯狂症状表（d10）
_TEMP_INSANITY_TABLE = [
    "失忆：调查员对刚刚发生的事情毫无记忆，仿佛被抹去了一般。",
    "恐惧症：调查员对当前场景中的某个元素产生极度恐惧，必须远离。",
    "暴力倾向：调查员无法自控地向最近的生物发起攻击。",
    "偏执妄想：调查员坚信身边的某个人是敌人/怪物伪装的。",
    "重要之人幻觉：调查员看到已故或远方的至亲，试图与其互动。",
    "昏厥：调查员当场失去意识，1d10 分钟后醒来。",
    "逃跑冲动：调查员不顾一切地逃离当前场景。",
    "歇斯底里：调查员大笑、哭泣或尖叫，无法正常行动。",
    "强迫行为：调查员反复做某个动作（洗手、祈祷、数数）。",
    "抽搐/僵直：调查员身体不受控制地颤抖或僵住。",
]

# 不定疯狂症状表（d10）
_INDEF_INSANITY_TABLE = [
    "失忆症：调查员对某段重要记忆完全空白，包括自己是谁。",
    "多重人格：出现第二人格，与原本性格截然不同。",
    "偏执狂：坚信某种阴谋正在针对自己，不信任任何人。",
    "强迫症：每天必须完成某个仪式性行为，否则陷入恐慌。",
    "恐惧症：对特定事物产生极度恐惧，接触时需 SAN 检定。",
    "幻觉：不定期看到或听到不存在的事物，真假难辨。",
    "抑郁症：失去行动意愿，做任何事都需要意志检定。",
    "躁狂症：精力过剩但注意力涣散，无法专注超过几分钟。",
    "反社会人格：失去共情能力，为达目的不择手段。",
    "自杀倾向：在不经意间将自己置于危险之中。",
]


@dataclass(frozen=True, slots=True)
class SanCheckResult:
    """SAN 检定结果"""

    san_before: int
    san_after: int
    loss: int                     # 实际损失的 SAN
    check: CocTestResult | None   # SAN 检定结果（成功时不损失则 None）
    insanity_type: InsanityType
    symptom: str = ""             # 疯狂症状描述（如有）
    description: str = ""         # KP 叙述用文本

    @property
    def went_insane(self) -> bool:
        return self.insanity_type != InsanityType.NONE


def san_check(
    san_value: int,
    loss_level: SanLoss,
    *,
    rng: random.Random | None = None,
) -> SanCheckResult:
    """执行 SAN 检定。

    COC 7 版规则：
    1. 掷 d100 ≤ 当前 SAN → 检定成功，SAN 损失最小化（见 loss_level 最小值）
    2. 掷 d100 > 当前 SAN → 检定失败，掷 loss_level 完整损失
    3. 单次损失 ≥5 → 临时疯狂
    4. SAN 归零 → 不定疯狂

    Args:
        san_value: 当前 SAN 值
        loss_level: SAN 损失等级
        rng: 随机数生成器

    Returns:
        SanCheckResult 包含损失、疯狂判定和 KP 叙述文本
    """
    rng = rng or random.Random()
    roll = rng.randint(1, 100)

    passed = roll <= san_value
    lo, hi = loss_level.loss_range
    loss = lo if passed else rng.randint(lo, hi)

    new_san = max(0, san_value - loss)

    # 疯狂判定
    insanity_type = InsanityType.NONE
    symptom = ""

    if new_san <= 0:
        insanity_type = InsanityType.INDEFINITE
        idx = rng.randint(0, len(_INDEF_INSANITY_TABLE) - 1)
        symptom = _INDEF_INSANITY_TABLE[idx]
    elif loss >= 5:
        insanity_type = InsanityType.TEMPORARY
        idx = rng.randint(0, len(_TEMP_INSANITY_TABLE) - 1)
        symptom = _TEMP_INSANITY_TABLE[idx]

    # 生成 KP 叙述文本
    desc_parts = [f"SAN 检定 {'成功' if passed else '失败'}（骰值 {roll} ≤ {san_value}）"]
    desc_parts.append(f"SAN: {san_value} → {new_san}（-{loss}）")

    if insanity_type == InsanityType.TEMPORARY:
        desc_parts.append(f"触发临时疯狂：{symptom}")
    elif insanity_type == InsanityType.INDEFINITE:
        desc_parts.append(f"触发不定疯狂：{symptom}")

    return SanCheckResult(
        san_before=san_value,
        san_after=new_san,
        loss=loss,
        check=None,  # simplified — no full CocTestResult needed
        insanity_type=insanity_type,
        symptom=symptom,
        description="；".join(desc_parts),
    )


def san_reward(san_value: int, amount: int, max_san: int = 99) -> tuple[int, str]:
    """SAN 奖励——完成冒险、击败怪物等正面事件恢复 SAN。

    Returns:
        (new_san, description)
    """
    new_san = min(max_san, san_value + amount)
    gained = new_san - san_value
    return new_san, f"SAN 恢复 +{gained}：{san_value} → {new_san}"


def daily_san_loss_check(
    san_value: int,
    max_san: int,
    total_daily_loss: int,
) -> bool:
    """检查是否触发不定疯狂（单日损失 ≥ 起始 SAN 的 20%）。

    Returns:
        True 如果触发不定疯狂
    """
    threshold = max_san // 5
    return total_daily_loss >= threshold
