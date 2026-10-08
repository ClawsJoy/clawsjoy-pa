# -*- coding: utf-8 -*-
u"""入仓之守（pm_1580 §二.4）：本仓（tracked）之件 ⛔ 载「个人痕」—— 扫 `git ls-files`。

二类（判据 · 一处定形）：
  ⭐ HARD（须 ＝ 0）：个人邮箱 ／ 用户档之径（盘符 ＋ `Users` 目录之形）／ 裸用户名。
     由：真 PII —— 认得出「是谁 ／ 哪台机」· 一 push 即出到外网之盘。
  ⭐ LEGACY（须 ＝ 基）：本机之库根（盘符 ＋ 库名）／ WSL 之家（`/home/<名>`）／
     开发机之根（盘符 ＋ paseo ／ codex ／ npm ／ clawsjoy 之根）／ 组织物之名（面名三串）。
     留 ∵ **运行 ／ 组织版所必需**（真源表 ／ 径归一 ／ 面之组织定位）—— 逐处之由见回件
     pm_1581。⚠ 其剔之准 ⛔ 随族（⛔ 一刀切 —— 那会把「运行所必需」一并清掉）。
     由：⛔ 静增（其数 ＝ 面之量 ⇒ 须可回指）｜⚠ 清之则**须并降基**（一处定形）。

⚠ 本档 ⛔ 载其字面：诸式皆以**碎片**拼成（如 `"fly" + "bo"`）⇒ 本档自扫亦清
  ⇒ **⛔ 自指之洞**（⛔ 以「排除本档」为解 —— 那会把本档留作藏身之所）。

何形调用：python -X utf8 -B -m pytest tests/unit/test_repo_no_personal_traces.py -q
"""
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: 用户名（碎片拼 · 本档自清）—— 先于下文用
_U = "fly" + "bo"
#: 个人邮箱（同上）
_MAIL = _U + "y_qu" + "@" + "163" + ".com"
#: 库根之名 ／ 面名（同上）
_OBS = "Obsid" + "ian"
_ORG = ("paseo" + "-" + "pm", u"\u5185\u5bb9" + u"\u5de5\u574a", u"\u4fe1" + u"\u901a")
#: 盘符之式（`[\\/]{1,2}` 兼收源码之逸写形 · 承 pm_1580 之「并扫逸写之形」）
_ABS = r"[A-Za-z]:[\\/]{1,2}"

HARD = {
    u"个人邮箱": re.compile(re.escape(_MAIL), re.I),
    u"用户档之径": re.compile(_ABS + r"Users[\\/]{1,2}" + _U + r"\b", re.I),
    u"裸用户名": re.compile(r"(?<![/\\])" + _U, re.I),
}
LEGACY = {
    u"本机之库根": re.compile(_ABS + _OBS),
    u"WSL 之家": re.compile(r"/home/" + _U),
    u"开发机之根": re.compile(_ABS + r"(paseo|codex|npm|clawsjoy)[_-]"),
    u"组织物之名": re.compile(u"|".join(re.escape(x) for x in _ORG)),
}

