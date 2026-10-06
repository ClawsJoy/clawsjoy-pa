# -*- coding: utf-8 -*-
u"""note 内核（`core/lib/note_kernel.py`）之测（承 pm_1442 §二.2 ／ pm_1444 §二.2 之准）。

以何形调用（判通／断须附）：
  python -X utf8 -B -m pytest tests/unit/test_note_kernel.py -q

判据（逐条对 §二.2 之的）：
  ⒈ 内核三物（库根之解析 ／ 目录约定 ／ 最小 frontmatter）＋ 六面 ⛔ 删
  ⒉ 库根 ⛔ 得 ⇒ **未接（选目录）**（⛔ 崩 ／ ⛔ 静默兜底）—— 六面逐面
  ⒊ 库根在 ∧ 空 ⇒ **空库**（空 ≠ 缺）
  ⒋ 六面之往复（new ／ read ／ search ／ append ／ edit_section）＋ ⛔ 覆写
  ⒌ 径之守护（绝对径 ／ `..` ／ 越根）
  ⒍ 写之形（LF ／ UTF-8 ⛔ BOM）＋ ⛔ 删（**以调用形判** · ⛔ 免文档串自指）
  ⒎ 插件之界：面 ⇒ 走 `ToolPlugin` ＋ `_TOOL_REGISTRY`（内核三物 ⛔ 插件化）
"""
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.lib import note_kernel as NK  # noqa: E402


def test_一_内核三物与六面():
    assert NK.SUBDIRS == ("notes", "sop", "reviews", "inbox", "drafts", "assets")
    assert set(NK.FACES) == {"list", "read", "search", "create", "append", "edit_section"}
    assert "delete" not in NK.FACES and "remove" not in NK.FACES
    assert NK.FM_KEYS[:4] == ("title", "created", "updated", "tags")
    # 库根之解析 ⇒ 唯引真源（⛔ 第二份判据）
    src = io.open(str(ROOT / "core" / "lib" / "note_kernel.py"), encoding="utf-8").read()
    assert "from core.lib.paths import vault_root" in src
    assert not re.search(r"D:\\\\Obsidian|/mnt/d/Obsidian", src), u"内核载字面组织物径"


def test_二_库根不得_六面皆未接(monkeypatch):
    monkeypatch.setattr(NK, "kroot", lambda: None)
    monkeypatch.setattr(NK, "kroot_src", lambda: NK.STATE_NO_ROOT)
    got = [
        NK.face_list(root=None),
        NK.face_read("notes/a.md", root=None),
        NK.face_search("x", root=None),
        NK.face_create("notes", "a", root=None),
        NK.face_append("notes/a.md", "t", root=None),
        NK.face_edit_section("notes/a.md", "h", "t", root=None),
    ]
    # ⚠ face_list/face_search 自 kroot_state() 取 ⇒ 亦须见「未接」
    for g in got:
        assert g["ok"] is False, g
        assert g["state"] == NK.STATE_NO_ROOT, g
    # 逐面（插件之口）
    assert NK.face("list")["state"] == NK.STATE_NO_ROOT
    assert NK.face("nope")["state"] == NK.STATE_BADARG


def test_三_空库_与_缺_分立(tmp_path):
    assert NK.face_list(root=str(tmp_path))["state"] == NK.STATE_EMPTY
    r = NK.face_list(root=str(tmp_path))
    assert r["ok"] is True and r["items"] == []
    missing = tmp_path / "nope"
    assert NK.face_list(root=str(missing))["state"] == NK.STATE_MISSING


