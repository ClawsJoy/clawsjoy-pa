# -*- coding: utf-8 -*-
"""PA 路由 · 公共件（②v1 拆件）。

`bp` 唯此一处建；10 个 `pa_routes_*` 簇皆 `from core.pa.pa_routes_common import bp`。
endpoint 名仍 `pa_routes.<func>`（Blueprint 名不变 ⇒ 前端契约不变）。
⭐ `register_pa_routes` 亦在本件（唯挂载一处）⇒ 依赖单向：簇 → 本件，⛔ 环。
"""

import logging
from flask import Blueprint, jsonify
from core.lib.paths import org_enabled, vault_root, ws_root

logger = logging.getLogger(__name__)

bp = Blueprint("pa_routes", __name__)


def ok(payload=None, **kw):
    doc = {"ok": True}
    if payload is not None:
        doc.update(payload)
    doc.update(kw)
    return jsonify(doc)


def err(msg, code=400):
    return jsonify({"ok": False, "error": str(msg)[:300]}), code


def _pa_brain_of_app():
    """注册时注入之对话脑（per-app · 承 `register_pa_routes(app, brain=...)` 之原义）。"""
    from flask import current_app
    return getattr(current_app, "_pa_brain", None)


from core.pa import owner_guard as _owner_guard
_owner_guard.install(bp)


import logging


import os


import time


from pathlib import Path


from flask import Blueprint, jsonify, request


logger = logging.getLogger(__name__)


from core.pa.pa_core import PaCore


from core.pa import _proc as _proc   # ⭐ 窗隐唯一出口（PM 2026-10-05 令 · ⛔ 各写 creationflags）


_PA_ROUTE_PREFIX = "/v9/pa/"


_CAP_BRIEF_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")


def build_capability_brief(url_map):
    u"""由**路由表**（`app.url_map`）生成能力面清单（⛔ 手写 · pm_1802 §一.1）。

    ⚠ 须于 `app.register_blueprint` **之后**取：注册前蓝图之路由尚在 `deferred_functions`
      之列，⛔ 现于 `url_map` 之 `Rule` ⇒ 早取 ＝ **空表**（假绿）。
    """
    rows = []
    for _r in url_map.iter_rules():
        _rule = str(getattr(_r, "rule", "") or "")
        if not _rule.startswith(_PA_ROUTE_PREFIX):
            continue
        _ms = sorted(_m for _m in (getattr(_r, "methods", None) or set())
                     if _m in _CAP_BRIEF_METHODS)
        rows.append((_rule, u"/".join(_ms) or u"-"))
    rows.sort()
    _head = (u"【本 PA 的真实能力面（**由路由表自动生成** · pm_1802 §一.1）】\n"
             u"· 接口共 %d 条（前缀 `%s`）—— **照抄**，⛔ 不许加清单外的东西。\n"
             u"· ⚠ 此清单答的是「本 PA **有**什么」（供你**如实作答**之料）；\n"
             u"  **⛔ 不等于你此刻能调它** —— 能不能动手**看轴**（见系统提示之「两轴分书」）。\n"
             % (len(rows), _PA_ROUTE_PREFIX))
    return _head + u"".join(u"  [%s] %s\n" % (_m, _p) for _p, _m in rows)


PA_CAPABILITY_BRIEF = u""


def _set_capability_brief(app):
    u"""挂载即定形：由**本次挂载后**之路由表现生 ⇒ 新路由一上，清单自跟（pm_1802 §一.1）。"""
    global PA_CAPABILITY_BRIEF
    try:
        PA_CAPABILITY_BRIEF = build_capability_brief(app.url_map)
    except Exception as _e:
        print("[PA] ⚠ 能力面清单未生成：%s: %s" % (type(_e).__name__, _e), flush=True)
    return PA_CAPABILITY_BRIEF


_PA_APP = None


def _set_pa_app(app):
    u"""挂载即定形（承 pm_1859 §一.4）：真 app 一挂 ⇒ 只读面之工具**即**可进程内真调。"""
    global _PA_APP
    _PA_APP = app
    return _PA_APP


def _lru_put(cache, key, val, cap):
    u"""**LRU 存**（一处定形 · pm_1569 §五）—— 满 ⇒ 逐**最旧**（⛔ 弃新）。

    旧病：if len(cache) < cap: cache[k] = v ⇒ 一旦满 ⇒ **新键永不入**（复问恒 miss ∧ 死键只增
      不减 ⇒ 「治了等于没治」之潜口 · 承 pm_1549 §一 之旨）。
    ⚠ **命中亦须过此**（pop ＋ 重插 ⇒ 提为最新）—— 否则降为 FIFO（⛔ LRU）。
    ⚠ dict 保插入序（py3.7+）⇒ 首键 ＝ 最旧 ⇒ ⛔ 须 OrderedDict ／ 新导。
    """
    if key in cache:
        cache.pop(key, None)
    elif len(cache) >= cap:
        cache.pop(next(iter(cache)), None)
    cache[key] = val


def _pa_read_at():
    u"""**取数之刻**（一处定形 · pm_1478 §二）—— 后端算成本轮回执之刻。

    ⚠ 义（⛔ 混）：**取数之刻**（就地时钟 · 本回执诸数之取时）
      —— ⛔ **落盘之刻**（那属 `persisted.*` 之域 · 另一端）。
    ① 名就旧：与 `/v9/pa/ask` 之 `read_at` **同名同义**（前端 `read_at || at` 之首选）。
    ② 格式就旧：`%Y-%m-%d %H:%M:%S`（承三处旧行 · 唯此一处出）。
    """
    from datetime import datetime as _dt
    return _dt.now().strftime("%Y-%m-%d %H:%M:%S")


def _data_dir():
    return os.getenv("PA_DATA_DIR", "data/v9/pa")