#: 日当值（器取 · 2026-10-08 二次核毕 · pm_1936 §二 之裁 ⓜ）—— **须 ＝ 实**：增 ⇒ 红（⛔ 静增）；
#: 减 ⇒ 红（一处定形：清了就并降基）。
#: ⭐ 改基之由（**逐处列毕** · 承 TD_1919 §一「凡报 N 处须先逐处列毕再数」之戒）——
#:   ① 本机之库根 19 ⇒ 20（8 处 · 盘符 ＋ 库名 之「运行必需」之径）：
#:      test_vault_root_paired_change(6) ／ core/lib/paths.py(5) ／ scripts/dev/投一步.py(2) ／
#:      test_tools_path_true_source(2) ／ tools/win_alias_bridge.py(2) ／ scripts/win_pa/静默启动.vbs(1) ／
#:      test_vault_write_faces(1) ／ tools/scan_heartbeat.mjs(1)。
#:   ② WSL 之家 1（1 处 · 不变）：test_file_isolation_fix(1)。
#:   ③ 开发机之根 16 ⇒ 30（20 处 · 产线诸根之径 · 皆「运行必需」）：
#:      test_pa_feedback_1635(4) ／ scripts/dev/投一步.py(3) ／ test_data_root_1698(2) ／
#:      test_vault_root_paired_change(2) ／ test_vault_write_faces(2) ／ tools/scan_heartbeat.mjs(2) ／
#:      tools/win_alias_bridge.py(2) ／ config/v9/vault_write_faces.yaml(1) ／ core/lib/config_helper.py(1) ／
#:      core/lib/paths.py(1) ／ scripts/dev/safe_edit.py(1) ／ scripts/dev/scan_abs_paths.py(1) ／
#:      scripts/win_pa/install_win_pa.py(1) ／ scripts/win_pa/netmachine_steps.md(1) ／ shell/main.js(1) ／
#:      test_pa_face_clean_1853(1) ／ test_pa_first_run(1) ／ test_pa_shell_bridge_1657(1) ／
#:      test_tools_path_true_source(1) ／ test_vector_center_guard_1694(1)。
#:   ④ 组织物之名 100 ⇒ 109（31 处 · 面之组织定位：组织名三串）：
#:      core/pa/gateway_routes.py(16) ／ scripts/win_pa/boot_resume.py(15) ／ config/v9/vault_write_faces.yaml(10) ／
#:      core/pa/resume_face.py(10) ／ core/pa/env_face.py(8) ／ scripts/dev/投一步.py(6) ／
#:      scripts/dev/recipes/edit_闸三_tou1.py(4) ／ core/gateway/ui_state.py(3) ／
#:      docs/reports/platform_publish_workflow.md(3) ／ scripts/dev/查散落浏览器.py(3) ／ web/pa/faces/selfdesc.js(3) ／
#:      docs/design/v9_pa_capability_pluginization_standard.md(2) ／
#:      scripts/dev/recipes/edit_1057_元问答话与死件路界与器病.py(2) ／
#:      scripts/dev/recipes/edit_接线批四_丙己庚.py(2) ／ scripts/dev/scan_abs_paths.py(2) ／
#:      scripts/win_pa/make_client_bundle.py(2) ／ scripts/win_pa/pa_nowindow.py(2) ／
#:      scripts/win_pa/stop_win_pa.bat(2) ／ tests/unit/test_pa_kb_col.py(2) ／ core/pa/agent_scan.py(1) ／
#:      core/routes/skill_routes.py(1) ／ scripts/dev/recipes/edit_1055_源标与拒答与死件直读.py(1) ／
#:      scripts/dev/scan_line_refs.py(1) ／ scripts/win_pa/netmachine_check.py(1) ／
#:      scripts/win_pa/task_migrate.py(1) ／ scripts/win_pa/净机安装一页.md(1) ／
#:      tests/unit/test_pa_faces_lazy.py(1) ／ tests/unit/test_stray_chrome_1898.py(1) ／
#:      tests/unit/test_today_boot_1852.py(1) ／ tools/win_alias_bridge.py(1) ／ web/pa/faces/sources.js(1)。
#:   ⭐ 本批之新件 ＋4（**悉在 ④** · 承 pm_1936 §二.2ⓝ 认「正当」）：scripts/dev/查散落浏览器.py(3 ——
#:      散落实例「归属判」之表 · **功能必需**) ＋ tests/unit/test_stray_chrome_1898.py(1)。
#:   ⚠ HARD（邮箱 ／ 用户档之径 ／ 裸名）仍 ＝ 0（pm_1936 §二.3ⓜ 之守 · 一手核我之新件皆 0）。
BASELINE = {u"本机之库根": 20, u"WSL 之家": 1, u"开发机之根": 30, u"组织物之名": 109}


def _tracked(root):
    r = subprocess.run(["git", "-C", root, "-c", "core.quotepath=false", "ls-files"],
                       capture_output=True)
    return [x.decode("utf-8", "replace") for x in (r.stdout or b"").splitlines() if x.strip()]


def scan(root=None):
    u"""还 {family: [(rel, line_no, line_text)]}—— 出包侧之同形扫。
    ⛔ 跳二进制（首 4 KiB 含 NUL）。"""
    root = root or ROOT
    out = {k: [] for k in list(HARD) + list(LEGACY)}
    for rel in _tracked(root):
        p = os.path.join(root, rel.replace("/", os.sep))
        try:
            raw = open(p, "rb").read()
        except Exception:
            continue
        if b"\x00" in raw[:4096]:
            continue
        try:
            txt = raw.decode("utf-8")
        except Exception:
            txt = raw.decode("gbk", "replace")
        for i, line in enumerate(txt.splitlines(), 1):
            for k, rx in list(HARD.items()) + list(LEGACY.items()):
                if rx.search(line):
                    out[k].append((rel, i, line.strip()[:160]))
    return out


def test_仓内无个人痕():
    got = scan()
    bad = [k for k in HARD if got[k]]
    assert not bad, (u"⛔ 硬 PII 入仓：%s\n" % u"、".join(bad)
                     + u"\n".join(u"  %s:%d  %s" % t for k in bad for t in got[k][:8]))
    for k in LEGACY:
        assert len(got[k]) == BASELINE[k], (
            u"⛔ 旧痕之数 ⛔ 符基（%s）⇒ ⛔ 静增 ／ 静减。\n"
            u"  当：%s\n  基：%s\n  前三：%s\n"
            u"  若为正当 ⇒ 请明书并改基（一处定形）") % (
            k, u"  ".join(u"%s = %d" % (n, len(got[n])) for n in LEGACY), BASELINE,
            u" · ".join(u"%s:%d" % (r, i) for r, i, _t in got[k][:3]))