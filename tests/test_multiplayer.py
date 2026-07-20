"""多人联机 + 存档系统测试。"""

from __future__ import annotations

import tempfile
import shutil
from pathlib import Path

from trpg_agent.session import Session
from trpg_agent.memory.game_state import Investigator, Npc, Quest


def test_speaker_in_record_turn():
    """speaker 参数传递到 history 条目。"""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        session = Session("multi_test", data_dir=tmpdir)
        session.state.investigators.append(
            Investigator(name="陈明", hp=12, max_hp=12, san=60, max_san=60, luck=50)
        )
        session.state.investigators.append(
            Investigator(name="林晓", hp=10, max_hp=10, san=70, max_san=70, luck=45)
        )

        # 陈明行动
        session.record_turn("我检查门后的暗格", "门后有一个上锁的铁盒。", speaker="陈明")
        # 林晓行动
        session.record_turn("我用发卡试着撬锁", "咔嗒一声，锁开了。", speaker="林晓")

        entries = session.history.entries()
        # 第1条 user 消息应该有 speaker
        assert entries[0]["speaker"] == "陈明"
        assert entries[0]["content"] == "我检查门后的暗格"
        # 第2条 assistant 消息应该没有 speaker
        assert "speaker" not in entries[1]
        # 第3条 user
        assert entries[2]["speaker"] == "林晓"

        print("✓ speaker 字段正确写入 history")
    finally:
        shutil.rmtree(tmpdir)


def test_build_messages_with_speaker():
    """speaker 前缀注入 Ollama 消息。"""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        session = Session("msg_test", data_dir=tmpdir)
        msgs = session.build_messages("我推开大门", speaker="陈明")
        assert msgs[-1]["content"] == "[陈明] 我推开大门"

        # 带检定上下文
        msgs2 = session.build_messages(
            "我检查血迹", speaker="林晓", dice_context="侦查 成功 (42 ≤ 60)"
        )
        assert "[林晓]" in msgs2[-1]["content"]
        assert "侦查 成功" in msgs2[-1]["content"]

        print("✓ build_messages speaker 前缀正确")
    finally:
        shutil.rmtree(tmpdir)


def test_save_and_load():
    """命名存档 + 读档往返。"""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        session = Session("save_test", data_dir=tmpdir)
        session.state.investigators.append(
            Investigator(name="陈明", hp=8, max_hp=12, san=50, max_san=60, luck=30)
        )
        session.state.location = "废弃医院大厅"
        session.state.quests.append(Quest(title="寻找失踪的病人", status="open"))
        session.state.npcs.append(
            Npc(name="值班护士", attitude="wary", location="废弃医院大厅")
        )

        session.record_turn("我环顾四周", "大厅空无一人，但你能听到远处有滴水声。", speaker="陈明")
        session.record_turn("我朝滴水声的方向走去", "走廊尽头是一扇半开的铁门。", speaker="陈明")

        # 存档
        save_path = session.save_game("医院探险_第2轮")
        assert save_path.is_dir()
        assert (save_path / "state.json").is_file()
        assert (save_path / "history.jsonl").is_file()

        # 列出存档
        saves = Session.list_saves("save_test")
        assert "医院探险_第2轮" in saves

        # 读档
        loaded = Session.load_game("save_test", "医院探险_第2轮", data_dir=tmpdir)
        assert loaded is not None
        assert loaded.state.turn_count == 2
        assert loaded.state.location == "废弃医院大厅"
        assert loaded.state.investigators[0].hp == 8
        assert loaded.state.investigators[0].name == "陈明"
        assert loaded.history.count() == 4  # 2 user + 2 assistant
        assert loaded.state.quests[0].title == "寻找失踪的病人"

        # 验证 speaker 在读档后保留
        entries = loaded.history.entries()
        assert entries[0]["speaker"] == "陈明"

        print("✓ 存档/读档往返正确")
    finally:
        shutil.rmtree(tmpdir)


def test_delete_save():
    """删除存档。"""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        session = Session("del_test", data_dir=tmpdir)
        session.save_game("临时存档")
        assert "临时存档" in Session.list_saves("del_test")

        Session.delete_save("del_test", "临时存档")
        assert "临时存档" not in Session.list_saves("del_test")

        print("✓ 删除存档正确")
    finally:
        shutil.rmtree(tmpdir)


def test_load_nonexistent():
    """读不存在的存档返回 None。"""
    result = Session.load_game("no_such", "no_such_save")
    assert result is None
    print("✓ 不存在存档返回 None")


def test_backward_compat():
    """无 speaker 时完全向后兼容。"""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        session = Session("compat_test", data_dir=tmpdir)
        # 不带 speaker 的调用（旧式）
        session.record_turn("我检查房间", "房间很暗，什么也看不清。")
        entries = session.history.entries()
        assert "speaker" not in entries[0]
        assert entries[0]["content"] == "我检查房间"

        # build_messages 不带 speaker
        msgs = session.build_messages("继续前进")
        assert "[陈明]" not in msgs[-1]["content"]
        assert msgs[-1]["content"] == "继续前进"

        print("✓ 向后兼容（无 speaker）")
    finally:
        shutil.rmtree(tmpdir)


def test_multiplayer_full_flow():
    """完整多人游戏流程测试。"""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        session = Session("full_test", data_dir=tmpdir)
        session.state.investigators = [
            Investigator(name="陈明", hp=12, max_hp=12, san=60, max_san=60, luck=50),
            Investigator(name="林晓", hp=10, max_hp=10, san=70, max_san=70, luck=45),
        ]
        session.state.location = "古屋门厅"

        # 陈明探查
        session.record_turn(
            "我用手电筒扫过墙壁，寻找暗门。",
            "光束照到一幅歪斜的家族肖像。在画框的角落，你注意到一个几乎看不见的凹槽。",
            speaker="陈明"
        )
        # 林晓跟进
        session.record_turn(
            "我走近那幅画，用手指摸索凹槽。",
            "凹槽里藏着一枚生锈的铜钥匙。",
            speaker="林晓"
        )

        assert session.state.turn_count == 2
        assert session.history.count() == 4

        # 存档
        session.save_game("古屋_门前")
        # 删除当前 session，模拟重新登录
        session2 = Session.load_game("full_test", "古屋_门前", data_dir=tmpdir)
        assert session2 is not None

        # 一个人续局
        session2.record_turn(
            "我决定独自进入地下室。",
            "楼梯吱嘎作响，每走一步都像在惊动什么沉睡的东西。",
            speaker="陈明"
        )
        assert session2.state.turn_count == 3

        print("✓ 多人→存档→单人续局 完整流程")
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    test_speaker_in_record_turn()
    test_build_messages_with_speaker()
    test_save_and_load()
    test_delete_save()
    test_load_nonexistent()
    test_backward_compat()
    test_multiplayer_full_flow()
    print()
    print("全部多人联机+存档测试通过 ✓")
