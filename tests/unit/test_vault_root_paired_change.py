# -*- coding: utf-8 -*-
"""Win-PA 用 Obsidian 作第二大脑 · 落地反例门（CEO 2026-09-28 ④/⑤/③ · 老板已批）。

病理：脑根（vault 根）此前有**三份口径** ——
  ① `config/v9/execution_policy.yaml:obsidian.vault_path`（写死 WSL 挂载形态）
  ② `core/lib/paths.py:vault_root()`（探测式 · 已解耦未启用）
  ③ 两处**安全判据**各自写死的路径串（`guards/registry.py` · `v9_bridge/tool_runner.py`）
⇒ 脑根一改，安全判据**在场却打错对象**（判据还在，判的不是真对象）。
⇒ 纪律 = **成对改 ＋ 反例门**：⛔ 不许「只加新串」—— 那是把 1 个硬编码换成 N 个，
   判据仍不跟随真源 ⇒ 门一关照样瞎。

判据（每条都能先失败）
  A 两形态都命中：Windows 原生 `D:\\...` 与 WSL 形态 `/mnt/d/...`
  B 判据跟随真源：`PA_VAULT_DIR` 一变判据跟着变（证判据出自 vault_root()，⛔ 非硬编码）
  C 负例：非 vault 路径必不命中（防放宽 —— 放宽就等于没有判据）
  D 检索面排除：`_冷区`/`_垃圾箱`/`.obsidian`/`Templates` 不参与检索（CEO ⑧ 终裁）
  E 单一真源：三个 vault 根读取口同值
  F 知识指针指向**活区真件**且可读（CEO ② / ③）
"""
import sys

sys.path.insert(0, ".")

from pathlib import Path

import pytest

import core.lib.paths as paths

_REPO = Path(__file__).resolve().parents[2]
_REAL_VAULT = Path("D:/Obsidian/ClawsJoy/ClawsJoy")

WIN_VAULT_FILE = "D:\\Obsidian\\ClawsJoy\\ClawsJoy\\收件箱\\x.md"
WSL_VAULT_FILE = "/mnt/d/Obsidian/ClawsJoy/ClawsJoy/收件箱/x.md"


def _continuation_vault_write(cmd):
    """续跑期「禁写 vault」判据（三条写通道的统一入口）。"""
    from core.gateway.v9_bridge.tool_runner import _is_vault_write

    return _is_vault_write("execute_command", {"command": cmd})[0]


def _registry_vault_hint(path, sandbox_base):
    """读工具路径越权时的「这是不是 vault」归类判据；返回 True/False/None(未被拦)。"""
    from core.gateway.guards.registry import EscapeGuard

    res = EscapeGuard().check(
        {"tool": "read_file", "args": {"path": path}, "sandbox_base": sandbox_base}
    )
    if not res:
        return None
    return bool((res.get("blocked") or {}).get("vault_hint"))


# ---------- A 两形态都命中 ----------


def test_A_windows_native_vault_path_is_recognized(tmp_path):
    """脑根在 Windows 上就是 `D:\\Obsidian\\...`；判据须认（⛔ 不认 = 判据打错对象）。"""
    assert _continuation_vault_write("echo x >> " + WIN_VAULT_FILE) is True
    assert _registry_vault_hint(WIN_VAULT_FILE, str(tmp_path)) is True


def test_A_wsl_form_vault_path_is_recognized(tmp_path):
    """同一份 vault 的 WSL 形态（`/mnt/d/...`）须**同时**认（跨平台文本回落）。"""
    assert _continuation_vault_write("echo x >> " + WSL_VAULT_FILE) is True
    assert _registry_vault_hint(WSL_VAULT_FILE, str(tmp_path)) is True


# ---------- B 判据跟随真源（反「只加新串」） ----------


