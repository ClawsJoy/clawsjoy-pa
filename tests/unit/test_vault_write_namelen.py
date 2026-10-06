# -*- coding: utf-8 -*-
"""Win-PA 第二大脑 · 「件名 UTF-8 ≤ 200 B · 写侧 fail-loud」反例门。

病理：**命名无上限**（DS 2026-09-28 逮：vault 里有超名件，WSL 侧 `ENAMETOOLONG` 读不到
⇒ 「本侧看得见、对端读不到」的假在场）。根因 ⛔ 不是 FS 毛病 —— 是**写侧没有上限判据**。
⇒ 判据 = 任何写进 vault 的件名，UTF-8 字节数 > 200 即**当场拒写**（fail-loud），
   落点在唯一写出口 `core.lib.paths.write_text_lf()` → `check_name_len()`。
⇒ 承「成对改 ＋ 反例门」：⛔ 不许「写的时候注意点」—— 那是个案，不是判据。

判据（每条都能先失败）
  A 短名放行：`check_name_len()` 回字节数；`write_text_lf()` 正常落盘
  B 边界 200 B **放行**（⛔ 不早拦：上限是「不超过」）
  C 201 B **拒写**（`ValueError`）
  D ⭐ **按字节不按字数**：70 个中文字 = 210 B ⇒ **必拒**（按字数实现的门会漏 —— 这条先失败）
  E 拒写**零副作用**：⛔ 不落半件 ＋ ⛔ 不建父目录（守护在 `mkdir` **之前**）
  F 错误可读：`ValueError`（⛔ 非 `OSError`）＋ 文本含「实得字节数 ＋ 上限」
"""
import sys

sys.path.insert(0, ".")

from pathlib import Path

import pytest

import core.lib.paths as paths

_REPO = Path(__file__).resolve().parents[2]
LIMIT = 200


def _name_of(nbytes: int) -> str:
    """构造 **UTF-8 恰好 nbytes** 的件名（尾缀 .md = 3 B ⇒ 前缀补足）。"""
    assert nbytes >= 3, "至少容得下 .md"
    return "a" * (nbytes - 3) + ".md"


# ---------- A 短名放行 ----------


def test_A_short_name_passes_and_writes(tmp_path):
    assert hasattr(paths, "check_name_len"), "core.lib.paths 缺 check_name_len（写侧上限判据）"
    name = _name_of(50)
    assert paths.check_name_len(tmp_path / name) == 50
    p = paths.write_text_lf(tmp_path / name, "".join(["x", chr(10)]))
    assert p.is_file() and p.read_bytes() == b"x" + bytes([10])


# ---------- B 边界：200 B 放行 ----------


def test_B_boundary_200_bytes_passes(tmp_path):
    """上限语义 = 「不超过」⇒ 恰好 200 B 必须**放行**（⛔ 不早拦）。"""
    name = _name_of(LIMIT)
    assert len(name.encode("utf-8")) == LIMIT
    assert paths.check_name_len(tmp_path / name) == LIMIT
    assert paths.write_text_lf(tmp_path / name, "ok" + chr(10)).is_file()


# ---------- C 201 B 拒写 ----------


def test_C_201_bytes_rejected(tmp_path):
    name = _name_of(LIMIT + 1)
    assert len(name.encode("utf-8")) == LIMIT + 1
    with pytest.raises(ValueError):
        paths.check_name_len(tmp_path / name)
    with pytest.raises(ValueError):
        paths.write_text_lf(tmp_path / name, "boom")


# ---------- D ⭐ 按字节不按字数 ----------


def test_D_byte_based_not_char_based(tmp_path):
    """70 个中文字：**字数 70 ≤ 200**，但 **字节 210 > 200** ⇒ 必拒。

    ⛔ 这条是本门的「有牙」判据：按 `len(name)`（字数）实现的门在此**必漏**。
    """
    name = "\u4e2d" * 70 + ".md"
    name = name.encode("utf-8").decode("utf-8")  # 显式往返，防源文件编码歧义
    assert len(name) <= LIMIT, "字数看着很短（%d ≤ %d）" % (len(name), LIMIT)
    assert len(name.encode("utf-8")) > LIMIT, "字节超限（%d > %d）" % (len(name.encode("utf-8")), LIMIT)
    with pytest.raises(ValueError):
        paths.check_name_len(tmp_path / name)


# ---------- E 拒写零副作用 ----------


def test_E_reject_leaves_no_file_and_no_parent(tmp_path):
    """守护在 `mkdir` **之前** ⇒ 拒写后：⛔ 无半件、⛔ 无新建父目录。"""
    deep = tmp_path / "nope"
    name = _name_of(LIMIT + 40)
    with pytest.raises(ValueError):
        paths.write_text_lf(deep / name, "boom")
    assert not deep.exists(), "拒写却建了父目录 ⇒ 守护位置错（应在 mkdir 之前）"
    assert not (deep / name).exists()
    assert list(tmp_path.iterdir()) == [], "拒写却落了东西"


# ---------- F 错误可读 ----------


def test_F_error_is_valueerror_and_names_numbers(tmp_path):
    name = _name_of(LIMIT + 7)
    try:
        paths.check_name_len(tmp_path / name)
    except ValueError as e:
        msg = str(e)
    except OSError as e:  # pragma: no cover - 反例：⛔ 不该是 OSError
        raise AssertionError("拒写应为 ValueError（调用方可捕），实得 OSError: %s" % e)
    else:  # pragma: no cover
        raise AssertionError("超名未拒写 ⇒ 判据不在场")
    assert str(LIMIT + 7) in msg, "错误文本应含实得字节数（%d）" % (LIMIT + 7)
    assert str(LIMIT) in msg, "错误文本应含上限（%d）" % LIMIT


