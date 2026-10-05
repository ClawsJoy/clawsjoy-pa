# -*- coding: utf-8 -*-
"""Win-PA 第二大脑 · 「写进 vault 的文本件须纯 LF」反例门（CEO 2026-09-28 §一③ / §三②）。

病理：`Path.write_text()` 默认 `newline=None` ⇒ 在 **Windows 上把 `\n` 翻成 `\r\n`**
（本机实测 `write_text("x\n")` -> `b"x\r\n"`）。而 vault 是**跨平台镜像面** ——
WSL 侧按 `LF` 播种/镜像/比对 ⇒ 本侧写入一旦带 CRLF 就出三样病：
  · 同一逻辑内容按字节分成两份 ⇒ `sha16` 与对端不等（四元组对不上）
  · 镜像只能靠「归一 EOL 后逐位同」勉强过 ⇒ 判据被稀释（CEO §三② 的放宽本是给沙箱的）
  · 检索/清单的 `bytes` 读数随写入者变化 ⇒ 报数不稳
⇒ 判据 = 写 vault 一律走 `core.lib.paths.write_text_lf()`（显式 `newline=""`）。
⇒ 承「成对改 ＋ 反例门」：⛔ 不许「这次注意点」—— 那是个案，不是判据。

判据（每条都能先失败）
  A 写手脚：`write_text_lf()` 纯 LF（无 `\r`）＋ 无 BOM ＋ 自动建父目录
  B 写点实测：五个 vault 写点各写一次，落盘件必无 `\r`
  C 复扫归零：vault 写模块里的 `.write_text(` 要么带 `newline=""`，要么在**已列清**的豁免面
"""
import sys

sys.path.insert(0, ".")

from pathlib import Path

import pytest

import core.lib.paths as paths

_REPO = Path(__file__).resolve().parents[2]


def _pure_lf(p: Path) -> bool:
    return b"\r" not in p.read_bytes()


# ---------- A 写手脚 ----------


def test_A_write_text_lf_emits_pure_lf(tmp_path):
    """写手脚本身必须纯 LF —— 它是全部 vault 写点的唯一出口。"""
    p = tmp_path / "sub" / "a.md"
    assert hasattr(paths, "write_text_lf"), "core.lib.paths 缺 write_text_lf（唯一写出口）"
    paths.write_text_lf(p, "".join(["标题", chr(10), "正文", chr(10)]))
    raw = p.read_bytes()
    assert raw == "标题\n正文\n".encode("utf-8"), raw
    assert b"\r" not in raw
    assert not raw.startswith(b"\xef\xbb\xbf"), "不得带 BOM"
    assert p.parent.is_dir(), "须自动建父目录"
    # 幂等：再写一次不得累积 CR
    paths.write_text_lf(p, "a\nb\n")
    assert p.read_bytes() == b"a\nb\n"


# ---------- B 写点实测（每个写点各写一次） ----------


def _pi_cfg(vault: Path):
    return {
        "enabled": True,
        "append_pitfalls": True,
        "reviews_dir": "聊天区/复盘",
        "sops_dir": "工作区/SOPs/SOPs",
        "pitfalls_dir": "开发区/ComputerUse/Pitfalls",
        "pitfalls_file": "避坑清单.md",
    }


def test_B_task_review_is_pure_lf(tmp_path, monkeypatch):
    """`write_task_review` -> vault/聊天区/复盘/（此前 CRLF）。"""
    import core.gateway.precision_inject as pi

    monkeypatch.chdir(_REPO)
    monkeypatch.setenv("PA_VAULT_DIR", str(tmp_path))
    monkeypatch.setattr(pi, "_obsidian_cfg", lambda: _pi_cfg(tmp_path))

    p = pi.write_task_review("u1", "s1", "t1", "标题", "## 做了什么" + chr(10) + "干活")
    assert p, "写点返回空 ⇒ 门没测到东西"
    assert _pure_lf(Path(p)), "复盘件带 CRLF: " + repr(Path(p).read_bytes()[:80])


def test_B_pitfall_is_pure_lf(tmp_path, monkeypatch):
    """`append_pitfall` -> vault/开发区/ComputerUse/Pitfalls/避坑清单.md（此前 CRLF）。"""
    import core.gateway.precision_inject as pi

    monkeypatch.chdir(_REPO)
    monkeypatch.setenv("PA_VAULT_DIR", str(tmp_path))
    monkeypatch.setattr(pi, "_obsidian_cfg", lambda: _pi_cfg(tmp_path))

    p = pi.append_pitfall("这是一条足够长的踩坑记录用于通过长度守卫")
    assert p, "写点返回空 ⇒ 门没测到东西"
    assert _pure_lf(Path(p)), "避坑清单带 CRLF"