def _loopback(req):
    """唯本机（环回）—— 另端（LAN / 他机）⛔ 达（承 pm_1613 令四 · 端之鉴权）。

    ⚠ 服务绑 0.0.0.0 ⇒ LAN 可达本端 ⇒ 故须显判（⛔ 凭「无鉴权」而放行）。
    """
    a = str(getattr(req, "remote_addr", "") or "").strip()
    if a.startswith("127."):
        return True
    if a.startswith("::ffff:") and a[7:].startswith("127."):
        return True
    return a in ("::1", "localhost")


def _owner_corrupt_json(_oc):
    u"""坏身份档之报（**一处定形** · 409）：⛔ 回落空身份 ／ ⛔ 另铸（承 pm_1858 §四.1）。"""
    return jsonify({"ok": False, "error": "owner_state_corrupt",
                    "message": str(_oc), "path": getattr(_oc, "path", "")}), 409


def _core(user_id=None):
    """单 principal 先跑通(多租户后续: data/v9/pa/users/<uid>)。"""
    return PaCore(data_dir=_data_dir())


PA_KB_ASK_SCOPES = ("收件箱", "知识库")


PA_ASK_MIN_SCORE = 0.42  # ⭐ 2026-10-04：0.34 → 0.42（扩面后弱命中 0.375 之假有据之修）


def _rel_under(base, *parts):
    """`base` 之下的相对径（⛔ 字面绝对径 · 承 pm_1409 §二.3）—— 缺 `base` ⇒ `None`。"""
    return os.path.join(base, *parts) if base else None


def _pa_faces_tables():
    u"""（PA_FACES, PA_FACES_GATE）—— **惰算**（依**当刻**之 `ws_root()` ／ `vault_root()`）。"""
    _FACE_WS = ws_root()
    _FACE_VR = vault_root()
    _PA_FACES_ORG = (
        ("文件", (_FACE_WS,), ("*.md", "*.txt")),
        # ⭐ 台账面＝**只取台账本身**（⛔ 不收整个 `_auto\deliver`：那含我的报告集）
        ("台账", (_rel_under(_FACE_WS, "_auto", "deliver"),),
         ("老板令台账_v1.md",)),  # ⛔ 收 `投递台账.csv`／`债单_*.md`（真身皆在信通 · 该根下⛔存在 ⇒ 空转）
        # ⭐ PM 2026-10-05（老板批「并入技总写域」之同批 · 承 技总 972 §五）：新面 `平台台账`
        #   真源 ＝ `…\内容工坊\04_平台台账`（`46` 项 · ⛔ 存底类：`*.md` 天然排除 `.before_*` ／ `.bak_*` ／ `.sha256`）
        #   ＋ `平台注册表.md`（生成物 · 源头 `08_工具\平台\*\plugin.json`）⇒ `role: knowledge`（⛔ archive ⇒ 可作据）
        ("平台台账", (_rel_under(_FACE_VR, "内容工坊/04_平台台账"),), ("*.md",)),
        ("台账·信通", (_rel_under(_FACE_VR, "内容工坊/02_协作/信通"),),
         ("投递台账.csv",)),  # ⛔ 收 `债单_*.md`（内含测试问题引用 ⇒ 污染）
        # ⭐ 2026-10-05（PM b136893 令「menghua 进 PA 试用」§四「先接素材面」· 老板批）：新面 `梦中月水中花`
        #   真源 ＝ `11_实验室/记忆` —— 皆**插件产出**（`梦_*.md` 做梦读数 ／ `唤醒_*.md` 唤醒(体检)读数）· ⛔ 非我测。
        #   ⇒ `role: archive`（**我们之报述** 之族 ⇒ ⛔ 作据 · 仍可检索回指 · 承 PM 846 §二）。
        #   ⚠ 根 ＝ **既有**面：`11_实验室/记忆/` 系 PM `955`／`956` 准我之**跨面子面**（父面属主 ＝ 工作流实验室席 `e621c26`）
        #     ⇒ 只读 · ⛔ 写 · glob 特指 ⇒ 天然排除 `.唤醒水位` 等点件与 `待做梦_*` 备料。
        ("梦中月水中花", (_rel_under(_FACE_VR, "内容工坊/11_实验室/记忆"),),
         ("梦_*.md", "唤醒_*.md")),
        # ⭐ 2026-10-05（PM b136893 令「M1 接线收口：加两个素材面」§二 ⒜ · 老板 20:0x 之纠后）：
        #   新面 `文件·产出` —— **文本产出**（`10_产出` ／ `dsh` ／ `_交付`）⇒ `role: archive`
        #   （**只索引 · ⛔ 作据** · 承 PM 846 §二）。
        #   ⚠ **名 ⛔ 取 `文件`** —— 由：`PA_FACE_ROLE` ／ `PA_FACES_MIN_ROW` 皆**按名取** ⇒ 与本表**既有**之
        #     `文件`（`<workspace>` · `knowledge`）**撞名** ⇒ 一面二义：改 `archive` ⇒ 撤 `q07` 之
        #     真据行（`项目经理_角色卡.md:71` · 承 L152 之注）；改 `knowledge` ⇒ 产出（我们之报述）入据
        #     ＝ 循环取证。⇒ 故取 `文件·产出`（承本表 `台账·信通` 之「大类·子类」之形）—— **候裁名**（承 1048 §三）。
        #   ⚠ **图产出 ⛔ 入本表** —— 本表之列 ⛔ 能表「目录级聚合」（PM §二 ⒝ 之裁）；且 `_cached_lines`
        #     读图 ⇒ `None` ⇒ 该面恒 `0` 件 ＝ **假绿之面** ⇒ 图面走 `PA_SRC_FACES` ＋ `GET /v9/pa/source_faces`。
        ("文件·产出", tuple(x for x in (_rel_under(_FACE_VR, "内容工坊/10_产出"),
                                      _rel_under(_FACE_VR, "dsh"), _rel_under(_FACE_WS, "_交付")) if x), ("*.md",)),
        # ⭐ 2026-10-05（PM 22:34 §二 裁「闸面余 9 件」· 逐件列判 ⇒ **唯此一件入闸**）：
        #   判据（PM 定）：**本机有据 ∧ ⛔ 无 GET 面 ⇒ 入闸**；有 GET 面者 ⇒ 归「另路」。
        #   逐件判：余 8 件皆有 GET /v9/pa/*（ledger ／ deliver/mail ／ caliber ／ roster ／
        #     seats ／ roster(probe 二键) ／ resume ／ threads）⇒ ⛔ 入闸；唯 deadfile_ledger.json
        #     **无任何路由**（rg dead core/pa/gateway_routes.py ⇒ 0 命中）⇒ **入闸**。
        #   ⚠ 根取 _data_dir()（与 DecisionStore 一处口径 · ⛔ 另立绝对径 ⇒ 免「两真源」）。
        ("死件账", (_data_dir(),), ("deadfile_ledger.json",)),
    )
    # ⭐ 2026-10-06（pm_1409 §二.3）：`PA_ORG_FACES` 门（**功能级** · 默认关 ⇒ 其径逻辑 ⛔ 执行）。
    #   本表七面中唯 `死件账` 为**产品面**（本机 `data/` 之账 · 与组织物无关）；余六面
    #   （文件 ／ 台账 ／ 平台台账 ／ 台账·信通 ／ 梦中月水中花 ／ 文件·产出）皆**组织物**
    #   （我方工作区 ／ 台账 ／ 信通 ／ 实验室 ／ 产出）⇒ 净机 ⛔ 得读 ⇒ 门关即 ⛔ 入表。
    #   ⚠ **关**时之面集 ＝ `收件箱` ／ `知识库`（`PA_KB_ASK_SCOPES` · vault 相对 · 用户自选库）
    #     ＋ `死件账`（本表产品面）。⚠ **面之数之变须报**（⛔ 静默减面）：响应附 `faces_gate`。
    # ⚠ 缺基（`_FACE_WS` ／ `_FACE_VR` ＝ `None`）⇒ 该面 ⛔ 入表（⛔ 空径 ⇒ 误扫 cwd · 承 pm_1409 §二.3）。
    # ⚠ 空根（全缺基）亦 ⛔ 入表 —— `all(())` 恒真 ⇒ 须并判 `ff[1]` 非空
    #   （否则该面以「0 件」上屏 ＝ **假绿之面** · 承本表 L323 之注）。
    _PA_FACES_ORG = tuple(ff for ff in _PA_FACES_ORG if ff[1] and all(x for x in ff[1]))
    _PA_FACES_ORG_ONLY = tuple(x for x in _PA_FACES_ORG if x[0] != "死件账")
    _PA_FACES_PRODUCT = tuple(x for x in _PA_FACES_ORG if x[0] == "死件账")
    PA_FACES = (_PA_FACES_ORG_ONLY + _PA_FACES_PRODUCT) if org_enabled() else _PA_FACES_PRODUCT
    PA_FACES_GATE = "org" if org_enabled() else "product"
    return PA_FACES, PA_FACES_GATE