# ---------- G 父目录段（逐段守护） ----------


def test_G_parent_segment_too_long_rejected(tmp_path):
    """``NAME_MAX`` 是**逐段**约束 ⇒ 「件名短 + 父目录段超限」同样 ``ENAMETOOLONG``。

    ⛔ 只查 basename 的门在此**必漏**（承 DS 2026-09-28 裁「守护扩到父目录段」）。
    """
    long_dir = tmp_path / ("D" * 210)
    assert not long_dir.exists()
    with pytest.raises(ValueError):
        paths.check_path_len(long_dir / "ok.md")
    with pytest.raises(ValueError):
        paths.write_text_lf(long_dir / "ok.md", "x")
    assert not long_dir.exists(), "拒写却建了超名父目录"


def test_H_check_path_len_names_the_offending_segment(tmp_path):
    """错误须报**是哪一段**超限（便于定位）；且**全短**时返回最长段字节数。"""
    seg = "P" * 210
    try:
        paths.check_path_len(tmp_path / seg / "ok.md")
    except ValueError as e:
        assert seg in str(e), "错误文本未点出超限段: %s" % e
    else:  # pragma: no cover
        raise AssertionError("父目录段超限未拒")
    assert paths.check_path_len(tmp_path / "a" / "b.md") <= 200


# ---------- I 复扫：非文本写出口也须有守护 ----------


# 非文本写出口清单（**逐条列清** · 数量机检 —— 承「豁免/覆盖面须逐条列清」）：
#   `shutil.copy2` / `shutil.move` 不走 write_text_lf ⇒ 必须**就近**挂 check_path_len，
#   否则「件名上限」在这条出口上**不在场**（判据只覆盖一半出口）。
_NONTEXT_SITES = {
    "core/plugins/media_processor.py": 1,
    "core/pa/vault_brain.py": 1,
    "core/plugins/draft_box/base.py": 3,
}


def test_I_nontext_write_sites_have_guard():
    """5 处 非文本写出口（copy2/move）**前一行**必有 ``check_path_len(``；数量机检。"""
    seen = {}
    for rel, want in _NONTEXT_SITES.items():
        lines = (_REPO / rel).read_text(encoding="utf-8").splitlines()
        hits = []
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith("shutil.copy2(") or s.startswith("shutil.move("):
                prev = lines[i - 1].strip() if i else ""
                hits.append((i + 1, "check_path_len(" in prev))
        seen[rel] = hits
        assert len(hits) == want, "%s: 非文本写出口 %d 处，声明 %d 处（变了须同步声明）" % (rel, len(hits), want)
        bad = [ln for ln, ok in hits if not ok]
        assert bad == [], "%s: 这些非文本写出口**前一行无守护** ⇒ %r" % (rel, bad)


# ---------- J 工具出口实测：write_file 工具写 vault 面须过件名/路径段守护 ----------


class _WfCtx2:
    """write_file 工具的最小 ToolContext 桩。"""

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


def test_J_write_file_tool_vault_face_name_guard(tmp_path, monkeypatch):
    """`core/tools/write_file.py` 工具写 vault 面：父目录段 > 200 B ⇒ **拒写 · 零副作用**。

    ⛔ 该出口原先无守护（裸 `Path.write_text`）⇒ 超名件会落成「本侧看得见、对端读不到」。
    """
    import core.tools.write_file as wf

    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setenv("PA_VAULT_DIR", str(vault))
    ctx = _WfCtx2(vault)

    long_seg = "D" * 210
    r = wf.WriteFilePlugin().execute({"path": long_seg + "/b.md", "content": "x" + chr(10)}, ctx)
    assert r.get("success") is False, r
    assert "200" in str(r.get("error", "")), r
    assert not (vault / long_seg).exists(), "拒写却建了超名父目录（须在 mkdir 之前查）"

    ok = wf.WriteFilePlugin().execute({"path": "复盘/短.md", "content": "x" + chr(10)}, ctx)
    assert ok.get("success") is True, ok
    assert (vault / "复盘" / "短.md").is_file()


def test_K_derived_bak_uses_derived_budget(tmp_path, monkeypatch):
    """`.bak` 派生名按**派生名预算**（224）判 ⇒ 190 B 件名（＋`.bak` = 194 B）**放行**。

    ⛔ 若拿 200 去卡派生名 ⇒ 会误拒 CEO 判为合法的派生件（200 ＋ 24 ≤ 255）。
    """
    import core.tools.write_file as wf

    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setenv("PA_VAULT_DIR", str(vault))
    ctx = _WfCtx2(vault)

    name = "a" * 186 + ".md"  # 189 B
    assert len(name.encode("utf-8")) == 189
    p = vault / name
    p.parent.mkdir(parents=True, exist_ok=True)
    # ⚠ 承 TD_1408 之定性：原 "old" ⟷ 新 "new" ＝ **零相似** ⇒ 撞 write_file 之相似度闸
    #   （core/tools/write_file.py:243 · 唯「已批准」∨ 目标在 `data/tmp/` 方可免）⇒ 本测之本旨
    #   （`.bak` 之**派生名预算** · 224 B）被其掩 ／ 且其绿红随 basetemp 之位而变 ⇒ 改以**高相似**之料。
    p.write_bytes(b"old\nline1\nline2\nline3\n")
    r = wf.WriteFilePlugin().execute({"path": name, "content": "new\nline1\nline2\nline3\n"}, ctx)
    assert r.get("success") is True, r
    assert (vault / (name + ".bak")).is_file(), "派生名 .bak 未落（应按 224 B 预算放行）"
