# -*- coding: utf-8 -*-
"""按段落重要性裁剪验收（2026-09-13 批88）。用被改对象本身（体检项 45）。"""
import sys

sys.path.insert(0, ".")

from core.gateway.message_assembler import _hard_truncate_messages, _inject_sys_content, _split_uncuttable

SYS = open("config/prompts/agent_system.md", encoding="utf-8").read()


def test_uncuttable_sections_survive():
    """用例1：不可裁段落超长时仍完整保留（执行纪律 G1-G3 必须在）"""
    msgs = [{"role": "system", "content": SYS}]
    _hard_truncate_messages(msgs)
    out = msgs[0]["content"]
    assert len(SYS) > 8000, "前置：原文确实超限"
    assert "## 执行纪律" in out, "执行纪律段被截掉了（本条即为原缺陷）"
    assert "Harness G1-G3" in out, "执行纪律段正文不完整"
    print("用例1 OK 输出长度 =", len(out), "（原文", len(SYS), "）")


def test_no_uncuttable_still_head_tail():
    """用例2：无不可裁段落时仍按头70/尾30（不破原行为）"""
    # 每段 2000 字符 × 12 = 24000，确保中间段落明确落在丢弃带内
    body = "".join("## 信息段%d\n%s\n" % (i, "甲" * 2000) for i in range(12))
    msgs = [{"role": "system", "content": body}]
    _hard_truncate_messages(msgs)
    out = msgs[0]["content"]
    assert "--- 开头 ---" in out and "--- 结尾 ---" in out, "仍应保留头尾结构"
    assert "信息段0" in out, "头部应保留"
    assert "信息段11" in out, "尾部应保留"
    assert "信息段5" not in out, "中间段（信息段5）应被裁掉"
    print("用例2 OK 长度 =", len(out))


def test_both_paths_consistent():
    """用例3：两处截断策略一致 —— B（注入上限）也必须保住不可裁段落"""
    msgs = [{"role": "system", "content": SYS}]
    _inject_sys_content(msgs, "\n## 补充注入\n" + "乙" * 2000, max_sys_chars=8000)
    out = msgs[0]["content"]
    assert "## 执行纪律" in out, "B 路径把执行纪律段丢了（两处不一致）"
    print("用例3 OK 长度 =", len(out), "含执行纪律 =", "## 执行纪律" in out)


def test_split_has_teeth():
    """防失效自检：不可裁清单确实能挑出来"""
    keep, rest = _split_uncuttable(SYS)
    assert keep, "未挑出任何不可裁段落（清单失效）"
    joined = "\n".join(keep)
    assert "## 执行纪律" in joined
    assert "## 花名册身份" not in joined, "信息段不该进不可裁列表"
    print("用例4 OK 不可裁段落数 =", len(keep), "| 其余字符 =", len(rest))
