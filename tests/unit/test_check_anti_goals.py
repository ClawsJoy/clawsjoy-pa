# -*- coding: utf-8 -*-
"""T75 · R8 反目标 10 条机检器单测（含反例必红）

只测 tests 构造之临时根；不写产品码、不联网。
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("check_anti_goals_t75", ROOT / "tools" / "check_anti_goals.py")
C = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(C)


def base_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "config" / "llm").mkdir(parents=True)
    (root / "dist" / "pa_shell" / "payload").mkdir(parents=True)
    (root / "docs" / "reports" / "pa_iter40").mkdir(parents=True)
    (root / "config" / "llm" / "llm_config.yaml").write_text(
        "default_provider: ollama\n"
        "providers:\n"
        "  ollama:\n"
        "    endpoint: http://127.0.0.1:11434\n"
        "  deepseek:\n"
        "    api_key: your-api-key\n",
        encoding="utf-8",
    )
    (root / "docs" / "reports" / "pa_iter40" / "06_pm.md").write_text(
        "> 代发: DSH（PA）\n\n正文\n", encoding="utf-8"
    )
    return root


def statuses(root: Path) -> dict:
    return {x["id"]: x["status"] for x in C.run(root)["items"]}


def test_baseline_nine_pass_one_manual(tmp_path):
    st = statuses(base_root(tmp_path))
    for i in range(1, 10):
        assert st["AG-0%d" % i] == "PASS", (i, st)
    assert st["AG-10"] == "MANUAL"
    assert st.get("AG-00") is None


def test_baseline_exit_codes(tmp_path):
    root = base_root(tmp_path)
    assert C.main(["--root", str(root)]) == 0
    assert C.main(["--root", str(root), "--strict"]) == 2


def test_json_output_schema(tmp_path):
    root = base_root(tmp_path)
    out = tmp_path / "out.json"
    assert C.main(["--root", str(root), "--json", str(out)]) == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["summary"] == {"pass": 9, "fail": 0, "manual": 1, "total": 10}
    assert d["verdict"] == "NO_FAIL_WITH_MANUAL"
    assert len(d["items"]) == 10


def test_cloud_default_fails(tmp_path):
    root = base_root(tmp_path)
    (root / "config" / "llm" / "llm_config.yaml").write_text(
        "default_provider: deepseek\n", encoding="utf-8")
    assert statuses(root)["AG-01"] == "FAIL"
    assert C.main(["--root", str(root)]) == 2


def test_payload_data_fails(tmp_path):
    root = base_root(tmp_path)
    (root / "dist" / "pa_shell" / "payload" / "data").mkdir()
    assert statuses(root)["AG-02"] == "FAIL"


def test_payload_clean_passes(tmp_path):
    root = base_root(tmp_path)
    (root / "dist" / "pa_shell" / "payload" / "core").mkdir()
    assert statuses(root)["AG-02"] == "PASS"


def test_pfx_fails(tmp_path):
    root = base_root(tmp_path)
    (root / "secret.pfx").write_bytes(b"x")
    assert statuses(root)["AG-03"] == "FAIL"


def test_hardcoded_key_fails(tmp_path):
    root = base_root(tmp_path)
    (root / "config" / "llm" / "llm_config.yaml").write_text(
        "default_provider: ollama\nproviders:\n  openai:\n    api_key: sk-abcdefghijklmnopqrstuvwxyz012345\n",
        encoding="utf-8")
    assert statuses(root)["AG-04"] == "FAIL"


def test_placeholder_key_passes(tmp_path):
    assert statuses(base_root(tmp_path))["AG-04"] == "PASS"


def test_missing_delivery_mark_fails(tmp_path):
    root = base_root(tmp_path)
    (root / "docs" / "reports" / "pa_iter40" / "bad.md").write_text("无标头\n", encoding="utf-8")
    assert statuses(root)["AG-05"] == "FAIL"


def test_red_lines_must_be_10(tmp_path, monkeypatch):
    root = base_root(tmp_path)
    monkeypatch.setattr(C, "ITEMS", C.ITEMS[:9])
    assert statuses(root)["AG-06"] == "FAIL"


def test_ad_monetization_fails(tmp_path):
    root = base_root(tmp_path)
    (root / "docs" / "design").mkdir(parents=True)
    (root / "docs" / "design" / "x.md").write_text("我们主推广告变现路径\n", encoding="utf-8")
    assert statuses(root)["AG-07"] == "FAIL"


def test_ad_feature_allowed(tmp_path):
    root = base_root(tmp_path)
    (root / "docs" / "design").mkdir(parents=True)
    (root / "docs" / "design" / "x.md").write_text("阅读器支持去广告\n", encoding="utf-8")
    assert statuses(root)["AG-07"] == "PASS"


def test_scale_selling_fails(tmp_path):
    root = base_root(tmp_path)
    (root / "docs" / "design").mkdir(parents=True)
    (root / "docs" / "design" / "x.md").write_text("以接入数量当卖点\n", encoding="utf-8")
    assert statuses(root)["AG-08"] == "FAIL"


def test_scale_selling_negated_passes(tmp_path):
    root = base_root(tmp_path)
    (root / "docs" / "design").mkdir(parents=True)
    (root / "docs" / "design" / "x.md").write_text("⛔ 不以接入数量当卖点\n", encoding="utf-8")
    assert statuses(root)["AG-08"] == "PASS"


def test_toks_selling_fails(tmp_path):
    root = base_root(tmp_path)
    (root / "docs" / "design").mkdir(parents=True)
    (root / "docs" / "design" / "x.md").write_text("推理 tok/s 遥遥领先\n", encoding="utf-8")
    assert statuses(root)["AG-09"] == "FAIL"


def test_toks_measurement_allowed(tmp_path):
    root = base_root(tmp_path)
    (root / "docs" / "design").mkdir(parents=True)
    (root / "docs" / "design" / "x.md").write_text("实测 3.41 tok/s（RTX 2060）\n", encoding="utf-8")
    assert statuses(root)["AG-09"] == "PASS"


def test_no_fake_green_defense(tmp_path, monkeypatch):
    root = base_root(tmp_path)
    items = [dict(x) for x in C.ITEMS]
    items[9]["fn"] = lambda _root: ("PASS", [], "假绿")
    monkeypatch.setattr(C, "ITEMS", items)
    res = C.run(root)
    st = {x["id"]: x["status"] for x in res["items"]}
    assert st.get("AG-00") == "FAIL", res
    assert res["verdict"] == "FAIL"
    assert C.main(["--root", str(root)]) == 2


def test_manual_item_always_manual(tmp_path):
    assert statuses(base_root(tmp_path))["AG-10"] == "MANUAL"
