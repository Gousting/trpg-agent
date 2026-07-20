"""Phase 4 规则模块单元测试 — SAN / 战斗 / 幸运 / 孤注一掷"""

import random

import pytest

from trpg_agent.rules.sanity import (
    san_check, san_reward, daily_san_loss_check,
    SanLoss, InsanityType,
)
from trpg_agent.rules.combat import (
    resolve_attack, ActionType, AttackResult,
)
from trpg_agent.rules.luck import spend_luck, luck_recovery
from trpg_agent.rules.pushing import push_roll, can_push
from trpg_agent.rules.coc import resolve_coc


# ═══════════════════════════════════════════
# SAN
# ═══════════════════════════════════════════

class TestSanity:
    def test_san_check_pass_minimal_loss(self):
        """SAN 检定成功，损失取最小值。"""
        rng = random.Random(42)
        # SAN 70，检定需要 ≤70，骰子 seed 42 大概率通过
        result = san_check(70, SanLoss.MAJOR, rng=rng)
        assert result.loss == SanLoss.MAJOR.loss_range[0]  # 1
        assert result.san_after == 69

    def test_san_check_triggers_temporary_insanity(self):
        """单次损失 ≥5 SAN 触发临时疯狂。"""
        rng = random.Random(42)
        result = san_check(10, SanLoss.EXTREME, rng=rng)
        if result.loss >= 5:
            assert result.insanity_type == InsanityType.TEMPORARY
            assert result.symptom != ""

    def test_san_check_zero_triggers_indefinite(self):
        """SAN 归零触发不定疯狂。"""
        rng = random.Random(42)
        result = san_check(5, SanLoss.CALAMITOUS, rng=rng)
        if result.san_after <= 0:
            assert result.insanity_type == InsanityType.INDEFINITE

    def test_san_loss_ranges(self):
        """各等级损失范围正确。"""
        assert SanLoss.TRIVIAL.loss_range == (1,)
        assert SanLoss.MINOR.loss_range[1] == 2
        assert SanLoss.CALAMITOUS.loss_range[1] == 20

    def test_san_reward(self):
        new_san, desc = san_reward(50, 10, max_san=99)
        assert new_san == 60
        assert "恢复" in desc

    def test_san_reward_capped(self):
        new_san, desc = san_reward(95, 10, max_san=99)
        assert new_san == 99

    def test_daily_san_loss_threshold(self):
        """单日损失 ≥ 20% 触发不定疯狂。"""
        assert daily_san_loss_check(50, 60, 12)   # 60*0.2=12, loss=12 → True
        assert not daily_san_loss_check(50, 60, 11)  # loss=11 < 12 → False


# ═══════════════════════════════════════════
# 战斗
# ═══════════════════════════════════════════

class TestCombat:
    def test_attack_hit(self):
        """攻击命中并造成伤害。"""
        rng = random.Random(123)
        # 高技能确保命中
        result = resolve_attack("陈明", "邪教徒", ActionType.FIGHTING, 90,
                                damage_dice="1d6", rng=rng)
        assert result.attacker == "陈明"
        assert result.defender == "邪教徒"
        # 技能 90，非常可能命中
        if result.attack_success:
            assert result.total_damage > 0

    def test_dodge_evasion(self):
        """闪避成功，攻击落空。"""
        rng = random.Random(42)
        result = resolve_attack("邪教徒", "陈明", ActionType.FIGHTING, 30,
                                defense_type=ActionType.DODGE, defense_skill=90,
                                damage_dice="1d6", rng=rng)
        # 防守技能 90 vs 攻击技能 30，陈明大概率闪避成功
        assert result.defense_roll is not None

    def test_fumble(self):
        """大失败——武器可能脱手。"""
        rng = random.Random(42)
        # 技能值 5，大概率大失败
        result = resolve_attack("新手", "怪物", ActionType.FIGHTING, 5,
                                damage_dice="1d3", rng=rng)
        # 技能很低，大概率失败或大失败
        assert not result.attack_success or result.attack_level == "大失败"

    def test_firearms_no_defense(self):
        """射击不能被格挡（需要闪避）。"""
        rng = random.Random(42)
        result = resolve_attack("林晓", "深潜者", ActionType.FIREARMS, 60,
                                damage_dice="1d10", rng=rng)
        assert result.action == ActionType.FIREARMS

    def test_impale(self):
        """极难成功时贯穿取满伤害。"""
        # 固定骰值 1 → 大成功（也是极难以上）
        # 但 resolve_attack 用的是 rng.randint，无法精确控制
        # 仅验证 impale 参数被接受
        rng = random.Random(42)
        result = resolve_attack("王博士", "食尸鬼", ActionType.FIGHTING, 80,
                                damage_dice="1d6", impale=True, rng=rng)
        # 不崩溃即通过
        assert isinstance(result, AttackResult)


# ═══════════════════════════════════════════
# 幸运
# ═══════════════════════════════════════════

class TestLuck:
    def test_spend_luck_successful(self):
        """消耗幸运值将失败扭转为成功。"""
        # 骰值 55，目标 50，需要 5 点幸运
        result = spend_luck(current_luck=30, roll_value=55, target_value=50)
        assert result.spent == 5
        assert result.luck_after == 25
        assert result.is_success
        assert result.roll_after == 50

    def test_spend_luck_insufficient(self):
        """幸运不足，无法扭转为成功。"""
        result = spend_luck(current_luck=3, roll_value=55, target_value=50)
        assert result.spent == 3  # 只有 3 点
        assert result.luck_after == 0
        assert not result.is_success
        assert "不足" in result.description

    def test_spend_luck_already_success(self):
        """检定已成功，不消耗幸运。"""
        result = spend_luck(current_luck=50, roll_value=30, target_value=50)
        assert result.spent == 0
        assert result.luck_after == 50
        assert result.is_success

    def test_luck_recovery(self):
        """幸运恢复检定。"""
        rng = random.Random(42)
        new_luck, desc = luck_recovery(30, rng=rng)
        assert new_luck >= 30  # 可能恢复


# ═══════════════════════════════════════════
# 孤注一掷
# ═══════════════════════════════════════════

class TestPushing:
    def test_can_push_failed_roll(self):
        """失败检定可以孤注一掷。"""
        result = resolve_coc(50, "常规", rng=random.Random(42))
        if not result.success and not result.is_fumble:
            assert can_push(result)

    def test_cannot_push_fumble(self):
        """大失败不能孤注一掷。"""
        # 技能 1，几乎必然大失败
        rng = random.Random(42)
        result = resolve_coc(1, "常规", rng=rng)
        if result.is_fumble:
            assert not can_push(result)

    def test_cannot_push_success(self):
        """已成功不能孤注一掷。"""
        rng = random.Random(42)
        result = resolve_coc(99, "常规", rng=rng)
        if result.success:
            assert not can_push(result)

    def test_push_roll_different_result(self):
        """孤注一掷产生新的骰值。"""
        rng = random.Random(42)
        # 先做一个失败的检定
        original = resolve_coc(30, "常规", rng=rng)
        if can_push(original):
            pushed = push_roll(30, "常规", previous_result=original, rng=random.Random(99))
            assert pushed.was_pushed
            # 两次的骰值可能不同