def test_B_judges_follow_vault_root(tmp_path, monkeypatch):
    """把真源指到别处 ⇒ 判据须**跟着走**。只加新串的实现过不了这条。"""
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setenv("PA_VAULT_DIR", str(vault))

    assert str(paths.vault_root()) == str(vault)
    assert paths.is_vault_path(str(vault / "a.md")) is True
    assert _continuation_vault_write("echo x >> " + str(vault / "a.md")) is True
    # 归类判据只在「路径越权」分支里跑 ⇒ 须让 vault 落在只读白名单**外**才触得到；
    # 本机测试临时目录在仓库内（PROJECT_ROOT）⇒ 把项目根挪开，模拟真实布局。
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path / "proj"))
    # 归类判据只在「路径越权」分支里跑 ⇒ 沙箱要**包不住**这个 vault 才触得到
    # （`_is_read_path_escape` 的白名单含沙箱根与其父目录，故沙箱须再深一层）。
    assert _registry_vault_hint(str(vault / "a.md"), str(tmp_path / "sb" / "session")) is True

    # 标记集须含**实算**出来的真源（证其来源是 vault_root() 而非字面量）
    markers = [str(m).replace("\\", "/").lower() for m in paths.vault_markers()]
    assert any(str(vault).replace("\\", "/").lower() in m for m in markers)


# ---------- C 负例：不许放宽 ----------


def test_C_non_vault_paths_are_not_claimed():
    """非 vault 路径必不命中 —— 判据放宽就等于没有判据。"""
    for p in (
        "D:\\clawsjoy_v9\\data\\reports\\a.md",
        "/tmp/a.md",
        "data/reports/a.md",
        "D:\\Obsidian\\OtherVault\\a.md",
    ):
        assert paths.is_vault_path(p) is False, p
    for p in (
        "D:\\clawsjoy_v9\\data\\reports\\a.md",
        "/tmp/a.md",
        "data/reports/a.md",
    ):
        assert _continuation_vault_write("echo x >> " + p) is False, p


def test_C_continuation_judge_keeps_its_conservative_net():
    """保守兜底**保留**（只可收紧不可放宽）：命令串含 `Obsidian` 字面即按 vault 写处理。

    ⇒ 该判据比 is_vault_path() 精确判据**宽**（别的 Obsidian 库也算）——
      宁可在续跑期多拦，不可漏拦。⛔ 不得据此认为精确判据可省。
    """
    assert _continuation_vault_write("echo x >> D:\\Obsidian\\OtherVault\\a.md") is True
    assert paths.is_vault_path("D:\\Obsidian\\OtherVault\\a.md") is False


def test_C_vault_reads_are_still_not_writes():
    """读不得被判成写（2026-09-13 的既有约束，成对改不得把它推翻）。"""
    for cmd in (
        "cat " + WIN_VAULT_FILE,
        "grep -rn foo " + WSL_VAULT_FILE,
        "ls /mnt/d/Obsidian/ClawsJoy",
    ):
        assert _continuation_vault_write(cmd) is False, cmd


# ---------- D 检索面排除（CEO ⑧ 终裁） ----------


def _mk_vault(tmp_path):
    vault = tmp_path / "vault"
    for rel in (
        "_冷区/x.md",
        "_垃圾箱/y.md",
        ".obsidian/z.md",
        "Templates/t.md",
        "工作区/ok.md",
        "聊天区/复盘/r.md",
    ):
        f = vault / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# %s\n\n正文\n" % rel, encoding="utf-8")
    return vault


def test_D_excluded_dirs_do_not_participate_in_retrieval(tmp_path, monkeypatch):
    """`_冷区`/`_垃圾箱` 是**排除面**，不得进检索/清单（进了 = 自相矛盾）。"""
    import core.gateway.precision_inject as pi

    vault = _mk_vault(tmp_path)
    monkeypatch.setattr(pi, "_vault_path", lambda: str(vault))
    monkeypatch.setattr(
        pi, "_obsidian_cfg", lambda: {"enabled": True, "reviews_dir": "聊天区/复盘"}
    )

    want = {"工作区/ok.md", "聊天区/复盘/r.md"}
    assert {r["rel_path"] for r in pi._scan_vault()} == want
    assert {r["rel_path"] for r in pi.list_knowledge_files()} == want


