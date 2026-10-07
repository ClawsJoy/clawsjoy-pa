# -*- coding: utf-8 -*-
"""立面级「路径 ⇒ 写者」登记表 · 门（DS 裁「立」 · 2026-09-28）

登记表：config/v9/vault_write_faces.yaml
判据（机检 · 七条 · 承 T-6 扩面）：
  A 登记表自洽：writers[].module 存在；face/evidence 非空；evidence 一律 file:line（绑件名 · 承 L-DSH-32）。
  B 覆盖性（两向）：扫 core/tools/web/scripts ⇒ 凡「引 vault 真源（vault_root()/is_vault_path()…） ＋ 有写调用」的模块
      B1 全在登记表内（未登记写者 ⇒ 报红）
      B2 登记表内每条也都真实存在（幽灵条目 ⇒ 报红 · 「登记表不许说谎」）
  C 唯一写者：同一 face，CW 侧 writer 唯一（>1 ⇒ 该面须显式 multi_writer_ok）。
  D 对端面显式：peer_faces 非空 ＋ 每项有 excludes/guards/provenance（⛔ 不许沉默）。
  E 例外不许膨胀：exceptions 条数 == exceptions_count（防「沉默新增」）。
  F 反例门（预红 · 纯内存合成）：假写者 ⇒ 必被逮；只引不写 ⇒ ⛔ 不逮（防误报）；登记后 ⇒ 绿。
  B3 data/tmp 侧（T-6 扩面 · DS mid=418 裁「扩面」）：含 vault 字面的落件脚本 ⇒ 分母**两档均冻结** ——
      只走 emit_text 者入 tmp_emit_only；有裸写者入 tmp_scripts（须写明写目标）；裸写目标为 vault 变量者 ⇒
      须在 deviations 逐条登记。任一名单/条数变动 ⇒ 红（⛔ 不许静默漂移）。
      —— 证「判据有分辨力」，⛔ 不是一句声明。
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "config" / "v9" / "vault_write_faces.yaml"
SCAN_DIRS = ("core", "tools", "web", "scripts")

WRITE_CALL = re.compile(r"write_text_lf\(|\.write_text\(|write_bytes\(|shutil\.copy|shutil\.move")
VAULT_REF = re.compile(r"vault_root\(\)|_vault_root\(\)|VAULT_ROOT|self\.vault|PA_VAULT_DIR|is_vault_path\(")


# —— B3（T-6 扩面 · DS mid=418 裁「扩面」）：data/tmp 侧落件脚本面 ——
# 由来：本门扫 core/tools/web/scripts；而我线落件**实走** data/tmp/*.py —— 唯一写出口
#   data/tmp/cw_emit.py 取「调用方给的路径」、自身 ⛔ 无 vault 引用（与
#   core/tools/write_file.py 同族）⇒ 原规则一律逮不到 ⇒ 该面补一条可机检判据。
SCAN_TMP = ("data/tmp",)
VAULT_LITERAL = re.compile(r"Obsidian[\\/]ClawsJoy")
BARE_WRITE = re.compile(r"\.write_text\(|write_bytes\(|(?:io\.)?open\([^)]*['\"](?:w|wb)['\"]|WriteAllText|shutil\.copy|shutil\.move")
USES_EMIT = re.compile(r"emit_text\(")


def tmp_files(root, dirs=SCAN_TMP):
    """data/tmp/*.py（⛔ 不递归 —— 子目录 cdp/ 等另有其面）。"""
    files = {}
    for d in dirs:
        base = root / d
        if not base.is_dir():
            continue
        for p in sorted(base.glob("*.py")):
            files[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8", errors="replace")
    return files


def tmp_candidates(files):
    """分母：含 vault 字面 ∧（裸写 ∨ 走唯一出口 emit_text）的脚本。"""
    out = {}
    for rel, t in files.items():
        if VAULT_LITERAL.search(t):
            out[rel] = {"bare": bool(BARE_WRITE.search(t)), "emit": bool(USES_EMIT.search(t))}
    return {k: v for k, v in out.items() if v["bare"] or v["emit"]}


def vault_vars(src):
    """单层字符串赋值传播（启发式 · ⛔ 非数据流）：rhs ⛔ 不含「(」且含 vault 字面/已知 vault 变量 ⇒ 传播。
    ⚠ 已知边界（⛔ 不假装覆盖）：目标经 os.path.join / Path(...) / 任意调用构造者 ⛔ 逮不到 ——
       该取舍**有意**：`os.path.join(仓内, os.path.basename(P))` ＝ 正解存底写法，
       若对调用透明传播 ⇒ 必生假阳性（F 门「join 构造」一条把该边界钉成断言）。"""
    names = set()
    assigns = re.findall(r"^[ \t]*([A-Za-z_]\w*)[ \t]*=[ \t]*([^\n]*)$", src, re.M)
    changed = True
    while changed:
        changed = False
        for name, rhs in assigns:
            if name in names or "(" in rhs:
                continue
            if VAULT_LITERAL.search(rhs) or any(re.search(r"\b%s\b" % re.escape(n), rhs) for n in names):
                names.add(name)
                changed = True
    return names


def tmp_bare_vault_writes(files):
    """{rel: [行号,…]}：裸写行的目标出现「vault 变量」⇒ 命中（＝绕开唯一出口写 vault）。"""
    out = {}
    for rel, t in files.items():
        if not VAULT_LITERAL.search(t):
            continue
        vs = vault_vars(t)
        if not vs:
            continue
        hits = [i for i, l in enumerate(t.split("\n"), 1)
                if BARE_WRITE.search(l) and any(re.search(r"\b%s\b" % re.escape(n), l) for n in vs)]
        if hits:
            out[rel] = hits
    return out


def _load():
    return yaml.safe_load(REG.read_text(encoding="utf-8"))


def _writers_from_sources(files):
    """纯函数：{相对路径: 源码} ⇒ 候选写者（同件既引 vault 真源、又有写调用）。"""
    out = []
    for rel, t in files.items():
        if VAULT_REF.search(t) and WRITE_CALL.search(t):
            out.append(rel)
    return sorted(out)


def scan_writers(root: Path, dirs=SCAN_DIRS):
    files = {}
    for d in dirs:
        base = root / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            files[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8", errors="replace")
    return _writers_from_sources(files)


def test_A_registry_self_consistent():
    reg = _load()
    assert reg["writers"], "writers 空"
    for w in reg["writers"]:
        assert (ROOT / w["module"]).is_file(), "登记的表件不存在: %s" % w["module"]
        assert w.get("side") == "cw", "side 非 cw: %s" % w["module"]
        for f in w["faces"]:
            assert f["face"].strip(), "空面: %s" % w["module"]
            assert f["evidence"], "面无 evidence: %s / %s" % (w["module"], f["face"])
            for e in f["evidence"]:
                # file:line 须绑件名（承 L-DSH-32）：形如 <path>.py:<n>
                assert re.match(r"^.+\.py:\d+$", e), "evidence 未绑件名/行号: %r" % e
                assert (ROOT / e.rsplit(":", 1)[0]).is_file(), "evidence 指不存在的件: %r" % e


def test_B1_no_unregistered_writer():
    reg = _load()
    declared = {w["module"] for w in reg["writers"]} | {e["module"] for e in reg["exceptions"]}
    unreg = sorted(set(scan_writers(ROOT)) - declared)
    assert not unreg, "逮到未登记的 vault 写者（新增写者必须登记）: %s" % unreg


def test_B2_no_ghost_entry():
    reg = _load()
    declared = {w["module"] for w in reg["writers"] if not w.get("coverage_gap")}
    declared |= {e["module"] for e in reg["exceptions"]}
    ghost = sorted(declared - set(scan_writers(ROOT)))
    assert not ghost, "登记表说谎（条目已不再被规则逮到）: %s" % ghost


def test_C_single_writer_per_face():
    reg = _load()
    by_face = {}
    for w in reg["writers"]:
        if w.get("role") == "exit":
            continue
        for f in w["faces"]:
            by_face.setdefault(f["face"], []).append((w["module"], f))
    for face, lst in by_face.items():
        if len(lst) > 1:
            assert any("multi_writer_ok" in f for _, f in lst), \
                "同面多写者且未显式声明: %s -> %s" % (face, [m for m, _ in lst])


def test_D_peer_faces_declared():
    reg = _load()
    peer = reg.get("peer_faces")
    assert peer, "缺 peer_faces（对端写面 ⛔ 不许沉默）"
    for p in peer:
        for k in ("holder", "face", "excludes", "guards", "provenance", "direction"):
            assert p.get(k), "peer_faces 缺 %s" % k


def test_E_exceptions_not_growing_silently():
    reg = _load()
    assert len(reg["exceptions"]) == reg["exceptions_count"], \
        "例外条数 != 声明数 ⇒ 静默新增"


def test_F_counterexample_registry_has_teeth():
    """反例门（纯内存合成 · ⛔ 不落盘）：假写者必被逮；只引不写 ⛔ 不逮；登记后放行。"""
    rel = "core/svc/fake_writer.py"
    src_write = ('from core.lib.paths import vault_root, write_text_lf' + chr(10) + chr(10) + chr(10)
                 + 'def go():' + chr(10)
                 + '    write_text_lf(vault_root() / "草稿箱" / "x.md", "hi")' + chr(10))
    src_read = 'from core.lib.paths import vault_root' + chr(10)
    src_other = ('def go():' + chr(10) + '    open("data/tmp/x.txt", "w").write("hi")' + chr(10))

    found = _writers_from_sources({rel: src_write})
    assert found == [rel], "假写者未被逮到 ⇒ 判据无分辨力: %s" % found

    # 反例 1：未登记 ⇒ 必红
    assert set(found) - set() == {rel}

    # 反例 2：只引真源不写 / 写但不引真源 ⇒ ⛔ 不逮（防误报）
    assert _writers_from_sources({rel: src_read}) == []
    assert _writers_from_sources({rel: src_other}) == []

    # 登记后 ⇒ 绿
    assert not (set(found) - {rel})

def test_B3_tmp_vault_writers_registered():
    """B3 · data/tmp 侧（扩面 · DS mid=418 裁）：
       ① 唯一出口在场：data/tmp/cw_emit.py::emit_text；
       ② 分母 = 含 vault 字面 ∧（裸写 ∨ 走 emit_text）的 data/tmp/*.py；
       ③ 「只走 emit_text」档 ⇒ 合规，但**名单与条数冻结**（tmp_emit_only ⇒ 新入者必红 · ⛔ 不许静默漂移）；
          其余（有裸写）⇒ 须在 tmp_scripts 逐条登记（写目标须写明）；
       ④ 裸写目标为 vault 变量者 ⇒ 须在 deviations 逐条登记（已知偏差 · ⛔ 未删 · 待处置）；
       ⑤ 四处都不许说谎：条目已不再命中 ⇒ 红；条数 != 声明数 ⇒ 红（防静默增删）。
       ⭐ 2026-10-08（pm_1837 §一 · 采 ⒝ · 技术总监 f202f89 一手）：`data/tmp` 之擦写面**已清**
          ⇒ 表立 `tmp_history_only: true` ⇒ 本齿走**「已清」之支**（⛔ 静默兜底 · ⛔ 空混缺）：
          ⒜ 史档**自洽**（名与数 · 仍是 fail-loud）⒝ `cw_emit.py` **照实不在**（正面断言 · ⛔ 非跳）
          ⒞ **盘之活牙仍在**（现面若再落触碰 vault 之脚本 ⇒ 必红 ⇒ ⛔ 因史档而失牙）。
    """
    reg = _load()
    files = tmp_files(ROOT)
    cand = tmp_candidates(files)
    if reg.get("tmp_history_only"):
        # ⭐ 「已清」之支（pm_1837 §一）：史档自洽 ∧ 照实其不在 ∧ 盘之活牙仍在
        for _k, _c in (("tmp_emit_only", "tmp_emit_only_count"),
                       ("tmp_scripts", "tmp_scripts_count"),
                       ("deviations", "deviations_count")):
            assert len({x["module"] for x in reg.get(_k, [])}) == reg.get(_c), \
                "史档 %s 条数 != 声明数 ⇒ 静默增删（已清亦 ⛔ 说谎）" % _k
        assert not (ROOT / "data/tmp/cw_emit.py").exists(), \
            "史档书「已清」而 cw_emit.py 在场 ⇒ 二处互斥（pm_1837 §一）"
        assert not cand, \
            "data/tmp 现面有触碰 vault 之脚本而史档已冻结 ⇒ 须立新档登记: %s" % sorted(cand)
        return
    assert "def emit_text(" in files.get("data/tmp/cw_emit.py", ""), "唯一出口 data/tmp/cw_emit.py::emit_text 不见了"

    emit_only = {rel for rel, v in cand.items() if v["emit"] and not v["bare"]}
    eo_reg = {x["module"] for x in reg.get("tmp_emit_only", [])}
    assert eo_reg == emit_only, "emit_only 档与登记不符（增删须同批登记）: 新增 %s / 幽灵 %s" % (sorted(emit_only - eo_reg), sorted(eo_reg - emit_only))
    assert len(eo_reg) == reg.get("tmp_emit_only_count"), "tmp_emit_only 条数 != 声明数 ⇒ 静默增删"
    tsrc = {x["module"] for x in reg.get("tmp_scripts", [])}
    bad = sorted(set(cand) - emit_only - tsrc)
    assert not bad, "data/tmp 内未走唯一出口且未登记的 vault 触碰脚本: %s" % bad
    ghost = sorted(tsrc - set(cand))
    assert not ghost, "tmp_scripts 说谎（条目已不再命中）: %s" % ghost
    assert len(tsrc) == reg.get("tmp_scripts_count"), "tmp_scripts 条数 != 声明数 ⇒ 静默增删"

    hits = tmp_bare_vault_writes(files)
    dev = {x["module"] for x in reg.get("deviations", [])}
    fresh = sorted(set(hits) - dev)
    assert not fresh, "裸写落 vault（绕开 emit_text）且未登记为偏差: %s ⇒ %s" % (fresh, {k: hits[k] for k in fresh})
    dghost = sorted(dev - set(hits))
    assert not dghost, "deviations 说谎（条目已不再命中）: %s" % dghost
    assert len(dev) == reg.get("deviations_count"), "deviations 条数 != 声明数 ⇒ 静默增删"


def test_B3_counterexample_rule_has_teeth():
    """B3 反例门（预红 · 纯内存合成 · ⛔ 不落盘）：vault 变量 ＋ 裸写 ⇒ 必逮；
       本树变量 ⇒ ⛔ 不逮；join 构造 ⇒ ⛔ 不逮（已知边界 · 有意取舍）；只引不写 ⇒ ⛔ 不逮（防误报）。"""
    nl = chr(10)
    pc = r'P = r"D:\Obsidian\ClawsJoy\ClawsJoy\codex\x.md"' + nl
    offender = pc + 'BAK = P + ".before_x"' + nl + 'open(BAK, "wb").write(b"")' + nl
    assert tmp_bare_vault_writes({"data/tmp/_fake_offender.py": offender}) == {"data/tmp/_fake_offender.py": [3]}
    tree = r'B = r"D:\clawsjoy_v9\.rollback_codex\x"' + nl + 'open(B, "wb").write(b"")' + nl
    assert tmp_bare_vault_writes({"data/tmp/_fake_tree.py": tree}) == {}
    join = pc + "import os" + nl + r'bak = os.path.join(r"D:\clawsjoy_v9\.rollback_codex", os.path.basename(P))' + nl + 'open(bak, "wb").write(b"")' + nl
    assert tmp_bare_vault_writes({"data/tmp/_fake_join.py": join}) == {}
    lead = pc + "open(P, encoding='utf-8').read()" + nl
    assert tmp_bare_vault_writes({"data/tmp/_fake_read.py": lead}) == {}
