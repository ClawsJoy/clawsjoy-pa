# -*- coding: utf-8 -*-
u"""本机管理（二阶段 · 授权之动作）—— 承 pm_1852 §四.2（准形 ＝ pm_1847 §一 · 一事一处）。

一阶段（`core/pa/sys_face.py`）唯**读**；本件为其「动作」之约 ——
**逐次授权 ＋ 可撤 ＋ 幂等 ＋ 审计**（⛔ 一按即删）。

铁律（一处定形 · ⛔ 各调用点各判）:
  * **唯本机** —— 远机 `403`（闸在路由之 `_loopback`）。
  * **⛔ 出机** —— 全程本机；清删类**恒本机执行**（⛔ 涉云端）。
  * **⛔ 提权静默** —— 须管理员者：**明标** ＋ 唯**引导用户去点**（⛔ 自提权）。
  * **逐次授权** —— 一 `act` 一 `token`（TTL `120 s` · 绑 `act` ＋ `target` ＋ **预案之印**）· ⛔ 复用。
  * **可撤** —— 删除类入 `<落点>\\_trash\\<刻>\\`（**⛔ 直 `unlink`**）＋ 回执示**撤之径**。
  * **幂等** —— 同 `token` 二次调 ⇒ 回**首次**之回执（⛔ 二删）。
  * **审计** —— 一件一行落 `data/v9/pa/sys_act.jsonl`（刻 ／ `act` ／ `target` ／ 果 ／ 字节 ／ 印）。
  * **⒢ 陪伴轴** —— `axis="chat"` ⇒ **恒拒**（承「聊天 ＝ 只商量」之界）。
  * **缺省 ⛔ 危险** —— `dry_run` 缺省 `True`（缺参 ⇒ 唯回**预案**）。
  * **清之险三档** —— `未验` ／ `已验` ／ `建议清`；**升档须有真演练之痕**（演练记录入审计）。
  * **回执 ⛔ 载本机绝对径** —— 唯书「**去哪看**」（⛔ 书 `C:\\Users\\…`）。
"""
from __future__ import annotations

import hashlib
import json
import os
import time

TOKEN_TTL_S = 120          # 一次性 token 之窗（承 pm_1847 §一.2）
PLAN_MAX_FILES = 4000      # 一次预案之件（有界）
TRASH_DIRNAME = "_trash"   # 回收（⛔ 直删）
OUR_DIR = u"ClawsJoyPA"    # 我司装位（与 sys_face 同处定形）
RAW_PREFIXES = (u"clawsjoy", u"pa_")   # TEMP 下我司物之小写前缀（与 sys_face 同）

# 清之险 —— 三档（⛔「安全」之辞 · 承 pm_1753 §二.1）
RISK_UNVERIFIED = u"未验"
RISK_VERIFIED = u"已验"
RISK_SUGGEST = u"建议清"

ACT_OPEN_SETTINGS = "open_settings"
ACT_CLEAN = "clean"
ACTS = (ACT_OPEN_SETTINGS, ACT_CLEAN)

# ---- 一类 · 开系统页（无破坏性 · **定字面** · 承 sys_face 之既有诸页）--------
SETTINGS_TARGETS = {
    "storagesense": "ms-settings:storagesense",
    "windowsupdate": "ms-settings:windowsupdate",
    "startupapps": "ms-settings:startupapps",
    "defender": "windowsdefender://",
}

# ---- 二类 · 清我司自己之物（**唯白名单之桶** · ⛔ 任意径）--------------------
#   ⛔ 三类（用户文档 ／ 注册表 ／ 服务起停 ／ 卸载 ／ 提权静默）⇒ 恒 `kind:"none"`（本器 ⛔ 挂）。
CLEAN_BUCKETS = (
    # (名, 相对装位/仓根之段, 人话, 须留最近一份)
    (u"装位/update/backup", ("update", "backup"), u"旧备份（回滚之靠山）", True),
    (u"装位/update/stage", ("update", "stage"), u"暂存（旧包）", False),
    (u"装位/diag", ("diag",), u"诊断包", False),
    (u"装位/shell", ("shell",), u"壳之日志", False),
)
_REPO_TMP_BUCKET = (u"仓根/data/tmp", u"仓根之弃树暂存（演练／测试所造）", False)

_OUR_DIR_CACHE = []