PA_FACES_SKIP = (".git", "node_modules", "__pycache__", ".pytest_cache", "store-assets",
                 "_tmp", "_tools", "_seats", "_pm", "_cdp_profile", "_out", "_auto",
                 # ⭐ pm_1569 §四.1（剔之准随族 · ⛔ 一刀切）：**测试残渣之形** —— --basetemp 落
                 #   根面之新名（ptmp1564 …）曾入检索面（14 件 fixture ⇒ 抖印 ∧ 假有据之口）。
                 "ptmp*")


PA_FACES_SKIP_PREFIX = ("作废_", "回执_", "作战单_", "发表_", "投递_", "派单_", "请求_",
                        "申请_", "讲解_", "对表_", "点选表_", "素材_", "方案_", "设计方案_",
                        "外采集_", "外线风险登记_")


def _face_skip_name(name):
    u"""目录名 ⇒ 剔否（**一处定形** · pm_1569 §四.1）—— 精确名 ∨ 通配形（ptmp*）。

    ⚠ 旧形 e.name in PA_FACES_SKIP 唯精确 ⇒ ptmp1564 之流**漏剔**（残渣入面 ⇒ 抖印 ＋ 假有据）。
    """
    if name in PA_FACES_SKIP:
        return True
    import fnmatch                     # ⭐ 局部导入（本模块级 ⛔ 增导 · 承 L22 之族）
    return any(("*" in _p or "?" in _p) and fnmatch.fnmatch(name, _p) for _p in PA_FACES_SKIP)


PA_FACES_MIN_SCORE = {"文件": 0.5, "台账": 0.5, "台账·信通": 0.5}


PA_FACES_MIN_ROW = {"平台台账": 0.05, "收件箱": 0.05, "文件": 0.05,
                    # ⭐ 2026-10-05（PM 22:34 §二）：死件账 —— 其行为**结构化 JSON**（径 ／ 键），
                    #   ⛔ 散文 ⇒ 行侧覆盖天然低 ⇒ 默认 0.42 会**恒杀**（实测：默认 0 中）。
                    #   ⚠ **唯降行阈 · ⛔ 动问阈**（降问阈 ＝ 扩假有据面 ⇒ 与「扩面之阈值独立抬高」相反）；
                    #   实测：行阈 0.05 ⇒ 应拒之问（老板叫什么 …）**死件账 0 中**（⛔ 假有据）。
                    "死件账": 0.05}


PA_CORPUS_NAME_BIGRAMS = ("内容工坊",)


