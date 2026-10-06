# -*- coding: utf-8 -*-
r"""recipe —— pm_1569 之四裁（一改一底 · 本件之树 ＝ 本件所在之仓）。

字面之据（器取 · ⛔ 手抄）：
  一（Python 锁）：包内 wheel 21 件为 cp312-cp312-win_amd64 ⇒ 唯 CPython 3.12 64 位可装；
    旧稿（安装页 §〇.2）书「3.10 或更新」＝ 假言 ⇒ 3.10 ／ 3.11 之机**装必败**（PM 1569 §二）。
  二（模型明书）：净机 GPU 1 GB ⇒ 主线走云端 deepseek-flash ⇒ 本机模型**可选**（PM 1569 §三）。
  三（扫面之界）：旧剔唯（a）精确目录名（e.name in PA_FACES_SKIP）⇒ ptmp1564 漏剔；（b）唯目录名 _auto
    ⇒ 文件面（根 ＝ 工作区 · 递归）95 件中 **32 件**（我方之报告 ／ 派件集之前缀族）漏剔（PM 1569 §四）。
  四（缓存淘汰）：_ASK_CACHE ／ _LINE_CACHE 之存唯 if len < cap（⛔ 淘汰）⇒ 满则**新键永不入**（PM 1569 §五）。
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

core = [
    (u'core/pa/gateway_routes.py · 剔之准随族 ＋ 唯一件数 ＋ LRU', 'core/pa/gateway_routes.py', [
        # ---- A1 剔之准（目录名之通配 ＋ 件名之前缀族）----
        ("sub",
         '                 "_tmp", "_tools", "_seats", "_pm", "_cdp_profile", "_out", "_auto")',
         '                 "_tmp", "_tools", "_seats", "_pm", "_cdp_profile", "_out", "_auto",\n'
         '                 # ⭐ pm_1569 §四.1（剔之准随族 · ⛔ 一刀切）：**测试残渣之形** —— --basetemp 落\n'
         '                 #   根面之新名（ptmp1564 …）曾入检索面（14 件 fixture ⇒ 抖印 ∧ 假有据之口）。\n'
         '                 "ptmp*")\n'
         '# ⭐ pm_1569 §四.2（剔之准 ⛔ 随族）：**我方之报告 ／ 派件集** —— 按**件名之前缀族**剔\n'
         '#   （⛔ 唯目录名 _auto 一据 ⇒ 根面之同族件漏 · 承 L154 ／ L514 之族）。\n'
         '#   量（我一手器取）：文件面 95 件中 **32 件** 属此族（根 31 ＋ reports 1）⇒ 我方之报述入据\n'
         '#   ＝ **假有据**。⚠ 唯「文种前缀」之族 · ⛔ 扩面：凡**知识之件**皆留（英文调研 ／ *纪要 ／\n'
         '#   *报告 ／ 项目经理_角色卡）。\n'
         'PA_FACES_SKIP_PREFIX = ("作废_", "回执_", "作战单_", "发表_", "投递_", "派单_", "请求_",\n'
         '                        "申请_", "讲解_", "对表_", "点选表_", "素材_", "方案_", "设计方案_",\n'
         '                        "外采集_", "外线风险登记_")\n'
         '\n'
         '\n'
         'def _face_skip_name(name):\n'
         '    u"""目录名 ⇒ 剔否（**一处定形** · pm_1569 §四.1）—— 精确名 ∨ 通配形（ptmp*）。\n'
         '\n'
         '    ⚠ 旧形 e.name in PA_FACES_SKIP 唯精确 ⇒ ptmp1564 之流**漏剔**（残渣入面 ⇒ 抖印 ＋ 假有据）。\n'
         '    """\n'
         '    if name in PA_FACES_SKIP:\n'
         '        return True\n'
         '    import fnmatch                     # ⭐ 局部导入（本模块级 ⛔ 增导 · 承 L22 之族）\n'
         '    return any(("*" in _p or "?" in _p) and fnmatch.fnmatch(name, _p) for _p in PA_FACES_SKIP)'),
        # ---- A2 列举之处：用新剔 ＋ 件名之前缀族 ----
        ("sub",
         '                        if e.is_dir(follow_symlinks=False):\n'
         '                            if e.name in PA_FACES_SKIP:\n'
         '                                continue\n'
         '                            stack.append(Path(e.path))\n'
         '                        else:\n'
         '                            found.append(Path(e.path))',
         '                        if e.is_dir(follow_symlinks=False):\n'
         '                            if _face_skip_name(e.name):\n'
         '                                continue\n'
         '                            stack.append(Path(e.path))\n'
         '                        else:\n'
         '                            # ⭐ pm_1569 §四.2：**件名之前缀族**（我方之报告 ／ 派件集）⇒ 剔（⛔ 入面）\n'
         '                            if any(e.name.startswith(_sp) for _sp in PA_FACES_SKIP_PREFIX):\n'
         '                                continue\n'
         '                            found.append(Path(e.path))'),
        # ---- A3d 唯一件数之据（init）----
        ("sub",
         '    searched = 0\n    faces = {}',
         '    searched = 0\n'
         '    _seen = {}   # ⭐ pm_1569 §四.4：径 ⇒ 角色（searched 之**唯一**之据 · 同件二面 ⇒ 只计一次）\n'
         '    faces = {}'),
        # ---- A3a 面级角色之取（上提）----
        ("sub",
         '        n0 = searched\n        _ms = PA_FACES_MIN_SCORE.get(face, min_score)',
         '        n0 = searched\n'
         '        _role = PA_FACE_ROLE.get(face, "knowledge")   # ⭐ 面级角色（一处取 · pm_1569 §四.3）\n'
         '        _ms = PA_FACES_MIN_SCORE.get(face, min_score)'),
        # ---- A3b 去内层之重复取 ----
        ("sub",
         '                _role = PA_FACE_ROLE.get(face, "knowledge")\n'
         '                if cov < _ms:',
         '                if cov < _ms:'),
        # ---- A3c 记唯一之据 ----
        ("sub",
         '            searched += 1\n            for i, ln in enumerate(lines, 1):',
         '            searched += 1\n'
         '            _seen[str(p)] = _role   # ⭐ pm_1569 §四.4：唯一件数之据（同件二面 ⇒ 只计一次）\n'
         '            for i, ln in enumerate(lines, 1):'),
        # ---- A3f 早返（无库根）之键形 ----
        ("sub",
         '        return {"hits": [], "archive_hits": [], "searched": 0, "scope": [],\n'
         '                "threshold": min_score, "faces": {}, "no_kb_root": True,',
         '        return {"hits": [], "archive_hits": [], "searched": 0, "searched_scans": 0,\n'
         '                "searched_roles": {}, "scope": [],\n'
         '                "threshold": min_score, "faces": {}, "no_kb_root": True,'),
        # ---- A3g 早返（无问句）之键形 ----
        ("sub",
         '        return {"hits": [], "searched": 0, "scope": [], "threshold": min_score, "faces": {},\n'
         '                "faces_missing": [], "faces_skipped": {}}',
         '        return {"hits": [], "searched": 0, "searched_scans": 0, "searched_roles": {},\n'
         '                "scope": [], "threshold": min_score, "faces": {},\n'
         '                "faces_missing": [], "faces_skipped": {}}'),
        # ---- A3e 回之键（唯一件数 ＋ 分列 ＋ 原数）----
        ("sub",
         '    return {"hits": hits[:limit], "archive_hits": _arch[:limit], "searched": searched,\n'
         '            "scope": allscope, "threshold": min_score, "faces": faces,',
         '    _roles = {}                      # ⭐ pm_1569 §四.3／§四.4：作据 N ／ 只索引 M（分列 ⇒ ⛔ 静默）\n'
         '    for _r in _seen.values():\n'
         '        _roles[_r] = _roles.get(_r, 0) + 1\n'
         '    return {"hits": hits[:limit], "archive_hits": _arch[:limit], "searched": len(_seen),\n'
         '            "searched_scans": searched, "searched_roles": _roles,\n'
         '            "scope": allscope, "threshold": min_score, "faces": faces,'),
        # ---- A4 回执之键（唯加键）----
        ("sub",
         '        base = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": res["searched"],\n'
         '                "kb_state": "set",',
         '        base = {"question": q, "read_at": _at, "kb_root": str(kb), "searched": res["searched"],\n'
         '                # ⭐ pm_1569 §四.3／§四.4（**唯加键**）：作据 N ／ 只索引 M 分列 —— 面之半\n'
         '                #   （今 dsh 308 件）为**只索引**（role: archive）⇒ ⛔ 静默（承「⛔ 不实之辞入屏」）\n'
         '                "searched_roles": res.get("searched_roles", {}),\n'
         '                "searched_scans": res.get("searched_scans"),\n'
         '                "kb_state": "set",'),
        # ---- A5a LRU 器（一处定形）----
        ("sub",
         '_LLM_PHASE = {"warmed": False}',
         '_LLM_PHASE = {"warmed": False}\n'
         '\n'
         '\n'
         'def _lru_put(cache, key, val, cap):\n'
         '    u"""**LRU 存**（一处定形 · pm_1569 §五）—— 满 ⇒ 逐**最旧**（⛔ 弃新）。\n'
         '\n'
         '    旧病：if len(cache) < cap: cache[k] = v ⇒ 一旦满 ⇒ **新键永不入**（复问恒 miss ∧ 死键只增\n'
         '      不减 ⇒ 「治了等于没治」之潜口 · 承 pm_1549 §一 之旨）。\n'
         '    ⚠ **命中亦须过此**（pop ＋ 重插 ⇒ 提为最新）—— 否则降为 FIFO（⛔ LRU）。\n'
         '    ⚠ dict 保插入序（py3.7+）⇒ 首键 ＝ 最旧 ⇒ ⛔ 须 OrderedDict ／ 新导。\n'
         '    """\n'
         '    if key in cache:\n'
         '        cache.pop(key, None)\n'
         '    elif len(cache) >= cap:\n'
         '        cache.pop(next(iter(cache)), None)\n'
         '    cache[key] = val'),
        # ---- A5b ask 缓存：命中提新 ＋ 满则逐旧 ----
        ("sub",
         '        _hit = _ASK_CACHE.get(_ck)\n'
         '        if _hit is not None:\n'
         '            res, _cached_wall_s = _hit\n'
         '            _from_cache = True\n'
         '        else:\n'
         '            res = pa_kb_search(q, kb, limit=_limit)\n'
         '            _cached_wall_s = 0.0\n'
         '            _from_cache = False\n'
         '            if len(_ASK_CACHE) < _ASK_CACHE_MAX:\n'
         '                _ASK_CACHE[_ck] = (res, round(time.perf_counter() - _tk0, 3))',
         '        _hit = _ASK_CACHE.get(_ck)\n'
         '        if _hit is not None:\n'
         '            res, _cached_wall_s = _hit\n'
         '            _from_cache = True\n'
         '            _lru_put(_ASK_CACHE, _ck, _hit, _ASK_CACHE_MAX)   # ⭐ pm_1569 §五：命中提为最新（真 LRU）\n'
         '        else:\n'
         '            res = pa_kb_search(q, kb, limit=_limit)\n'
         '            _cached_wall_s = 0.0\n'
         '            _from_cache = False\n'
         '            # ⭐ pm_1569 §五（即刻办 · 治）：满 ⇒ **逐最旧**（⛔ 旧形「满则新键永不入」＝ 复问恒 miss）\n'
         '            _lru_put(_ASK_CACHE, _ck, (res, round(time.perf_counter() - _tk0, 3)), _ASK_CACHE_MAX)'),
        # ---- A6b LINE 缓存之上限入常量 ----
        ("sub",
         '_LINE_CACHE = {}',
         '_LINE_CACHE = {}\n'
         '_LINE_CACHE_MAX = 3000   # ⭐ pm_1569 §五：上限入常量（旧为字面 3000 · 无淘汰 ⇒ 满则新件永不入）'),
        # ---- A6 LINE 缓存：命中提新 ＋ 满则逐旧 ----
        ("sub",
         '    v = _LINE_CACHE.get(k)\n'
         '    if v is not None:\n'
         '        return v\n'
         '    try:\n'
         '        txt = p.read_text(encoding="utf-8", errors="replace")\n'
         '    except Exception:\n'
         '        return None\n'
         '    v = txt.splitlines()\n'
         '    if len(_LINE_CACHE) < 3000:\n'
         '        _LINE_CACHE[k] = v\n'
         '    return v',
         '    v = _LINE_CACHE.get(k)\n'
         '    if v is not None:\n'
         '        _lru_put(_LINE_CACHE, k, v, _LINE_CACHE_MAX)   # ⭐ pm_1569 §五：命中提为最新（真 LRU）\n'
         '        return v\n'
         '    try:\n'
         '        txt = p.read_text(encoding="utf-8", errors="replace")\n'
         '    except Exception:\n'
         '        return None\n'
         '    v = txt.splitlines()\n'
         '    # ⭐ pm_1569 §五（同族 · 一并）：满 ⇒ 逐最旧（⛔ 旧形「满则新件永不入」）\n'
         '    _lru_put(_LINE_CACHE, k, v, _LINE_CACHE_MAX)\n'
         '    return v'),
        # ---- A7 面册之版本 +1 ----
        ("sub",
         'PA_FACES_VERSION = "2026-10-06.10"   # ⭐ .10',
         'PA_FACES_VERSION = "2026-10-06.11"   # ⭐ .11（pm_1569 §四）：扫面之剔（PA_FACES_SKIP 增 ptmp* ＋ 新 '
         'PA_FACES_SKIP_PREFIX「报告 ／ 派件」族）＋ searched 改**唯一件数**（＋ searched_roles ／ searched_scans）'
         '⇒ +1（承 L152）｜ ⭐ .10'),
    ]),
]

