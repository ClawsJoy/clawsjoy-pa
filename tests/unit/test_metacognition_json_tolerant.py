# -*- coding: utf-8 -*-
"""2026-09-07: Metacognition JSON 损坏容错 — reflections.json 损坏不再抛异常,
坏文件备份为 .bak-<ts>, 重建空列表, 调用线程(os_monitor)正常继续。"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
import pytest


@pytest.fixture(autouse=True)
def _meta_root(tmp_path, monkeypatch):
    """数据根重定向到 tmp_path(不污染真实 data/agents)。"""
    import core.lib.metacognition as mc

    monkeypatch.setattr(mc, "get_data_root", lambda: str(tmp_path))
    yield mc, tmp_path


def _corrupt(tmp_path):
    d = tmp_path / "agents" / "os_monitor" / "metacognition"
    d.mkdir(parents=True, exist_ok=True)
    (d / "reflections.json").write_text('[{"a": 1}, {"b": 2}, {"broken": tru', encoding="utf-8")
    (d / "evolutions.json").write_text("[]", encoding="utf-8")
    return d


def test_corrupt_reflections_backup_and_rebuild(_meta_root):
    """损坏 reflections.json → 不抛异常, 备份 .bak-<ts>, 重建空列表"""
    mc, tmp_path = _meta_root
    d = _corrupt(tmp_path)
    meta = mc.Metacognition("os_monitor")  # 不应抛异常
    assert meta.reflections == []
    # 时间戳备份存在且内容为损坏原文
    baks = sorted(d.glob("reflections.json.bak-*"))
    assert baks, "应生成 .bak-<ts> 备份"
    assert '{"broken": tru' in baks[-1].read_text(encoding="utf-8")
    assert meta.evolutions == []


def test_valid_json_loads_normally(_meta_root):
    """正常文件照常加载(回归)"""
    mc, tmp_path = _meta_root
    d = _corrupt(tmp_path)
    (d / "reflections.json").write_text(json.dumps([{"a": 1}, {"b": 2}]), encoding="utf-8")
    meta = mc.Metacognition("os_monitor")
    assert len(meta.reflections) == 2
    assert not list(d.glob("reflections.json.bak-*"))


def test_missing_files_empty(_meta_root):
    """文件不存在 → 空列表, 不创建备份"""
    mc, tmp_path = _meta_root
    meta = mc.Metacognition("nobody")
    assert meta.reflections == []
    assert meta.evolutions == []


def test_non_list_tolerated(_meta_root):
    """顶层非 list(如 {} 或字符串)同样容错: 备份 + 空列表"""
    mc, tmp_path = _meta_root
    d = tmp_path / "agents" / "os_monitor" / "metacognition"
    d.mkdir(parents=True, exist_ok=True)
    (d / "reflections.json").write_text('{"unexpected": true}', encoding="utf-8")
    (d / "evolutions.json").write_text("[]", encoding="utf-8")
    meta = mc.Metacognition("os_monitor")
    assert meta.reflections == []
    assert list(d.glob("reflections.json.bak-*")), "非 list 也应备份"
