# -*- coding: utf-8 -*-
u"""客户端**离线包**（`scripts/win_pa/make_client_bundle.py` ＋ 安装器之 `--offline`）之测（承 pm_1386 §二.2）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_win_pa_bundle.py -q

判据（⛔ 无齿之闸 ＝ 假绿）：
  ⒈ **缺轮必逮**：`missing_wheels` ⇒ 空 ⇒ 皆缺 ／ 全 ⇒ ⛔ 假红 ／ `flask` ⟷ `flask-cors` ⛔ 混。
  ⒉ **册之核**：`check_bundle` ⇒ 印不合判「印异」／件亡判「印缺」／册外之件判「印多」。
  ⒊ **三源同轴**（二源必漂 ⇒ 钉之）：`requirements.txt` 之必需节 ≡ `requirements-runtime.txt` ≡
     `make_client_bundle.required_dists()` ≡ `preflight_start.REQUIRED_DEPS`。
  ⒋ **安装器之 `--offline` 闸有齿**：空 wheel ⇒ 判红 ＋ 点名 ＋ **修之门**（⛔ 静默）／全轮 ⇒ 过。
  ⒌ **下载之 argv 须含构建依**（`setuptools` ／ `wheel`）：⛔ 在 ⇒ sdist 之离线装必败。
  ⒍ **册之「源」键**（pm_1573 §二）：`commit` ／ `tree` ／ `刻` 须得（包须自证其出处）；
     ⛔ 非仓 ⇒ `commit` `None`（fail-loud 之据 · ⛔ 假印）。
"""
import ast
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "win_pa"))
sys.path.insert(0, str(ROOT / "scripts" / "dev"))
sys.path.insert(0, str(ROOT))

import make_client_bundle as MB  # noqa: E402
from scan_client_deps import _norm  # noqa: E402


def _req_names(path, only_required=False):
    sec, out = "", set()
    for ln in io.open(str(path), encoding="utf-8").read().splitlines():
        s = ln.strip()
        if s.startswith("#"):
            m = re.search(r"=\s*([^=]+?)\s*=", s)
            if m:
                sec = m.group(1).strip()
            continue
        s = s.split("#")[0].strip()
        if not s:
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)", s)
        if not m:
            continue
        if only_required and not sec.startswith(u"运行依赖"):
            continue
        out.add(_norm(m.group(1)))
    return out


def test_缺轮必逮(tmp_path):
    u"""承 ⒈：空 ⇒ 皆缺 ／ 全 ⇒ ⛔ 假红 ／ 名之归一（flask ⟷ flask-cors ⛔ 混）。"""
    w = tmp_path / "wheel"
    w.mkdir()
    assert MB.missing_wheels(str(w), ["flask", "PyYAML"]) == ["flask", "PyYAML"]
    (w / "Flask-3.1.3-py3-none-any.whl").write_text("", encoding="utf-8")
    (w / "PyYAML-6.0.3-cp312-cp312-win_amd64.whl").write_text("", encoding="utf-8")
    assert MB.missing_wheels(str(w), ["flask", "PyYAML"]) == [], u"全轮 ⇒ 缺空（⛔ 假红）"
    assert MB.missing_wheels(str(w), ["flask-cors"]) == ["flask-cors"], u"flask ⟷ flask-cors ⛔ 混"
    assert MB.missing_wheels(str(w), ["python-dotenv"]) == ["python-dotenv"]
    (w / "python_dotenv-1.2.2-py3-none-any.whl").write_text("", encoding="utf-8")
    assert MB.missing_wheels(str(w), ["python-dotenv"]) == [], u"下划线 ⟷ 连字符须归一"


def test_册之核(tmp_path):
    u"""承 ⒉：`check_bundle` 三判（印异 ／ 印缺 ／ 印多）。"""
    import json
    (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "bundle_manifest.json").write_text(
        json.dumps({"依之表": ["flask"], "件之表": [{"rel": "a.py", "sha256": "0" * 64}]}),
        encoding="utf-8")
    r = MB.check_bundle(str(tmp_path))
    assert r["印异"] == ["a.py"], r
    assert r["依缺"] == ["flask"], r
    (tmp_path / "c.py").write_text("y=1\n", encoding="utf-8")
    r2 = MB.check_bundle(str(tmp_path))
    assert "c.py" in r2["印多"], r2
    (tmp_path / "a.py").unlink()
    r3 = MB.check_bundle(str(tmp_path))
    assert "a.py" in r3["印缺"], r3


def test_三源同轴():
    u"""承 ⒊：四源之依表**同一**（二源必漂 ⇒ 钉之）。⚠ 以 `ast` 取 preflight 之表（⛔ exec_module）。"""
    want = _req_names(ROOT / "requirements.txt", only_required=True)
    assert want, u"真源之必需节空 ＝ 判据无齿"
    assert _req_names(ROOT / "requirements-runtime.txt") == want, u"镜像 ⛔ 同轴"
    assert {_norm(d) for d in MB.required_dists(str(ROOT))} == want, u"离线包器之表 ⛔ 同轴"
    src = (ROOT / "scripts" / "win_pa" / "preflight_start.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    node = next(n for n in tree.body
                if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "REQUIRED_DEPS")
    assert {_norm(d) for _m, d in ast.literal_eval(node.value)} == want, u"前置器之表 ⛔ 同轴"