pre = [
    (u'scripts/win_pa/preflight_start.py · Python 版之判（一处定形 · pm_1569 §二）', 'scripts/win_pa/preflight_start.py', [
        # ---- P1：常量 ＋ 纯函数 ＋ 探针（REQUIRED_DEPS 之后 · probe_deps 之前）----
        ("sub",
         "    ('psutil', 'psutil'), ('tiktoken', 'tiktoken'), ('chromadb', 'chromadb'),\n"
         ")\n"
         "\n"
         "\n"
         "def probe_deps(deps=None):",
         "    ('psutil', 'psutil'), ('tiktoken', 'tiktoken'), ('chromadb', 'chromadb'),\n"
         ")\n"
         "\n"
         "# ⭐ pm_1569 §二（裁一 · 即刻办）：**净机之 Python 锁 CPython 3.12 · 64 位** —— 包内 wheel\n"
         "#   21 件（我一手器取）皆 cp312-cp312-win_amd64 ⇒ 3.10 ／ 3.11 ／ 32 位之机**装必败**；\n"
         "#   旧稿书「3.10 或更新」＝ 假言（⛔ 一名一义）⇒ 前置闸须**检版 fail-loud**（⛔ 静默 ／ ⛔ 半装）。\n"
         "#   ⚠ **一处定形**：本器为**唯一之判** —— 安装器（install_win_pa.preflight_gates）承此出闸，\n"
         "#   ⛔ 另写一遍（二源必漂 · 承 L59-62 之族）。\n"
         "PY_REQUIRED = (3, 12)\n"
         "PY_REQUIRED_BITS = 64\n"
         "\n"
         "\n"
         "def classify_python(impl, ver, bits):\n"
         "    u'''⭐ Python 版之判（**一处定形** · pm_1569 §二）：CPython ∧ ver >= 3.12 ∧ 64 位。\n"
         "\n"
         "    返回 (ok, 人话之实, 修之门)；⛔ 静默 —— 不合则**点名本机之实**（实现 ／ 版 ／ 位数）＋ 门。\n"
         "    '''\n"
         "    _v = tuple(ver or ())[:3]\n"
         "    _impl = (impl or u'').lower()\n"
         "    _bits = int(bits or 0)\n"
         "    _ok = (_impl == u'cpython') and (_v >= PY_REQUIRED) and (_bits == PY_REQUIRED_BITS)\n"
         "    _why = u'%s %s · %d 位' % (impl or u'?', u'.'.join(str(x) for x in _v) or u'?', _bits)\n"
         "    if _ok:\n"
         "        return True, _why, u''\n"
         "    return False, _why, (u'修之门：装 CPython %d.%d · %d 位'\n"
         "                         u'（python.org ⇒ Windows installer (64-bit)）'\n"
         "                         % (PY_REQUIRED[0], PY_REQUIRED[1], PY_REQUIRED_BITS))\n"
         "\n"
         "\n"
         "def probe_python():\n"
         "    u'''本机之 Python 之实（sys.version_info ＋ sys.maxsize ⇒ 64 位）⇒ classify_python 之果。'''\n"
         "    return classify_python(sys.implementation.name, sys.version_info[:3],\n"
         "                           64 if sys.maxsize > 2 ** 32 else 32)\n"
         "\n"
         "\n"
         "def probe_deps(deps=None):"),
        # ---- P2：collect 之首项（Python 版入闸 · rc 随之）----
        ("sub",
         "    items = [(u'依赖（必需 %d 包）' % len(REQUIRED_DEPS), probe_deps())]",
         "    items = [(u'Python 版（须 %d.%d · %d 位）'\n"
         "              % (PY_REQUIRED[0], PY_REQUIRED[1], PY_REQUIRED_BITS), probe_python()),\n"
         "             (u'依赖（必需 %d 包）' % len(REQUIRED_DEPS), probe_deps())]"),
        # ---- P3：selftest 之三 say（正 ＋ 二反）----
        ("sub",
         "    n, t = sum(1 for c in hits if c), len(hits)",
         "    _pk = classify_python(u'cpython', (3, 12, 10), 64)\n"
         "    say(_pk[0] is True and (u'3.12.10' in _pk[1]),\n"
         "        u'正控：CPython 3.12.10 · 64 位 ⇒ 过（⛔ 假红）')\n"
         "    _po = classify_python(u'cpython', (3, 10, 11), 64)\n"
         "    say(_po[0] is False and (u'3.12' in _po[2]) and (u'修之门' in _po[2]),\n"
         "        u'反例：CPython 3.10 · 64 位 ⇒ 判红 ＋ 点名须 3.12 ＋ 修之门')\n"
         "    _pb = classify_python(u'cpython', (3, 12, 10), 32)\n"
         "    say(_pb[0] is False and (u'64' in _pb[2]),\n"
         "        u'反例：CPython 3.12 · **32 位** ⇒ 判红 ＋ 点名须 64 位')\n"
         "    n, t = sum(1 for c in hits if c), len(hits)"),
    ]),
]