PA_FACE_ROLE = {"收件箱": "knowledge", "知识库": "knowledge",
                "文件": "knowledge", "台账": "archive", "台账·信通": "archive",
                "平台台账": "knowledge", "梦中月水中花": "archive",
                # ⭐ 2026-10-05：文本产出面（PM「M1 接线收口」§二 ⒜）⇒ archive（只索引 · ⛔ 作据）
                "文件·产出": "archive",
                # ⭐ 2026-10-05（PM 22:34 §二）：死件账 ⇒ knowledge —— 由：其内容 ＝
                #   **对盘之事实读数**（死件 ／ 被拖死之件 ／ 登记之谎 ⇒ 逐条带径与由），
                #   ⛔ 「我们之报述」（⚠ 承 846 §二：archive 之义 ＝ 报述含问句样本 ⇒ 循环取证）；
                #   ⚠ 此为**我之判** ⇒ 候 PM 核（改 archive 仅一行 · ⛔ 动骨架）。
                "死件账": "knowledge"}


PA_FACES_VERSION = "2026-10-06.11"   # ⭐ .11（pm_1569 §四）：扫面之剔（PA_FACES_SKIP 增 ptmp* ＋ 新 PA_FACES_SKIP_PREFIX「报告 ／ 派件」族）＋ searched 改**唯一件数**（＋ searched_roles ／ searched_scans）⇒ +1（承 L152）｜ ⭐ .10：`PA_ORG_FACES` 门（关 ⇒ 唯产品面 `死件账`）⇒ +1（承 L152）｜ ⭐ .9：元问路（context_missing）之答话 ＋ 死件路「账不可读」之界（PM 1183 §五.1 ／ §八 · 我 1057）⇒ 仍 +1｜⭐ .8：死件账之**直读路**（PM 22:34 §三① 准 · 条件⒟）⇒ 仍 +1（承 L152）｜⭐ .7：面表＋角色表增「死件账」（PM 22:34 §二 裁）｜⭐ 2026-10-05：面表＋角色表增 `文件·产出`（PM「M1 接线收口」§二 ⒜）⇒ 皆 +1


PA_SELFTEST_MARKS = ("（自测）", "端到端自检", "探针 OK", "E2E 自检", "selftest")


PA_ASK_DECISION_ID_RE = r"d\d{13}"


PA_ASK_DECISION_KW = ("决策记录", "决策日志", "决策账", "拍板记录", "decision log", "decision_log")


PA_ASK_DEADFILE_KW = ("死件", "缺件", "登记之谎", "deadfile", "dead_file", "缺源")


PA_ASK_DEADFILE_LEDGER = "deadfile_ledger.json"


PA_FACES_MAX_BYTES = {"文件": 2 * 1024 * 1024, "台账": 16 * 1024 * 1024, "台账·信通": 16 * 1024 * 1024}


PA_FACES_DEFAULT_MAX_BYTES = 2 * 1024 * 1024


PA_FACES_MAX_FILES = 4000


def _bigrams(t):
    s = "".join(ch for ch in str(t or "") if ch.strip())
    if not s:
        return set()
    return set(s[i:i + 2] for i in range(len(s) - 1)) if len(s) > 1 else set((s,))


def _face_root(kb_root, spec):
    """面之根：常量绝对径 ／ "@vault:" 前缀（vault 内相对）。⛔ 用户输入。"""
    spec = str(spec)
    if spec.startswith("@vault:"):
        return Path(kb_root) / spec[len("@vault:"):]
    return Path(spec)


_LINE_CACHE = {}


_LINE_CACHE_MAX = 3000   # ⭐ pm_1569 §五：上限入常量（旧为字面 3000 · 无淘汰 ⇒ 满则新件永不入）


def _cached_lines(p):
    """按 (path, mtime_ns, size) 缓存行表 ⇒ 复问不重读盘（承「好用」之要求）。

    ⚠ pm_1549 §一.2：粒度**从 ns**（旧 `int(st.st_mtime)` ＝ 秒）—— 同秒内同长之改写
      ⇒ 行表读旧（与「印」不同轴 ⇒ 印变而读旧 ＝ **假新鲜**）。"""
    try:
        st = p.stat()
        k = (str(p), st.st_mtime_ns, st.st_size)   # ⭐ pm_1549 §一.2：**ns**（旧＝秒 ⇒ 同秒同长之改写 ⇒ 读旧）
    except Exception:
        return None
    v = _LINE_CACHE.get(k)
    if v is not None:
        _lru_put(_LINE_CACHE, k, v, _LINE_CACHE_MAX)   # ⭐ pm_1569 §五：命中提为最新（真 LRU）
        return v
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    v = txt.splitlines()
    # ⭐ pm_1569 §五（同族 · 一并）：满 ⇒ 逐最旧（⛔ 旧形「满则新件永不入」）
    _lru_put(_LINE_CACHE, k, v, _LINE_CACHE_MAX)
    return v


def _nows(t):
    u"""去空白 —— 与 `_bigrams()` 之剔法**同源**（`ch.strip()` 为假者皆白）。

    ⚠ 本模块级 ⛔ 增导 `re` ⇒ **局部导入**（承 L22 之族：新导须明其由 · `re` 自缓存所编之式）。
    """
    import re
    return re.sub(r"\s+", "", t)


def _inter_fast(qg, ln, all2):
    u"""⭐ 降本条 ⓑ（先判后算）：**⛔ 建行侧 bigram 集** 即得 `inter`（⛔ 返 `None` 时由调用方回落旧法）。

    `inter` ＝ 问侧 bigram 中**出现于**该行者之数 —— 于「问侧诸元皆 2 字 ∧ 行去白后 ≥ 2 字」时，
    行侧之 bigram 集 ≡ 行**去白后**之 2-gram 集（⚠ 去白会**跨空白**造 2-gram ⇒ 故先 `_nows`）：
    2 字之 `b` ⇒ `b in s` ⟺ `b ∈ _bigrams(ln)`。
    ⛔ 适用条件不成立（问侧含 1 字元 ∨ 去白后 < 2 字）⇒ 返 `None` ⇒ **回落旧法**（⛔ 猜 · 承 L124）。
    """
    if not all2:
        return None
    s = _nows(ln)
    if len(s) < 2:
        return None
    return sum(1 for b in qg if b in s)