def test_D_exclusion_is_configurable(tmp_path, monkeypatch):
    """排除名单可配（配置为唯一来源）—— 配了就以配置为准。"""
    import core.gateway.precision_inject as pi

    vault = _mk_vault(tmp_path)
    monkeypatch.setattr(pi, "_vault_path", lambda: str(vault))
    monkeypatch.setattr(
        pi,
        "_obsidian_cfg",
        lambda: {"enabled": True, "reviews_dir": "聊天区/复盘", "exclude_dirs": ["工作区"]},
    )

    got = {r["rel_path"] for r in pi._scan_vault()}
    assert "工作区/ok.md" not in got
    assert "_冷区/x.md" in got


# ---------- E 单一真源 ----------


def test_E_single_source_for_vault_root(tmp_path, monkeypatch):
    """三个 vault 根读取口（网关/媒体/草稿箱）须同值 —— ⛔ 不许三份口径。"""
    import core.gateway.precision_inject as pi
    import core.plugins.draft_box.base as db
    import core.plugins.media_processor as mp

    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setenv("PA_VAULT_DIR", str(vault))
    monkeypatch.chdir(_REPO)

    assert Path(paths.vault_root()).resolve() == vault.resolve()
    assert Path(pi._vault_path()).resolve() == vault.resolve()
    assert Path(mp._vault_root()).resolve() == vault.resolve()
    assert Path(db._vault_root()).resolve() == vault.resolve()


# ---------- F 知识指针 = 活区真件 ----------


EXCLUDED_TOP = ("_冷区", "_垃圾箱")


@pytest.mark.skipif(not _REAL_VAULT.is_dir(), reason="本机无 Obsidian vault")
def test_F_knowledge_pointers_hit_live_files(monkeypatch):
    """CEO ②③：知识指针须落在**活区真件**上（⛔ 不认 `_冷区`；⛔ 不许 4/4 断链）。"""
    import core.gateway.precision_inject as pi

    monkeypatch.setenv("PA_VAULT_DIR", str(_REAL_VAULT))
    monkeypatch.chdir(_REPO)
    # ⭐ pm_1517 §二.2（**测须自足** · 器取之实）：本件之红曾**取决于同进程先跑之件** ——
    #   `pi._cfg_roots()` 乃 `lru_cache(maxsize=1)` ∧ 其内 `_obsidian_cfg()` 以**相对径**开
    #   `config/v9/execution_policy.yaml` ⇒ 前件 `chdir(tmp_path)` 后已填缓存（回落 `SOPs`）
    #   ⇒ 本件 `chdir(_REPO)` 亦得**旧缓存** ⇒ 假红（测依外之序 ⇒ 器之病）。
    #   ⇒ **自清**（承本模块 `cache_clear()` 之既有式 · 见 precision_inject.py:169）。
    pi._cfg_roots.cache_clear()
    pi.reset_inject_cfg()
    root = paths.vault_root()
    cfg = pi._obsidian_cfg()

    assert cfg.get("enabled") is True
    for key in ("sops_dir", "pitfalls_dir"):
        rel = str(cfg.get(key) or "")
        assert rel, key
        assert rel.split("/")[0] not in EXCLUDED_TOP, (key, rel)
        assert (root / rel).is_dir(), (key, rel)

    for key in ("平台发布工作流", "番茄推广SOP", "视频制作SOP", "避坑清单"):
        got = pi.read_knowledge_file(key, max_chars=200)
        assert got is not None and got.get("exists") is True, key
        p = str(got.get("path") or "")
        assert p and all(x not in p for x in EXCLUDED_TOP), (key, p)