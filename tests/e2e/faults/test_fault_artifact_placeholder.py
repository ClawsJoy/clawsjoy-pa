# -*- coding: utf-8 -*-
"""故障注入 · 占位产物（R6）。纪律：**先能失败，再能通过**。

背景：data/v9/pa/artifacts/artifact_pa_task.txt 是 68 字节的 StubExecutor 假产物，
而审核只判「非空」→ 判 pass。R6 要求「产物存在」必须包含「不是占位物」。

注意：本例一律用**沙箱相对路径 + base_dir**（即 R1 的形态）。
绝对系统路径（/tmp /etc /home /root）按「沙箱边界」既有规定直接判越界 —— 这与 R1 同源，
不是测试的权宜之计。
"""
import sys

sys.path.insert(0, ".")
from core.pa.artifact import verify_artifact, verify_artifacts


def test_FAULT_placeholder_artifact_is_rejected(tmp_path):
    """① 先能失败：68 字节占位产物必须被拦。"""
    (tmp_path / "artifact_pa_task.txt").write_text("x" * 68, encoding="utf-8")
    r = verify_artifact("artifact_pa_task.txt", base_dir=tmp_path)
    assert r["ok"] is False
    assert "占位" in r["reason"], r
    assert r["size"] == 68


def test_FAULT_too_small_is_rejected(tmp_path):
    """过小文件（一行「已完成」）也算占位。"""
    (tmp_path / "done.md").write_text("已完成", encoding="utf-8")
    assert verify_artifact("done.md", base_dir=tmp_path)["ok"] is False


def test_PASS_real_artifact_is_accepted(tmp_path):
    """② 再能通过：真产物必须放行。"""
    (tmp_path / "deck.md").write_text("正文" * 2000, encoding="utf-8")
    r = verify_artifact("deck.md", base_dir=tmp_path)
    assert r["ok"] is True and r["reason"] is None, r


def test_FAULT_missing_and_out_of_bounds_rejected(tmp_path):
    assert verify_artifact("nope.md", base_dir=tmp_path)["ok"] is False
    assert verify_artifact("/tmp/evil.md")["ok"] is False
    assert verify_artifact("")["ok"] is False
    (tmp_path / "adir").mkdir()
    assert verify_artifact("adir", base_dir=tmp_path)["ok"] is False


def test_batch_verify_reports_all_failures(tmp_path):
    (tmp_path / "good.md").write_text("正文" * 2000, encoding="utf-8")
    (tmp_path / "bad.txt").write_text("x" * 68, encoding="utf-8")
    r = verify_artifacts(["good.md", "bad.txt"], base_dir=tmp_path)
    assert r["ok"] is False and r["checked"] == 2 and len(r["failures"]) == 1
    assert verify_artifacts(["good.md"], base_dir=tmp_path)["ok"] is True


def test_allow_stub_escape_hatch(tmp_path):
    """过渡/测试用豁免口子存在，但必须显式开。"""
    (tmp_path / "s.txt").write_text("x" * 68, encoding="utf-8")
    assert verify_artifact("s.txt", base_dir=tmp_path, allow_stub=True)["ok"] is True