inst = [
    (u'scripts/win_pa/install_win_pa.py · Python 闸改承前置器（一处定形 · pm_1569 §二）', 'scripts/win_pa/install_win_pa.py', [
        # ---- I1：PY_MIN 之字面 ⇒ 注（判取前置器 · 一处定形）----
        ("sub",
         'PY_MIN = (3, 10)\n',
         '# ⭐ pm_1569 §二（裁一 · 一处定形）：Python 版之判**唯一出处** ＝ preflight_start.py\n'
         '#   （PY_REQUIRED ／ classify_python ／ probe_python）—— 本器 ⛔ 另写「3.10」之字面（二源必漂）；\n'
         '#   本闸改为**承前置器之出**（见 preflight_gates）。\n'),
        # ---- I2：前置闸之首条（Python 版）改承前置器 ----
        ("sub",
         '    g = []\n'
         '    ok = sys.version_info >= PY_MIN\n'
         '    g.append({"name": u"Python 版", "ok": ok,\n'
         '              "reason": u"%d.%d.%d" % sys.version_info[:3],\n'
         '              "note": u"" if ok else u"修之门：装 Python %d.%d+（python.org）" % PY_MIN})\n',
         '    g = []\n'
         '    # ⭐ pm_1569 §二（裁一）：Python 版之判**唯一出处** ＝ preflight_start（本器 ⛔ 另判）。\n'
         '    _pm = _pf()\n'
         '    _pyr = getattr(_pm, "PY_REQUIRED", (3, 12)) if _pm is not None else (3, 12)\n'
         '    _pnm = u"Python 版（须 %d.%d · 64 位）" % (_pyr[0], _pyr[1])\n'
         '    if _pm is None:\n'
         '        g.append({"name": _pnm, "ok": False,\n'
         '                  "reason": u"前置器不可用（%s）" % _PF_ERR,\n'
         '                  "note": u"修之门：查 scripts/win_pa/preflight_start.py 是否在"})\n'
         '    else:\n'
         '        _pok, _pwhy, _pdoor = _pm.probe_python()\n'
         '        g.append({"name": _pnm, "ok": bool(_pok), "reason": _pwhy, "note": _pdoor or u""})\n'),
        # ---- I3：下段 _pf() 调用改复用 _pm ----
        ("sub",
         '    _m = _pf()\n    if _m is None:',
         '    _m = _pm\n    if _m is None:'),
        # ---- I4：模块首之文档（3.10 ⇒ 3.12 · 一名一义）----
        ("sub",
         '  1. Python 版（>= 3.10 · 承 pyproject requires-python）',
         '  1. Python 版（**CPython 3.12 · 64 位** · 承 pyproject requires-python · 判在 preflight_start）'),
    ]),
]
doc = [
    (u'scripts/win_pa/净机安装一页.md · Python 锁 3.12（64 位）＋ 模型明书二分（pm_1569 §二／§三）',
     'scripts/win_pa/净机安装一页.md', [
        # ---- D1：〇.2 之版（假言 ⇒ 正）----
        ("sub",
         "**2）电脑上已经装了 Python 3.10 或更新版本。**",
         "**2）电脑上必须装 CPython 3.12（64 位）。**"),
        # ---- D2：应该看到（3.10.x ⇒ 3.12.x ＋ 64 位）----
        ("sub",
         "应该看到 `Python 3.10.x` 以上（例：`Python 3.12.10`）。",
         "应该看到 `Python 3.12.x` · 并且是 **64 位**（例：`Python 3.12.10`）。"),
        # ---- D3：未装之支（加「为什么锁 3.12」＋ 下载门 64 位 3.12）----
        ("sub",
         "如果提示「不是内部或外部命令」⇒ 这台电脑还没装 Python。去官网 `python.org` 下 Windows 安装包，\n"
         "安装第一步**务必勾上** `Add python.exe to PATH`，装完关掉窗口重开，再跑一次上面那条命令。",
         "如果提示「不是内部或外部命令」⇒ 这台电脑还没装 Python。去官网 `python.org` 下 Windows 安装包，\n"
         "安装第一步**务必勾上** `Add python.exe to PATH`，装完关掉窗口重开，再跑一次上面那条命令。\n"
         "\n"
         "⭐ **为什么锁死 3.12（64 位）**：这个包里的零件是按 CPython 3.12 · 64 位编好的；\n"
         "3.10 ／ 3.11 ／ 32 位的机器**装不上**。下载页请选 **Windows installer (64-bit)** 的 **3.12** 版\n"
         "（⛔ 不要选 32 位、⛔ 不要选别的版本号）。\n"
         "装好后前置闸会自己核对版本：对不上会**当场用大白话报出来并停下**（⛔ 不会装一半）。"),
        # ---- D4：第三节 答法 B/C 之后（要装的两块：必装 ／ 可选）----
        ("sub",
         "  以后想放笔记，直接往那里放即可，也可以随时按答法 A 另外指定一个。",
         "  以后想放笔记，直接往那里放即可，也可以随时按答法 A 另外指定一个。\n"
         "\n"
         "**⭐ 这个包要装的东西分两块：**\n"
         "- **必装**：Python 依赖（就在包里 `wheel` 那个文件夹里的零件）—— 用 `--offline` 装，**不联网**也能装上。\n"
         "- **可选**：本机模型（要它「不连云端也能答」时才要）—— 须另外下载（**要网**）。装不装都不影响先跑起来。"),
        # ---- D5：§六.4b 之后（密钥有无 ⇒ 面之态）----
        ("sub",
         "   ⛔ 不会因为少了这个文件就启不起来。（要让它连云端 ⇒ 见文末「附」。）",
         "   ⛔ 不会因为少了这个文件就启不起来。（要让它连云端 ⇒ 见文末「附」。）\n"
         "\n"
         "   ⭐ **密钥有没有 ⇒ 页面显示不一样**：没配 ⇒ 那一行照实写「未配」，答问只能走**本机模型**；\n"
         "   配了 ⇒ 写「已配」，答问走**云端**（演示主线 `deepseek-flash`），本机模型可**不装**。\n"
         "   一句话：**没有密钥 ⇒ 本机模型才要装；有密钥 ⇒ 本机模型可选。**"),
    ]),
]