def test_B_update_sop_is_pure_lf(tmp_path, monkeypatch):
    """`update_sop` -> vault/工作区/SOPs/SOPs/（此前 CRLF）。"""
    import core.gateway.precision_inject as pi

    monkeypatch.chdir(_REPO)
    monkeypatch.setenv("PA_VAULT_DIR", str(tmp_path))
    monkeypatch.setattr(pi, "_obsidian_cfg", lambda: _pi_cfg(tmp_path))

    p = pi.update_sop("平台发布工作流", "小节甲", "正文甲" + chr(10) + "正文乙")
    assert p, "写点返回空 ⇒ 门没测到东西"
    assert _pure_lf(Path(p)), "SOP 带 CRLF"


def test_B_brain_ledger_is_pure_lf(tmp_path):
    """`vault_brain.BrainSync.sync_ledger` -> vault/收件箱/PA待办与进度.md（此前 CRLF）。"""
    from core.pa.vault_brain import BrainSync

    class _Ledger:
        def open_items(self, kinds):
            return [{"title": "写点甲", "id": "t1", "kind": "todo", "due": None}]

    p = BrainSync(_Ledger(), vault_dir=tmp_path).sync_ledger()
    assert p, "写点返回空 ⇒ 门没测到东西"
    assert _pure_lf(Path(p)), "PA 待办件带 CRLF"


def test_B_draft_box_is_pure_lf(tmp_path, monkeypatch):
    """`DraftBoxPlugin.write_draft` -> vault/草稿箱/<platform>/（此前 CRLF）。"""
    import core.plugins.draft_box.base as db

    monkeypatch.chdir(_REPO)
    monkeypatch.setenv("PA_VAULT_DIR", str(tmp_path))
    root = tmp_path / "vault"
    root.mkdir()
    monkeypatch.setattr(db, "_vault_root", lambda: root)

    box = db.DraftBoxPlugin()
    box.platform = "测试台"
    got = box.write_draft("标题甲", "正文甲" + chr(10) + "正文乙")
    assert got.get("success"), got
    assert _pure_lf(Path(got["path"])), "草稿件带 CRLF"


# ---------- C 复扫归零 ----------


_VAULT_WRITER_FILES = (
    "core/lib/paths.py",
    "core/pa/vault_brain.py",
    "core/plugins/draft_box/base.py",
    "core/plugins/media_processor.py",
    "core/gateway/precision_inject.py",
    "core/tools/write_file.py",
)

# 豁免面（**逐条列清** · 未列即视为未豁免）：
#   ① 沙箱镜像两处 —— CEO 2026-09-28 §三② 判「可不动」（沙箱面 CRLF 属目标形态，
#      镜像判据已改「归一 EOL 后逐位同」）。⛔ 不得扩大本清单 —— 那是把判据抹掉。
#   ② `precision_inject.py` 三处 —— **已落**（2026-09-28 · 该批发完即落）：`fpath`×2
#      ＋ `pfile`×1 已走 `write_text_lf()` ⇒ 豁免面清空（_DEFERRED_WRITE_OK = {}）。
#      本条是「豁免面必须逐条列清」的落实：豁免的**数量**也须机检
#      （少了 = 有人偷偷接了；多了 = 有人偷加豁免）—— 现声明 0 处，改回裸写即红。
_SANDBOX_WRITE_OK = (
    'dst.write_text(_vtxt, encoding="utf-8")',
    '_dst.write_text(txt, encoding="utf-8")',
)
# 2026-09-28 落毕：precision_inject.py 三处已走 write_text_lf ⇒ 待办豁免面**已清空**（空 = 无豁免）。
_DEFERRED_WRITE_OK = {}
# ③ `core/tools/write_file.py` 的非 vault 分支 —— `_emit_vault_safe()` 里**唯一**一处裸写
#    （vault 面走 write_text_lf；非 vault 面如 `.bat` 可能本来就要 CRLF ⇒ 不动）。
#    该件已在扫面内 ⇒ 再出现第二处裸写即红（豁免面**逐条列清 ＋ 数量机检**）。
_NONVAULT_WRITE_OK = (
    'path.write_text(text, encoding="utf-8")',
)