def _load_installer():
    import importlib.util as _ilu
    p = ROOT / "scripts" / "win_pa" / "install_win_pa.py"
    spec = _ilu.spec_from_file_location("_inst_probe", str(p))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_安装器离线闸有齿(tmp_path):
    u"""承 ⒋：空 wheel ⇒ 判红 ＋ 点名 ＋ 修之门；全轮 ⇒ 过（⛔ 静默 ／ ⛔ 假红）。"""
    mod = _load_installer()
    g = {x["name"]: x for x in mod.preflight_gates(offline=True, wheel_dir=str(tmp_path / "none"))}
    assert u"离线包 wheel" in g, list(g)
    assert g[u"离线包 wheel"]["ok"] is False
    assert u"缺" in g[u"离线包 wheel"]["reason"]
    assert "make_client_bundle" in g[u"离线包 wheel"]["note"], u"须附**修之门**（⛔ 静默）"
    w = tmp_path / "w"
    w.mkdir()
    for d in MB.required_dists(str(ROOT)):
        (w / (d.replace("-", "_") + "-1.0-py3-none-any.whl")).write_text("", encoding="utf-8")
    g2 = {x["name"]: x for x in mod.preflight_gates(offline=True, wheel_dir=str(w))}
    assert g2[u"离线包 wheel"]["ok"] is True, g2[u"离线包 wheel"]
    g3 = {x["name"]: x for x in mod.preflight_gates(offline=False, wheel_dir=str(w))}
    assert u"离线包 wheel" not in g3, u"⛔ --offline ⇒ 其闸 ⛔ 在（⛔ 白判红）"

def test_离线包之下载须含构建依():
    u"""承 ⒌（**我一手逮得** · 2026-10-06 · M2 预演）：`wheel\\` 须含**构建依**（setuptools ／ wheel）。

    由：运行依含 **sdist**（`flasgger` —— PyPI 上唯 `.tar.gz` ／ ⛔ wheel）⇒ 装时须**构建**
      ⇒ pip 于 `--no-index` 之下唯以 `find-links` 取构建依 ⇒ ⛔ 在 ⇒ **离线装必败**
      （实证：M2 预演之 venv 装 rc=1 ／ `No matching distribution found for setuptools>=40.8.0`）。
    反控：**旧式 argv**（唯 `-r` · ⛔ 构建依）⇒ 本判必红（有齿 · ⛔ 空判）。
    """
    cmd = MB.download_cmd("W", "R")
    assert "setuptools" in cmd, u"构建依 setuptools ⛔ 在 ⇒ sdist 之装必败"
    assert "wheel" in cmd, u"构建依 wheel ⛔ 在"
    old = [sys.executable, "-m", "pip", "download", "-d", "W", "-r", "R"]
    assert not ("setuptools" in old and "wheel" in old), u"反控：旧式 argv ⇒ 本判必红（有齿）"


def test_洁闸零红_本仓之运行子集():
    u"""pm_1478 §一 之齿：本仓之**运行子集** ⇒ 无 gitignored 之件（本机之产物 ⛔ 入包）。

    由：`apply_bundle()` 见 `ig_payload` 非空 ⇒ 「⇒ 止」（rc 2）⇒ **真出包之路断**
      （pm_1478 §一 一手：`core/lib/dependency_graph.json` 机器生成 ⇒ 未剔 ⇒ 闸红）。
    ⚠ 唯走 `_payload_files`（⛔ `scan_live_paths` —— 那是秒级之扫）；本判唯核剔表 ＋ 一齿。
    """
    files = MB._payload_files(str(ROOT))
    assert files, u"运行子集空 ⇒ 判据无齿"
    assert MB.ignored_payload(str(ROOT), files) == [], u"运行子集含 gitignored 之件"
    assert "core/lib/dependency_graph.json" in MB.EXCLUDE, u"机器生成物须入剔表（pm_1478 §一）"
    if (ROOT / "core" / "lib" / "dependency_graph.json").is_file():
        assert "core/lib/dependency_graph.json" in MB._payload_walk(str(ROOT)), \
            u"反控（有齿）：该件确在走查之内 ⇒ 剔表正生效力（⛔ 空判）"



def test_册之源键(tmp_path):
    u"""承 ⒍（pm_1573 §二）：册须载「源」（`commit` ／ `tree` ／ `刻`）⇒ 包自证其出处 · ⛔ 唯靠回件。"""
    src = MB.source_stamp(str(ROOT))
    assert re.match(r"^[0-9a-f]{40}$", src["commit"] or ""), src
    assert re.match(r"^[0-9a-f]{40}$", src["tree"] or ""), src
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}$", src["刻"] or ""), src
    assert u"唯副本之源" in src["明书"], src
    man = MB.manifest_for([{"rel": "a.py", "sha256": "0" * 64, "bytes": 1}], ["flask"], src)
    assert man["源"]["commit"] == src["commit"] and man["源"]["tree"] == src["tree"]
    assert man["version"] == MB.VERSION and man["件之表"] and man["依之表"] == ["flask"], man
    # 反控：⛔ 非仓 ⇒ 源之印 ⛔ 得判（⛔ 假印 —— apply 遇之则止）
    assert MB.source_stamp(str(tmp_path / "norepo"))["commit"] is None

