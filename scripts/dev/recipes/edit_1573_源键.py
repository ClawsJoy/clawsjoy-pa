# -*- coding: utf-8 -*-
r"""recipe —— pm_1573 之裁：册须增「源」键（`commit` ／ `tree` ／ `刻`）（一改一底 · 本件之树 ＝ 本件所在之仓）。

字面之据（器取 · ⛔ 手抄）：
  PM 1573 §二.1（我一手）：`bundle_manifest.json` 之键唯四（`version` ／ `依之表` ／ `件之表` ／ `口径`）
    ⇒ 「此包出于何源」**唯靠回件可回指** ⇒ 包 **⛔ 自证**（承「入库 ＝ 快照 ⛔ 品质之证」）。
  PM 1573 §二.2 之裁：册增 `源` ＝ {`commit`（副本 HEAD）／ `tree`（`HEAD^{tree}`）／ `刻`（含时区）}；
    主库（`master`）之对件 ⇒ 「⛔ 入册 ＋ 明书」∨「入册」⇒ 本器取**明书**：
    由 —— 本器于**副本**跑 ∧ ⛔ 知主库之径 ⇒ 硬编码 `<main-repo>` ＝ 新病（承「⛔ 硬编码本机径」）。
根：本器所改之树 ＝ 本件所在之仓（root=ROOT）⇒ 副树 ／ 主树各改其本（⛔ 互指）。
用法：python -X utf8 -B <本件> all [--apply]（⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

_HERE = os.path.dirname(os.path.abspath(__file__))                    # .../scripts/dev/recipes
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))       # 仓之根（本件之树）

# ---------------------------------------------------------------- 新骨（三件）
_GIT = r'''
def _git_out(args, cwd):
    u"""git 之一行（**只读** · ⛔ 起停 · 失败 ⇒ `None`）—— 一处定形（pm_1573 §二）。"""
    try:
        r = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return (r.stdout or "").strip() or None


def source_stamp(root=None, now=None):
    u"""**源之印**（一处定形 · pm_1573 §二）：册须自证其出处 ⇒ `commit` ／ `tree` ／ `刻`。

    由（PM 1573 §二.1 · 我一手）：旧册唯四键（`version` ／ `依之表` ／ `件之表` ／ `口径`）
      ⇒ 「此包出于何源」**唯靠回件可回指** ⇒ 包 **⛔ 自证**（承「入库 ＝ 快照 ⛔ 品质之证」）。
    ⚠ 主库（`master`）之对件 **⛔ 入册**：本器于**副本**跑 ∧ ⛔ 知主库之径
      （硬编码本机径 ＝ 新病 · 承「⛔ 硬编码本机径」）⇒ **明书**之（回件报其 `sha` · 承 PM 1573 §二.2「∨ 明书」）。
    """
    root = root or ROOT
    commit = _git_out(["rev-parse", "HEAD"], root)
    tree = _git_out(["rev-parse", "HEAD^{tree}"], root)
    branch = _git_out(["rev-parse", "--abbrev-ref", "HEAD"], root)
    stamp = now or datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return {"commit": commit, "tree": tree, "分支": branch, "刻": stamp,
            "明书": u"唯副本之源：主库（master）之对件 sha 由回件明书（器 ⛔ 知主库之径）"}
'''.lstrip("\n")

_MAN = r'''
def manifest_for(entries, dists, src):
    u"""册之形（**一处出** · pm_1573 §二）—— 唯此一处拼册（⛔ 各点各拼 ⇒ 免「二源必漂」）。"""
    return {"version": VERSION, "源": dict(src), "依之表": list(dists),
            "件之表": list(entries),
            "口径": u"离线包：wheel\\ 之依全 ∧ 运行子集之 sha256；⛔ 含模型（须另下）"}
'''.lstrip("\n")

_GATE = r'''
    if not (p["源"].get("commit") and p["源"].get("tree")):
        lines.append(u"[bundle] ⛔ 源之印 ⛔ 得判（git ⛔ 用 ∨ 非仓 ∨ HEAD 无）⇒ 止"
                     u"（包须自证其出处 · 承 pm_1573 §二）")
        return 2, lines
'''

_SELF = r'''
    # ⭐ pm_1573 §二：册须载「源」（`commit` ／ `tree` ／ `刻`）⇒ 齿（正控 ／ 反控）
    _st = source_stamp(ROOT)
    say(len(_st.get("commit") or "") == 40 and len(_st.get("tree") or "") == 40,
        u"正控：源之印须得（`commit` ／ `tree` 各 40 hex —— 册须自证其出处 · pm_1573 §二）")
    say(bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}$", _st.get("刻") or "")),
        u"正控：刻之形（含时区 ⇒ 可回指）")
    _man = manifest_for([{"rel": "a.py", "sha256": "0" * 64, "bytes": 1}], ["flask"], _st)
    say(_man["源"]["commit"] == _st["commit"] and _man["件之表"] and _man["依之表"],
        u"正控：册之形（唯 `manifest_for` 一处出 · 含源）")
    say(source_stamp(os.path.join(t, "norepo"))["commit"] is None,
        u"反控：⛔ 非仓 ⇒ `commit` `None`（fail-loud 之据 · ⛔ 假印）")
'''

bundler = [
    (u'scripts/win_pa/make_client_bundle.py · 源之印 ＋ 册之一处出 ＋ 闸', 'scripts/win_pa/make_client_bundle.py', [
        # ---- A1 import datetime ----
        ("sub", "import ast\nimport hashlib", "import ast\nimport datetime\nimport hashlib"),
        # ---- A2 源之印（test 于 plan_bundle 之前）----
        ("sub", "def plan_bundle(root=None, out=None):", _GIT + "\ndef plan_bundle(root=None, out=None):"),
        # ---- A3 plan 载源（干跑亦可见）----
        ("sub", '    return {"version": VERSION, "root": root, "out": out, "dists": dists,',
                '    return {"version": VERSION, "root": root, "out": out, "dists": dists,\n'
                '            "源": source_stamp(root),'),
        # ---- A4 册之一处出 ----
        ("sub", "def apply_bundle(root=None, out=None, wheel=True, json_out=False):",
                _MAN.lstrip("\n") + "\ndef apply_bundle(root=None, out=None, wheel=True, json_out=False):"),
        # ---- A5 洁闸·二 之后 ⇒ 源之闸（fail-loud）----
        ("sub", '    os.makedirs(p["wheel_dir"], exist_ok=True)', _GATE + '    os.makedirs(p["wheel_dir"], exist_ok=True)'),
        # ---- A6 册用一处出 ----
        ("sub", '    man = {"version": VERSION, "依之表": p["dists"], "件之表": entries,\n'
                '           "口径": u"离线包：wheel\\\\ 之依全 ∧ 运行子集之 sha256；⛔ 含模型（须另下）"}',
                "    man = manifest_for(entries, p[\"dists\"], p[\"源\"])"),
        # ---- A7 干跑印源 ----
        ("sub", '            print(u"  将动：① pip download -d %s -r requirements-runtime.txt ② 复运行子集 ③ 写册" % p["wheel_dir"])',
                '            _s = p["源"]\n'
                '            print(u"  源（pm_1573 §二）：commit %s ／ tree %s ／ 分支 %s ／ 刻 %s"\n'
                '                  % (_s.get("commit"), _s.get("tree"), _s.get("分支"), _s.get("刻")))\n'
                '            print(u"  将动：① pip download -d %s -r requirements-runtime.txt ② 复运行子集 ③ 写册" % p["wheel_dir"])'),
        # ---- A8 册核：报源（⛔ 加行 ⇒ 安装页「应看到两行」之辞 ⛔ 动）----
        ("sub", '    j = json.loads(io.open(man, encoding="utf-8").read())',
                '    j = json.loads(io.open(man, encoding="utf-8").read())\n    r["源"] = j.get("源")'),
        # ---- A9 自测之齿 ----
        ("sub", "    n, tt = sum(1 for c in hits if c), len(hits)", _SELF.lstrip("\n") + "    n, tt = sum(1 for c in hits if c), len(hits)"),
    ]),
]

test = [
    (u'tests/unit/test_win_pa_bundle.py · ⒍册之源键', 'tests/unit/test_win_pa_bundle.py', [
        # ---- B1 判据表之补 ----
        ("sub",
         "  ⒋ **安装器之 `--offline` 闸有齿**：空 wheel ⇒ 判红 ＋ 点名 ＋ **修之门**（⛔ 静默）／全轮 ⇒ 过。\n",
         "  ⒋ **安装器之 `--offline` 闸有齿**：空 wheel ⇒ 判红 ＋ 点名 ＋ **修之门**（⛔ 静默）／全轮 ⇒ 过。\n"
         "  ⒌ **下载之 argv 须含构建依**（`setuptools` ／ `wheel`）：⛔ 在 ⇒ sdist 之离线装必败。\n"
         "  ⒍ **册之「源」键**（pm_1573 §二）：`commit` ／ `tree` ／ `刻` 须得（包须自证其出处）；\n"
         "     ⛔ 非仓 ⇒ `commit` `None`（fail-loud 之据 · ⛔ 假印）。\n"),
        # ---- B2 齿 ----
        ("append",
         "\n\ndef test_册之源键(tmp_path):\n"
         "    u\"\"\"承 ⒍（pm_1573 §二）：册须载「源」（`commit` ／ `tree` ／ `刻`）⇒ 包自证其出处 · ⛔ 唯靠回件。\"\"\"\n"
         "    src = MB.source_stamp(str(ROOT))\n"
         "    assert re.match(r\"^[0-9a-f]{40}$\", src[\"commit\"] or \"\"), src\n"
         "    assert re.match(r\"^[0-9a-f]{40}$\", src[\"tree\"] or \"\"), src\n"
         "    assert re.match(r\"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}[+-]\\d{4}$\", src[\"刻\"] or \"\"), src\n"
         "    assert u\"唯副本之源\" in src[\"明书\"], src\n"
         "    man = MB.manifest_for([{\"rel\": \"a.py\", \"sha256\": \"0\" * 64, \"bytes\": 1}], [\"flask\"], src)\n"
         "    assert man[\"源\"][\"commit\"] == src[\"commit\"] and man[\"源\"][\"tree\"] == src[\"tree\"]\n"
         "    assert man[\"version\"] == MB.VERSION and man[\"件之表\"] and man[\"依之表\"] == [\"flask\"], man\n"
         "    # 反控：⛔ 非仓 ⇒ 源之印 ⛔ 得判（⛔ 假印 —— apply 遇之则止）\n"
         "    assert MB.source_stamp(str(tmp_path / \"norepo\"))[\"commit\"] is None\n"),
    ]),
]

EDITS = {"bundler": bundler, "test": test}
ORDER = ["bundler", "test"]
BASES = []          # 落改后补（--verify 之用）


if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"pm_1573 之源键 · 核（bundler ／ test）", root=ROOT))