def test_C_no_bare_write_text_in_vault_writers():
    """复扫归零：vault 写模块里 `.write_text(` 要么带 `newline=""`，要么在**已列清**的豁免面。"""
    bad = []
    deferred_seen = {}
    nonvault_seen = []
    for rel in _VAULT_WRITER_FILES:
        allow = _SANDBOX_WRITE_OK + _NONVAULT_WRITE_OK + _DEFERRED_WRITE_OK.get(rel, ())
        for i, line in enumerate((_REPO / rel).read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if ".write_text(" not in s:
                continue
            _head = s.split(".write_text(")[0]
            # 只认**真调用**行（`obj.write_text(`）：散文/docstring 里提及的不算写点
            if not _head or any(not (ch.isalnum() or ch in "_.[]") for ch in _head):
                continue
            if s in allow:
                if rel in _DEFERRED_WRITE_OK and s in _DEFERRED_WRITE_OK[rel]:
                    deferred_seen.setdefault(rel, []).append(i)
                if s in _NONVAULT_WRITE_OK:
                    nonvault_seen.append((rel, i))
                continue
            if 'newline=""' in s or "newline=''" in s:
                continue
            bad.append("%s:%d %s" % (rel, i, s))
    assert bad == [], "vault 写点未走 write_text_lf（Windows 上会翻 CRLF）: " + repr(bad)
    for rel, want in _DEFERRED_WRITE_OK.items():
        assert len(deferred_seen.get(rel, ())) == len(want), (
            "待办豁免面的数量变了（%s）: 实见 %r · 声明 %d 处"
            % (rel, deferred_seen.get(rel), len(want))
        )
    assert len(nonvault_seen) == len(_NONVAULT_WRITE_OK), (
        "非 vault 豁免面数量变了: 实见 %r · 声明 %d 处"
        % (nonvault_seen, len(_NONVAULT_WRITE_OK))
    )


# ---------- D 工具出口实测：write_file 工具写 vault 面须纯 LF ----------


class _WfCtx:
    """write_file 工具的最小 ToolContext 桩（同 tests/unit/test_write_file_long.py）。"""

    def __init__(self, base):
        self.base = base
        self.messages = []
        self.consecutive_reads = {}
        self.consecutive_lists = {}
        self.last_read_fingerprints = {}
        self.user_id = "u1"
        self.session_id = "s1"
        self.recap_checkpoint = lambda *a, **k: None
        self.task_name_async = "t"
        self.round = 1
        self.update_world_model = lambda *a, **k: 0
        self.sandbox_git_pre_write = lambda *a, **k: None
        self.sandbox_git_post_write = lambda *a, **k: None
        self.git_status = lambda *a, **k: {}
        self.policy = {"retry": {"js_rollback_limit": 3}}
        self.js_rollback_count = {}

    def resolve_path(self, base, p):
        return base / p


def test_D_write_file_tool_vault_face_is_pure_lf(tmp_path, monkeypatch):
    """`core/tools/write_file.py` 工具（此前裸 `Path.write_text`）写 vault 面 ⇒ 必纯 LF。

    ⛔ 该件原先**不在本门扫面内**（无 `vault_root()` 引用）⇒ 判据只覆盖一半出口
    （与「C1 门盲区」同型）；本批扩面 ＋ 走唯一出口。本条＝先红后绿的「后绿」。
    """
    import core.tools.write_file as wf

    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setenv("PA_VAULT_DIR", str(vault))
    ctx = _WfCtx(vault)
    r = wf.WriteFilePlugin().execute(
        {"path": "复盘/甲.md", "content": "l1" + chr(10) + "l2" + chr(10)}, ctx)
    assert r.get("success"), r
    raw = (vault / "复盘" / "甲.md").read_bytes()
    assert raw == "l1\nl2\n".encode("utf-8"), raw
    assert b"\r" not in raw, "write_file 工具写 vault 面翻了 CRLF: %r" % raw


def test_D_nonvault_face_unchanged(tmp_path, monkeypatch):
    """非 vault 面（无跨平台判据）⇒ **行为不变**（仍走平台默认换行）—— 防「一刀切」改动扩大射程。"""
    import core.tools.write_file as wf

    base = tmp_path / "outside"
    base.mkdir()
    monkeypatch.setenv("PA_VAULT_DIR", str(tmp_path / "vault_absent"))
    ctx = _WfCtx(base)
    r = wf.WriteFilePlugin().execute({"path": "a.md", "content": "l1" + chr(10) + "l2" + chr(10)}, ctx)
    assert r.get("success"), r
    assert (base / "a.md").read_bytes() == b"l1\r\nl2\r\n", "非 vault 面行为被改动了"