def test_四_六面之往复(tmp_path):
    root = str(tmp_path)
    c = NK.face_create("notes", "首篇", title="首篇", body="正文甲\n", tags=["a", "b"], root=root)
    assert c["ok"] and c["state"] == NK.STATE_OK and c["rel"] == "notes/首篇.md"
    # ⛔ 覆写
    assert NK.face_create("notes", "首篇", root=root)["state"] == NK.STATE_EXISTS
    # frontmatter 最小 ＋ tags
    rd = NK.face_read("notes/首篇.md", root=root)
    assert rd["meta"]["title"] == "首篇" and rd["meta"]["tags"] == "[a, b]"
    assert "正文甲" in rd["body"]
    assert "created" in rd["meta"] and "updated" in rd["meta"]
    # 追加
    ap = NK.face_append("notes/首篇.md", "追加乙", root=root)
    assert ap["ok"] and "追加乙" in NK.face_read("notes/首篇.md", root=root)["body"]
    # 改小节
    NK.face_append("notes/首篇.md", "## 节一\n旧文\n\n## 节二\n乙\n", root=root)
    es = NK.face_edit_section("notes/首篇.md", "节一", "新文", root=root)
    assert es["ok"], es
    body = NK.face_read("notes/首篇.md", root=root)["body"]
    assert "新文" in body and "旧文" not in body and "乙" in body
    # 搜
    sr = NK.face_search("新文", root=root)
    assert sr["state"] == NK.STATE_OK and sr["hits"][0]["rel"] == "notes/首篇.md"
    assert NK.face_search("绝无此字", root=root)["state"] == NK.STATE_EMPTY
    # 列
    ls = NK.face_list(root=root)
    assert ls["state"] == NK.STATE_OK and ls["total"] == 1
    # 缺节 ／ 缺件
    assert NK.face_edit_section("notes/首篇.md", "无此节", "x", root=root)["state"] == NK.STATE_MISSING
    assert NK.face_read("notes/无.md", root=root)["state"] == NK.STATE_MISSING
    assert NK.face_append("notes/无.md", "x", root=root)["state"] == NK.STATE_MISSING
    # 库名 ⛔ 合
    assert NK.face_create("其它", "a", root=root)["state"] == NK.STATE_BADARG


def test_五_径之守护(tmp_path):
    root = str(tmp_path)
    for bad in ("../x.md", "/abs.md", "D:/abs.md", "notes/../../x.md", "notes/\x00a.md", ""):
        assert NK.face_read(bad, root=root)["state"] == NK.STATE_BADREL, bad
    assert NK.safe_rel("notes/a.md") == ("notes/a.md", NK.STATE_OK)
    assert NK.safe_rel("a\\b.md") == ("a/b.md", NK.STATE_OK)


def test_六_写之形_LF_无BOM_且无删():
    src = io.open(str(ROOT / "core" / "lib" / "note_kernel.py"), encoding="utf-8").read()
    assert 'newline=""' in src, u"写须显式 LF（⛔ 平台默认）"
    assert "encoding=\"utf-8\"" in src
    for pat in (r"os\.remove\(", r"os\.unlink\(", r"shutil\.rmtree\(", r"\.unlink\("):
        assert not re.search(pat, src), u"内核含删之调用：%s" % pat


def test_六b_所写之件_LF_无BOM(tmp_path):
    NK.face_create("notes", "x", title="x", body="甲\n乙\n", root=str(tmp_path))
    b = (tmp_path / "notes" / "x.md").read_bytes()
    assert not b.startswith(b"\xef\xbb\xbf") and b"\r" not in b and b.endswith(b"\n")


def test_七_插件之界():
    from core.gateway.tool_router import _TOOL_REGISTRY, _tool_priority
    from core.tools.base import ToolPlugin
    from core.tools.note_kb import NoteKbPlugin
    assert issubclass(NoteKbPlugin, ToolPlugin)
    assert _TOOL_REGISTRY.get("note_kb") is NoteKbPlugin
    assert _tool_priority("note_kb") == 2, u"写类工具之优先级须为 2"
    assert NoteKbPlugin().validate({"action": "list"}) is True
    assert NoteKbPlugin().validate({"action": "delete"}) is False
    out = NoteKbPlugin().execute({"action": "nope"}, None)
    assert out["state"] == NK.STATE_BADARG