def _face_files(root, globs):
    u"""面内文件（⛔ 穿越 · 跳过工程目录 · 有上限）—— 只读列举。

    ⭐ 2026-10-05（降本条 ⓐ · 先判后算）：**剪树列举** —— 入目录前即剔 `PA_FACES_SKIP`。
    由：旧法走**全树**（含 `_tmp` ／ `_tools` ／ `.git` …）再逐件按相对径剔 ⇒ 列举即 **0.865 s**
    （实测 · 六面 141 件之面）⇒ 剪树 ⇒ **0.015 s**（同机同刻）。
    ⭐ 件集与**序** ⛔ 变：仍**逐通配**各 `sorted`（＝旧法之逐 `pat`）⇒ 实测六面**逐件逐序同**。
    ⚠ 界：⛔ 随目录符号链接（旧法 `rglob` 亦不随 · 本树无此物 ⇒ 六面实测同）。
    """
    out = []
    try:
        root = Path(root)
        if not root.is_dir():
            return out
    except Exception:
        return out
    import fnmatch                      # ⭐ 局部导入（本模块级 ⛔ 增导 · 承 L22 之族）
    found = []
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if _face_skip_name(e.name):
                                continue
                            stack.append(Path(e.path))
                        else:
                            # ⭐ pm_1569 §四.2：**件名之前缀族**（我方之报告 ／ 派件集）⇒ 剔（⛔ 入面）
                            if any(e.name.startswith(_sp) for _sp in PA_FACES_SKIP_PREFIX):
                                continue
                            found.append(Path(e.path))
                    except OSError:
                        continue
        except OSError:
            continue
    for pat in globs:
        for p in sorted(x for x in found if fnmatch.fnmatch(x.name, pat)):
            out.append(p)
            if len(out) >= PA_FACES_MAX_FILES:
                return out
    return out


_UI_REPO = Path(__file__).resolve().parents[2]


def _is_under_path(base, p):
    u"""`p` ⛔ 在 `base` 之下（皆绝对化 ＋ 大小写归一；⛔ 前缀误配 `kb` ⟷ `kb2`）。"""
    try:
        _b = os.path.normcase(os.path.abspath(str(base)))
        _p = os.path.normcase(os.path.abspath(str(p)))
    except Exception:
        return False
    if _p == _b:
        return True
    return _p.startswith(_b + os.sep)


def pa_vault_face_files(root):
    u"""本库根之 **PA 检索面**：⇒ `(件数, 命中面名…)`（判「态」用 · **一处定形** · pm_1517 §一）。

    ＝ `PA_KB_ASK_SCOPES`（库根相对 · `*.md`）＋ `PA_FACES` 中**根在本库根之下**者（各用其通配）。
    ⚠ 只读列举（`_face_files` ⇒ 剪树剔 `PA_FACES_SKIP`）；⚠ **⛔ 他根之面**（见上注）。
    """
    _r = Path(root)
    _n = 0
    _names = []
    for _rel in PA_KB_ASK_SCOPES:
        _c = len(_face_files(_r / _rel, ("*.md",)))
        _n += _c
        if _c:
            _names.append(_rel)
    for _name, _roots, _globs in pa_faces():
        _c = 0
        for _spec in _roots:
            _rp = _face_root(_r, _spec)
            if not _is_under_path(_r, _rp):
                continue
            _c += len(_face_files(_rp, _globs))
        _n += _c
        if _c:
            _names.append(_name)
    return _n, tuple(_names)


def pa_vault_state_code(root=None):
    u"""库根之「**态**」机器码（**一处定形** · pm_1517 §一 之裁 ⇒ 取拟一）。

    值域（一名一义 · 承 `pm_1503 §一`）：
      ``no_root`` —— 库根 ⛔ 得（四序皆无）
      ``empty``   —— 库根在 ∧ **本库根之 PA 检索面诸面皆无件**
      ``ok``      —— 有件
    ⚠ 其源**唯** `pa_vault_face_files()`（⛔ 另立判据 · ⛔ 内核约定六面 —— 二物别 · 报其读者）。
    ⚠ 传 ``root=None``（∨ 空）⇒ 自 `vault_root()`（四序 · 一处定形）。
    """
    from core.lib.note_kernel import (STATE_CODE_EMPTY, STATE_CODE_NO_ROOT,
                                      STATE_CODE_OK)
    _r = Path(root) if str(root or "").strip() else vault_root()
    if _r is None:
        return STATE_CODE_NO_ROOT, 0, ()
    _n, _names = pa_vault_face_files(_r)
    return (STATE_CODE_OK if _n else STATE_CODE_EMPTY), _n, _names


PA_VAULT_ENV_KEY = "PA_VAULT_DIR"


PA_VAULT_ENV_NOTE = (u"本机之库根由环境变量 PA_VAULT_DIR 指定 ⇒ 你所选须清该变量方生效")


def vault_env_override():
    u"""(env_override, note) —— 一处定形（⛔ 二处各判 · 承 pm_1525 §一）。"""
    _on = bool((os.environ.get(PA_VAULT_ENV_KEY) or "").strip())
    return _on, (PA_VAULT_ENV_NOTE if _on else "")