# ============================== 小件（一处定形） ==============================
def _our_root():
    u"""我司装位（`%LOCALAPPDATA%\\ClawsJoyPA` ∨ 无 ≫ `ProgramData`）。"""
    la = (os.environ.get(u"LOCALAPPDATA") or u"").strip()
    if la:
        return os.path.join(la, OUR_DIR), False
    return os.path.join((os.environ.get(u"ProgramData") or u"").strip(), OUR_DIR), True


def _repo_root():
    u"""仓根（本件 ＝ `core/pa/sys_act.py` ⇒ 上三级）。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _human(n):
    u"""字节 ⇒ 人话（⛔ 修饰 · 与 sys_face 同处定形）。"""
    try:
        v = float(n)
    except Exception:
        return u"—"
    for unit, k in ((u"TB", 2.0 ** 40), (u"GB", 2.0 ** 30), (u"MB", 2.0 ** 20), (u"KB", 2.0 ** 10)):
        if v >= k:
            return u"%.1f %s" % (v / k, unit)
    return u"%d B" % int(v)


def _stamp(now=None):
    return time.strftime(u"%Y-%m-%dT%H:%M:%S%z", time.localtime(_now(now)))


def _now(now=None):
    return time.time() if now is None else float(now)


def _stamp_fs(now=None):
    u"""目录名之刻 —— **文件系统安全**（Windows ⛔ 许 `:`）⇒ `YYYYmmdd-HHMMSS`。

    ⛔ 以 ISO 刻充目录名（其 `:` 在 Windows 为非法字符 ⇒ `makedirs` 抛 `OSError`）。
    """
    return time.strftime(u"%Y%m%d-%H%M%S", time.localtime(_now(now)))


def buckets():
    u"""{名: {`path`, `人话`, `须留最近一份`, `须管理员`, `去哪看`}} —— 白名单**唯此一处**。

    `去哪看` ＝ **人话之径**（⛔ 绝对径 · 承「回执 ⛔ 载本机绝对径」）。
    """
    root, admin = _our_root()
    out = {}
    for name, segs, label, keep in CLEAN_BUCKETS:
        out[name] = {
            "path": os.path.join(root, *segs),
            "人话": label,
            "须留最近一份": bool(keep),
            "须管理员": bool(admin),
            "去哪看": u"装位 → " + u" → ".join(segs),
        }
    out[_REPO_TMP_BUCKET[0]] = {
        "path": os.path.join(_repo_root(), "data", "tmp"),
        "人话": _REPO_TMP_BUCKET[1],
        "须留最近一份": False,
        "须管理员": False,
        "去哪看": u"仓根 → data → tmp",
    }
    return out


def _walk_files(bucket_path, cap=PLAN_MAX_FILES):
    u"""桶内之**件**（相对径 ＋ 字节）—— 有界 ／ ⛔ 入 `_trash` ／ ⛔ 随符号链接。"""
    rows = []
    if not os.path.isdir(bucket_path):
        return rows
    for dirpath, dirnames, filenames in os.walk(bucket_path, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d != TRASH_DIRNAME)
        for nm in sorted(filenames):
            if len(rows) >= cap:
                return rows
            fp = os.path.join(dirpath, nm)
            try:
                if os.path.islink(fp):
                    continue
                rows.append((os.path.relpath(fp, bucket_path).replace(os.sep, "/"),
                             int(os.path.getsize(fp)), float(os.path.getmtime(fp))))
            except OSError:
                continue
    return rows


# ============================== 预案（dry_run） ==============================
def _plan_digest(payload):
    u"""预案之印（`sha16`）—— 绑 `act` ＋ `target` ＋ 逐条（径 ＋ 字节）。"""
    core = {
        "act": payload.get("act"),
        "target": payload.get("target"),
        "逐条": [[r[0], r[1]] for r in payload.get("_rows") or []],
    }
    blob = json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def _plan_clean(target, now=None):
    bk = buckets().get(target)
    if bk is None:
        return None, u"⛔ 非白名单之桶：%s（白名单：%s）" % (target, u" ／ ".join(sorted(buckets())))
    rows = _walk_files(bk["path"])
    total = sum(r[1] for r in rows)
    keep = bk["须留最近一份"]
    move = rows
    kept = []
    if keep and rows:
        newest = max(rows, key=lambda r: r[2])
        move = [r for r in rows if r is not newest]
        kept = [newest[0]]
    plan = {
        "act": ACT_CLEAN,
        "target": target,
        "目标": target,
        "人话": bk["人话"],
        "逐条": [{"径": r[0], "字节": r[1]} for r in move],
        "件数": len(move),
        "合计": sum(r[1] for r in move),
        "合计人话": _human(sum(r[1] for r in move)),
        "险级": RISK_UNVERIFIED,
        "须管理员": bk["须管理员"],
        "须留最近一份": keep,
        "留之件": kept,
        "去哪看": bk["去哪看"],
        "_rows": move,
        "_total": total,
    }
    return plan, u""


def _plan_open(target):
    lit = SETTINGS_TARGETS.get(str(target or "").strip())
    if lit is None:
        return None, u"⛔ 非白名单之页：%s（白名单：%s）" % (target, u" ／ ".join(sorted(SETTINGS_TARGETS)))
    return {
        "act": ACT_OPEN_SETTINGS,
        "target": target,
        "目标": target,
        "人话": u"打开 Windows 设置页",
        "逐条": [{"径": lit, "字节": 0}],
        "件数": 0,
        "合计": 0,
        "合计人话": u"0 B",
        "险级": RISK_UNVERIFIED,
        "须管理员": False,
        "须留最近一份": False,
        "留之件": [],
        "去哪看": u"本机之设置页（由系统打开）",
        "_rows": [],
        "_total": 0,
    }, u""


def plan(act, target, now=None):
    u"""出**预案**（唯读 · ⛔ 动一物）⇒ `(预案 ∨ None, 因)`。"""
    if act == ACT_CLEAN:
        return _plan_clean(target, now=now)
    if act == ACT_OPEN_SETTINGS:
        return _plan_open(target)
    return None, u"⛔ 非白名单之 act：%s（白名单：%s）" % (act, u" ／ ".join(ACTS))


# ============================== 一次性之授权 ==============================
_TOKENS = {}          # token → {act,target,印,exp,回执}
_SEQ = [0]


def reset_tokens():
    u"""测试用：清空一次性授权之册（⛔ 生产径）。"""
    _TOKENS.clear()
    _SEQ[0] = 0


def _mint(act, target, digest, now=None):
    _SEQ[0] += 1
    tok = u"%s-%d-%s" % (act, _SEQ[0], digest[:8])
    _TOKENS[tok] = {"act": act, "target": target, "印": digest,
                    "exp": _now(now) + TOKEN_TTL_S, "回执": None}
    return tok


# ============================== 审计 ==============================
def _audit(data_dir, row):
    u"""一件一行落 `<data_dir>/sys_act.jsonl`（⛔ 静默吞：失败 ⇒ 回因）。"""
    p = os.path.join(data_dir or os.path.join(_repo_root(), "data", "v9", "pa"), "sys_act.jsonl")
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + u"\n")
        return u""
    except Exception as e:
        return u"审计落盘失败（%s）" % type(e).__name__


# ============================== 真跑 ==============================
def _trash_move(bucket_path, rel, stamp):
    u"""把一件移入 `<落点>\\_trash\\<刻>\\<rel>`（**⛔ 直 `unlink`**）⇒ 因 ∨ `""`。"""
    src = os.path.join(bucket_path, *rel.split("/"))
    dst = os.path.join(bucket_path, TRASH_DIRNAME, stamp, *rel.split("/"))
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.replace(src, dst)
        return u""
    except OSError as e:
        try:
            import shutil
            shutil.move(src, dst)
            return u""
        except Exception:
            return u"移入回收失败（%s）" % type(e).__name__


def _do_clean(target, plan_obj, data_dir, now=None):
    bk = buckets()[target]
    stamp = _stamp_fs(now)
    ok_n, bad = 0, []
    for row in plan_obj.get("_rows") or []:
        why = _trash_move(bk["path"], row[0], stamp)
        if why:
            bad.append((row[0], why))
        else:
            ok_n += 1
    n, moved = plan_obj["件数"], sum(r[1] for r in plan_obj.get("_rows") or [])
    receipt = {
        "件号": n, "席": u"技术总监",
        "果": (u"成" if ok_n == n else (u"部分" if ok_n else u"⛔ 未成")),
        "印": plan_obj["_印"],
    }
    out = {
        "act": ACT_CLEAN, "target": target, "dry_run": False,
        "回执": receipt,
        "逐条": [{"径": r[0], "果": u"入回收"} for r in (plan_obj.get("_rows") or [])][:200],
        "留之件": list(plan_obj.get("留之件") or []),
        "字节": moved,
        "撤之径": u"%s → %s → %s" % (bk["去哪看"], TRASH_DIRNAME, stamp),
        "去更远之界": u"本机回收处（⛔ 出机）",
    }
    if bad:
        out[u"败之件"] = [{"径": r, "因": w} for r, w in bad[:20]]
    return out


def _do_open(target):
    lit = SETTINGS_TARGETS[str(target)]
    why = u""
    try:
        if os.name == "nt":
            os.startfile(lit)                      # noqa: S606 —— 定字面之系统页（⛔ 用户输入）
        else:
            why = u"非 Windows ⇒ ⛔ 起"
    except Exception as e:
        why = u"起不得（%s）" % type(e).__name__
    return {
        "act": ACT_OPEN_SETTINGS, "target": target, "dry_run": False,
        "回执": {"件号": 0, "席": u"技术总监",
                 "果": (u"成" if not why else u"⛔ 未成"), "印": None},
        "逐条": [{"径": lit, "果": (u"已起" if not why else why)}],
        "字节": 0,
        "撤之径": u"无（开页无副作用 · ⛔ 撤）",
    }


# ============================== 入口（一处） ==============================
def act(act=None, target=None, dry_run=True, token=u"", axis=u"sys", data_dir=None, now=None):
    u"""本机管理之一处入口 ⇒ `dict`（`ok` ／ `因` ＋ `code`）。

    `axis="chat"` ⇒ **恒拒**（陪伴轴 ⛔ 动手）；`dry_run` 缺省 `True` ⇒ 唯回预案。
    """
    if str(axis or u"sys") == "chat":
        return {"ok": False, "code": 403,
                "因": u"陪伴轴 ⛔ 触发动作（聊天 ＝ 只商量）—— 请去「本机管理」逐次确认"}
    _act = str(act or u"").strip()
    _tgt = str(target or u"").strip()
    plan_obj, why = plan(_act, _tgt, now=now)
    if plan_obj is None:
        return {"ok": False, "code": 400, "因": why}
    digest = _plan_digest(plan_obj)
    plan_obj["_印"] = digest

    if dry_run is not False:                      # ⭐ 缺省 ⛔ 危险：唯回预案
        tok = _mint(_act, _tgt, digest, now=now)
        return {
            "ok": True, "dry_run": True, "act": _act, "target": _tgt,
            "预案": {k: v for k, v in plan_obj.items() if not k.startswith("_")},
            "token": tok, "ttl_s": TOKEN_TTL_S,
            "印": digest,
        }

    # ---- 二段：真跑（须一次性 token）----
    tok = str(token or u"").strip()
    rec = _TOKENS.get(tok)
    if not tok or rec is None:
        return {"ok": False, "code": 403, "因": u"⛔ 无有效 token ⇒ 拒（须先 dry_run 取预案）"}
    if rec["act"] != _act or rec["target"] != _tgt:
        return {"ok": False, "code": 403, "因": u"⛔ token 与 act ／ target ⛔ 符 ⇒ 拒"}
    if _now(now) > rec["exp"]:
        return {"ok": False, "code": 403, "因": u"⛔ token 已过期（TTL %d s）⇒ 拒" % TOKEN_TTL_S}
    if rec["回执"] is not None:                    # ⭐ 幂等：回首次之回执（⛔ 二删）
        #   ⚠ 须**先于**「预案之印」检 —— 首次之跑已改桶 ⇒ 再算之印必 ⛔ 同
        #   ⇒ 序若反 ⇒ 幂等之径永 ⛔ 达（器病 · 一手之证）。
        out = dict(rec["回执"])
        out[u"幂等"] = True
        return {"ok": True, **out}
    if rec["印"] != digest:                        # 世界已变（桶 ⛔ 同于出预案之时）⇒ 拒
        return {"ok": False, "code": 403, "因": u"⛔ token 与预案之印 ⛔ 符（桶已变）⇒ 拒"}

    bk_admin = bool(plan_obj.get("须管理员"))
    if bk_admin:                                   # ⛔ 提权静默
        return {"ok": False, "code": 403,
                "因": u"须管理员 ⇒ 本器 ⛔ 自提权 —— 唯引导你自己去点（去哪看：%s）" % plan_obj["去哪看"]}

    out = _do_clean(_tgt, plan_obj, data_dir, now=now) if _act == ACT_CLEAN else _do_open(_tgt)
    _audit(data_dir, {
        "刻": _stamp(now), "act": _act, "target": _tgt, "果": out["回执"]["果"],
        "件号": out["回执"]["件号"], "字节": out.get("字节", 0), "印": digest, "演练": True,
    })
    rec["回执"] = out
    out["幂等"] = False
    return {"ok": True, **out}