pyproj = [
    (u'pyproject.toml · requires-python ／ classifier ／ ruff ／ mypy（pm_1569 §二 · 一名一义）', 'pyproject.toml', [
        ("sub", 'requires-python = ">=3.10"',
                'requires-python = ">=3.12"   # ⭐ pm_1569 §二：包内 wheel 皆 cp312 ⇒ 锁 CPython 3.12（64 位）'),
        ("sub", '    "Programming Language :: Python :: 3",\n    "License :: OSI Approved :: MIT License",',
                '    "Programming Language :: Python :: 3",\n'
                '    "Programming Language :: Python :: 3.12",\n'
                '    "License :: OSI Approved :: MIT License",'),
        ("sub", 'target-version = ["py310"]', 'target-version = ["py312"]'),
        ("sub", 'target-version = "py310"', 'target-version = "py312"'),
        ("sub", 'python_version = "3.10"', 'python_version = "3.12"'),
    ]),
]
EDITS = {"core": core, "pre": pre, "inst": inst, "doc": doc, "pyproj": pyproj}
ORDER = ["core", "pre", "inst", "doc", "pyproj"]
BASES = []          # 落改后补（--verify 之用）


if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"pm_1569 四裁 · 核（core ／ pre ／ inst ／ doc ／ pyproj）", root=ROOT))