def _last_user_before(pa, question, session_id=None):
    """取本会话**真序列**之「上一句 user 原文」（⛔ 前端拼 ／ ⛔ 猜）。
    返回 (text|None, meta)：meta 逐项报 picked_by ／ path ／ skipped_self（⛔ 静默）。"""
    import json                      # ⚠ 本件**⛔ 模块级导 json**（我一手核 · 承我第 22 号）
    from datetime import datetime as _dt5
    _d = pa.dir / "sessions"
    _how, _p = None, None
    try:
        if session_id:
            # ⭐ PM 2026-10-05（我一手逮）：指定会话 ⇒ **唯该会话**（文件不在 ⇒ 如实「上下文缺」）
            #   由：旧法「指定而文件不在」⇒ 落「最新会话」⇒ **跨会话泄漏**（A 会话之问取 B 会话之句）
            _c = _d / ("session_%s.jsonl" % session_id)
            if _c.is_file():
                _how, _p = "request", _c
            else:
                return None, {"picked_by": "request", "reason": "指定会话无记录（⛔ 落他会话 · ⛔ 猜）",
                              "session_id": session_id}
        if _p is None:
            _all = sorted(_d.glob("session_*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
            if _all:
                _how, _p = "newest", _all[0]
    except Exception as _e:
        return None, {"picked_by": None, "reason": "列会话异常: %s" % _e}
    if _p is None:
        return None, {"picked_by": None, "reason": "sessions/ 无可读会话"}
    _meta = {"picked_by": _how, "path": str(_p),
             "session_id": _p.name[len("session_"):-len(".jsonl")], "skipped_self": 0,
             "read_at": _pa_read_at()}
    _last = None
    try:
        for _ln in _p.read_text(encoding="utf-8", errors="replace").splitlines():
            _ln = _ln.strip()
            if not _ln:
                continue
            try:
                _r = json.loads(_ln)
            except Exception:
                continue
            if _r.get("role") != "user":
                continue
            _t = (_r.get("text") or "").strip()
            if not _t:
                continue
            if _t == (question or "").strip():   # ⭐ 本问已落会话 ⇒ 再退一句（否则「上一句」＝本问）
                _meta["skipped_self"] += 1
                continue
            # ⭐ PM 2026-10-05（承 L159）：自测 ／ 探针之痕 ⛔ 作答（⛔ 充作「你上一条」）
            if str(_r.get("topic") or "") == "selftest" or any(_m in _t for _m in PA_SELFTEST_MARKS):
                _meta["skipped_selftest"] = _meta.get("skipped_selftest", 0) + 1
                continue
            _last = _t
    except Exception as _e:
        _meta["reason"] = "读会话异常: %s" % _e
    return _last, _meta


def _ask_decision(question, user_id=None, session_id=None):
    r"""⭐ 修①：**决策账之直答**（PM 2026-10-05 §二 · 老板实测 d1791202075323 之洞之修）。

    病：本机 data\v9\pa\decision_log.json 有据，而「有据才答」闸 ⛔ 扫该面 ⇒ 报「本机无据」
    ⇒ 拒答 ⇒ 回落模型 ⇒ **编造／冒认**（老板所见「T1已完成」＝ 编造；「查不到」＝ 闸漏之冒认）。
    ⇒ 修：问含 **decision_id 形（d\d{13}）** ∨ **「决策记录」之族** ⇒ **直取本机决策账**
      （DecisionStore(_data_dir())）⇒ **有据则答**（grounded）／**账无此条则如实「无此决策」**；
      ⛔ 回落模型（承「断『无』须先扫其体」）。
    返回 dict（本路）｜None（⛔ 属本路 ⇒ 交后续 _ask_scope 分路）。
    """
    import re as _re
    from datetime import datetime as _dt6
    _q = question or ""
    _ids = _re.findall(PA_ASK_DECISION_ID_RE, _q)
    _kw = [k for k in PA_ASK_DECISION_KW if k in _q]
    if not _ids and not _kw:
        return None
    from core.pa.decision import DecisionStore
    ds = DecisionStore(_data_dir())
    try:
        _all = ds.list(None)
    except Exception as _e:
        return {"grounded": False, "refused": False,
                "answer": "决策账不可读：%s ⇒ 如实不答（⛔ 不编）" % _e,
                "answer_source": "decision_store_unreadable",
                "decision_hits": [], "decision_source": str(ds.path),
                "decision_query": {"id": _ids, "kw": _kw},
                "verdict": "决策账不可读（%s）⇒ 如实不答（⛔ 不编）" % _e}
    _hits = [r for r in _all if str(r.get("id")) in _ids] if _ids else _all[-5:]
    if not _hits:
        # ⭐ 2026-10-05（PM 22:34 §一 · 活体之逮）：**拒答亦须有人话句** ——
        #   原 answer 为空（唯 verdict 载由）⇒ 前端只读 answer ⇒ 见「空答」
        #   （承「⛔ 失败静默」：拒答 ⛔ 等于无话）。今 answer 亦载逐字之由。
        _what = ", ".join(_ids) if _ids else "/".join(_kw)
        return {"grounded": False, "refused": True,
                "answer": "本机决策账无此条：%s（在盘共 %d 条）⇒ 如实不答（⛔ 不编）"
                          % (_what, len(_all)),
                "answer_source": "decision_none",
                "decision_hits": [], "decision_source": str(ds.path),
                "decision_query": {"id": _ids, "kw": _kw},
                "verdict": "本机决策账无此条（查 %s）⇒ 如实不答（⛔ 不编）" % _what}

    def _fmt(_r):
        _t = _dt6.fromtimestamp(int(_r.get("ts") or 0)).strftime("%Y-%m-%d %H:%M:%S")
        return "决策 %s：%s · 阶段 %s · note：%s · task：%s · 刻 %s" % (
            _r.get("id"), _r.get("decision"), _r.get("stage"),
            (_r.get("note") or "（无）"), (_r.get("task") or "（无）"), _t)

    if _ids:
        _ans = "\n".join(_fmt(_r) for _r in _hits)
    else:
        _ans = "本机决策账：%s（共 %d 条）· 最近：%s" % (ds.path, len(_all), _fmt(_hits[-1]))
    return {"grounded": True, "refused": False, "answer": _ans,
            "answer_source": "decision",
            "decision_hits": _hits, "decision_source": str(ds.path),
            "decision_query": {"id": _ids, "kw": _kw},
            "decision_found": (_hits[0] if _ids else None),
            "verdict": "决策账有据（本机 %d 条 · 逐字照录 ⛔ 模型生成）" % len(_all)}


def _ask_deadfile(question):
    r"""⭐ 死件账之**直读路**（PM 2026-10-05 22:34 §三① 准 · 同 _ask_decision 之形）。

    病：`data\v9\pa\deadfile_ledger.json` 已入 `PA_FACES`（面在），然其行为**结构化 JSON**
    （径 ／ 键），⛔ 散文 ⇒ 行侧覆盖天然低 ⇒ 问阈 `0.42` 下 **prose 型问恒 ⛔ 中**
    （实测：`真缺件有哪些` ⇒ 0 中）⇒ **面在而问无门**（＝「面在而达 ⛔ ⇒ 假绿之形」之族）。
    ⇒ 本路唯「**多一条直读**」（⛔ 改闸之判据 —— 承 PM 之界）。

    ⭐ **判据（逐字 · 关键字／正则表）**：
      ⒜ 关键字表 `PA_ASK_DEADFILE_KW` —— 问含任一词 ⇒ 本路
      ⒝ 名中 —— 问含**该账已录之名**（`真缺[].value` 之 basename（含／不含扩展）∨
         `真缺[].yaml` ∨ 其 basename）⇒ 本路
         （⚠ ⛔ 泛匹配：唯**账中已录之名** ⇒ 天然无假有据 · 承「⛔ 泛面」之族）
      ⒞ 两条件皆 ⛔ 中 ⇒ 返回 `None`（不属本路 ⇒ 交后续 `_ask_scope` ／ 检索闸）

    ⭐ **阴性对照**（PM 条件⒝）：非死件之问（老板叫什么名字 ／ 公司去年的营收是多少 ／
      今天天气怎么样 ／ 帮我写一首诗）⇒ 本路 None ⇒ 0 中（实测见件 1056 之表）。

    返回 dict（本路）｜None（⛔ 属本路）。
    """
    import json as _json     # ⚠ 本件 ⛔ 模块级导 json（承 L668 之注 · 我第 22 号）
    _q = question or ""
    _kw = [k for k in PA_ASK_DEADFILE_KW if k in _q]
    _path = os.path.join(_data_dir(), PA_ASK_DEADFILE_LEDGER)
    try:
        with open(_path, encoding="utf-8-sig") as _f:
            _led = _json.load(_f)
    except Exception as _e:
        # ⭐ 2026-10-05（我自逮 · 1057 · 承 PM 1183 §八之精神）：账不可读 ⇒ ⛔ 得据此断言「本路」
        #   —— 名中之路须读账 ⇒ 无可判 ⇒ **问 ⛔ 含关键字者 ⇒ 返回 None**（交后续分路）；
        #   ⛔ 返回本路之 dict（否则 **每一问** 皆被本路劫持 ⇒ 承「弱保证 ≠ 真闸」）。
        if not _kw:
            return None
        return {"grounded": False, "refused": False,
                "answer": "死件账不可读（%s：%s）⇒ 如实不答（⛔ 不编）" % (_path, _e),
                "answer_source": "deadfile_unreadable",
                "deadfile_path": _path, "deadfile_query": {"kw": _kw, "names": []},
                "verdict": "死件账面不可读 ⇒ 如实不答（⛔ 不编）"}
    _rows = list(_led.get("真缺") or [])
    _vocab = {}
    for _r in _rows:
        _v = str(_r.get("value") or "")
        _y = str(_r.get("yaml") or "")
        for _s in (_v, _v.replace(chr(92), "/").split("/")[-1],
                   os.path.splitext(_v.replace(chr(92), "/").split("/")[-1])[0],
                   _y, _y.replace(chr(92), "/").split("/")[-1],
                   os.path.splitext(_y.replace(chr(92), "/").split("/")[-1])[0]):
            if len(_s) >= 4:
                _vocab.setdefault(_s, []).append(_r)
    _by_name = sorted([k for k in _vocab if k in _q], key=len, reverse=True)
    if not _kw and not _by_name:
        return None
    _meta = {"器": _led.get("器"), "器印": _led.get("器印"), "取数刻": _led.get("取数刻"),
             "域": (_led.get("域") or {}).get("root"), "件数": _led.get("件数"),
             "分档": _led.get("分档"), "真缺件数": _led.get("真缺件数"),
             "path项数": _led.get("path项数"), "盘上无者数": _led.get("盘上无者数")}
    if _by_name:
        _sel, _seen = [], set()
        for _k in _by_name:
            for _r in _vocab[_k]:
                _key = (_r.get("yaml"), _r.get("line"), _r.get("value"))
                if _key in _seen:
                    continue
                _seen.add(_key)
                _sel.append((_k, _r))
        _ls = ["本机死件账（器 %s · 器印 %s · 取数刻 %s）命中 %d 条 —— 逐字照录："
               % (_meta["器"], _meta["器印"], _meta["取数刻"], len(_sel))]
        for _k, _r in _sel:
            _ls.append("  · 命中「%s」｜%s:%s ｜ value %s ｜ 档 %s ｜ 别处有 %s"
                       % (_k, _r.get("yaml"), _r.get("line"), _r.get("value"),
                          _r.get("档"), _r.get("别处有")))
        return {"grounded": True, "refused": False, "answer": "\n".join(_ls),
                "answer_source": "deadfile", "deadfile_path": _path,
                "deadfile_meta": _meta, "deadfile_query": {"kw": _kw, "names": _by_name},
                "deadfile_hits": [_r for _k, _r in _sel],
                "verdict": "死件账有据（本机账命中 %d 条 · 逐字照录 ⛔ 模型生成）" % len(_sel)}
    _ls = ["本机死件账（取数刻 %s · 器 %s · 器印 %s）：真缺件 %s 条 ／ path 项 %s ／ 盘上无者 %s"
           % (_meta["取数刻"], _meta["器"], _meta["器印"], _meta["真缺件数"],
              _meta["path项数"], _meta["盘上无者数"]),
           "分档：%s" % (_meta["分档"],)]
    if not _rows:
        _ls.append("⇒ 真缺件 0 条（照实之读数 · ⛔ 未知）")
    else:
        _ls.append("真缺件逐条（前 %d 条）：" % min(len(_rows), 20))
        for _r in _rows[:20]:
            _ls.append("  · %s:%s ｜ %s ｜ 档 %s ｜ 别处有 %s"
                       % (_r.get("yaml"), _r.get("line"), _r.get("value"),
                          _r.get("档"), _r.get("别处有")))
        if len(_rows) > 20:
            _ls.append("  …（余 %d 条见账）" % (len(_rows) - 20))
    return {"grounded": True, "refused": False, "answer": "\n".join(_ls),
            "answer_source": "deadfile", "deadfile_path": _path,
            "deadfile_meta": _meta, "deadfile_query": {"kw": _kw, "names": []},
            "deadfile_hits": _rows[:20],
            "verdict": "死件账有据（本机账 %s 条 · 逐字照录 ⛔ 模型生成）" % len(_rows)}


def pa_ask_scan_specs(kb_root):
    u"""`/v9/pa/ask` 之**扫面清单**（一处定形）—— `(根, 面名, 通配)` 之列。

    ⭐ pm_1549 §一.2：扫（`pa_kb_search`）与「印」（`pa_ask_scan_stamp`）**同用此单**
      ⇒ 「将被扫之件集」二处**必同**（⛔ 二处各列 ⇒ 印与扫错位）。
    """
    out = [(Path(kb_root) / rel, rel, ("*.md",)) for rel in PA_KB_ASK_SCOPES]
    for name, roots, globs in pa_faces():
        for spec in roots:
            out.append((_face_root(kb_root, spec), name, globs))
    return out


def _code_sha16(_o, *_more):
    u"""⭐ PM 089 §二（令）：**器之身份** —— 本路由之码之 `sha16`（**印须载器** · 承 `1018 §一`）。

    由：印之义 ＝ 「**以此器** · 以此面滤式 ⇒ 此数」⇒ **⛔ 载器 ⇒ 读者不知何版所出**（半个印）。
    ⛔ 人立之版号（承 `1018 §一`：**号可被默改** ⇒ 印稳而实 ⛔ 稳）。
    取 `inspect.getsource(_o)` ＝ **本路由之码**（⛔ 本模块之全文）；取不到 ⇒ 回落**本模块之字节**（皆为器之身份）。
    ⛔ 两路皆败 ⇒ `None` ⇒ ⭐ **调用方须 `印 = null`**（照实「未核」· ⛔ 以**缺器之印**冒充载器之印）。
    ⚠ 本模块级 ⛔ 增导 ⇒ **局部导入**（承 L22 之族）｜实测取价 ≈ `1.5 ms`／次（`100` 次均值）。
    ⭐ T2-刀26 §二（PM 裁 2026-10-05 17:55）：**印须载「产生此数之器之真源」** —— `_more` 承**面之真源**
      （如 `core/pa/lines.py` 之**模块源**）⇒ 印 ＝ `sha16(路由源 ＋ 真源)`；⛔ 传 `_more` ⇒ **旧义逐字同**（向后兼容）。
    """
    import hashlib, inspect
    _parts = []
    for _x in (_o,) + tuple(_more):
        try:
            _parts.append(inspect.getsource(_x).encode("utf-8"))
        except Exception:
            _parts.append(None)
    if any(_p is None for _p in _parts):
        try:
            with open(__file__, "rb") as _fh:
                _b = _fh.read()
        except Exception:
            return None
    else:
        _b = b"".join(_parts)
    return hashlib.sha256(_b).hexdigest()[:16]


def pa_faces():
    u"""PA **检索面**之表（**惰算** · pm_1520 §二.3）—— 旧名 `PA_FACES` 亦由此出。"""
    return _pa_faces_tables()[0]


def pa_faces_gate():
    u"""`PA_ORG_FACES` 之**门**（`org` ／ `product` · 惰算）。"""
    return _pa_faces_tables()[1]


from core.pa.state_out import PAStateCorrupt


def register_pa_routes(app, brain=None):
    """把 PA 路由挂到 Flask app。brain: 可选 callable(context_text)->str (LLM 对话脑)。

    ⭐ ②v1：路由分居 10 簇（同一 `bp`）⇒ 本处唯「挂载 ＋ 定形」。
    ⭐ brain 以 **per-app 属性**（`app._pa_brain`）传 ⇒ 临时 app（capability_brief ／ pa_app）
       之 `brain=None` ⛔ 覆盖真 app 之脑（承原闭包语义 · 一处不失）。
    ⭐ 首调惰引 10 簇（导入即挂）⇒ 唯引本件亦得全路由（⛔ 半挂之假绿）。
    """
    from core.pa import pa_routes_roster_seats    # noqa: F401
    from core.pa import pa_routes_chat_engine     # noqa: F401
    from core.pa import pa_routes_dispatch_flow   # noqa: F401
    from core.pa import pa_routes_ledger_audit    # noqa: F401
    from core.pa import pa_routes_env_providers   # noqa: F401
    from core.pa import pa_routes_faces_ui        # noqa: F401
    from core.pa import pa_routes_dialog_threads  # noqa: F401
    from core.pa import pa_routes_decision_perm   # noqa: F401
    from core.pa import pa_routes_content_caliber # noqa: F401
    from core.pa import pa_routes_registry        # noqa: F401
    from core.pa import pa_routes_notes           # noqa: F401
    from core.pa import pa_routes_notebooks       # noqa: F401
    try:
        app._pa_brain = brain
    except Exception:
        pass
    app.register_blueprint(bp)
    _set_capability_brief(app)
    _set_pa_app(app)
    return bp
