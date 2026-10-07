# -*- coding: utf-8 -*-
u'''「今日」一屏之四行 —— 一处定形（pm_1824 §二.1 · 技术总监席 f202f89 · 2026-10-08）。

【此件之职】四类之判据 **唯在此一处**（承「一处定形」· pm_1824 §二.1「⛔ 各端各拼」）：
  1) 要我拍的   —— 有哪件事卡在老板这一句话上
  2) 今天该做的 —— 今天不做会出事的
  3) 在等的     —— 在等谁回话 ／ 什么在跑
  4) 近来之痕   —— 昨天办成了什么

【定义页】《「今日」一屏之定义 v1》（PM 立 · _今日一屏之定义_v1.md）。
  本件之四行名 ／ 序 ／ 空态人话 ／ 去处 皆照该页 —— 凡与该页违者 ＝ 缺陷。

【读侧之律】
  - 只读：本件 **不改盘**（唯读 profile ／ ledger ／ dispatch ／ runs ／ threads ／ events）；
  - 空 ⛔ 混 缺：某源读不动 ⇒ 该源标 unreadable ＋ 原样报因，**⛔ 以 0 充「没有」**；
  - ⛔ 自曝之辞上屏：「未接」「尚无后端读数」之属 ⛔ 入人话（定义页 §四.3）；
  - ⛔ 硬编数：逐源现读，数随盘变。

【形】每行：
  {序, 行, 数, 空态, 源:[{面, 径, 读数, 因?}], 去处:[{标, 端}], 件:[...], 缺?}

【逐源之注】定义页 §二 所列之源逐条落此：
  - 要我拍的  ：/v9/pa/context（proposed）· /v9/pa/deliver/authz
                ⚠ /v9/audit/approvals 唯载 **已决之历史**（approved ／ rejected · audit.py:304-329）
                  ⇒ 「**待审**」者另在 write_gate 之内存队列（**无读端**）⇒ 本行照实标「缺」。
  - 今天该做的：/v9/pa/ledger（open）· /v9/pa/dispatch/history
  - 在等的    ：/v9/pes/runs · /v9/pa/dispatch/history · /v9/pa/threads
  - 近来之痕  ：data/v9/pa/sessions（会话）· /v9/pa/threads（archived）· data/v9/pa/events.jsonl
'''
import os
import time
from pathlib import Path

# 近 N 日 ＝ 「近来」（人话非工程话 · 定义页 §二 第 4 行）
RECENT_DAYS = 7
# 逐行「件」之上限（面只显数 · 明细按需展）
MAX_ITEMS = 50


def _mtime_stamp(p):
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(p.stat().st_mtime))
    except Exception:
        return None


def _row(seq, name, empty, sources, anchors, items, missing=None):
    r = {
        '序': seq,
        '行': name,
        '数': len(items),
        '空态': empty,          # 空之时**人话**（定义页 §二）
        '源': sources,
        '去处': anchors,
        '件': items,
    }
    if missing:
        r['缺'] = missing
    return r


def _dispatch_rows(pa):
    u'''派活之行 —— 段之判据与 GET /v9/pa/dispatch/history **同源**（⛔ 二判 · 承 pm_1824 §二.1）。

    由：overlay_history 把四段（已派 ／ 已收 ／ 在做 ／ 已收口）叠到 raw 行上；
      本处若自判 ⇒ 与路由之数**必歧** ⇒ 故**同调一器**，⛔ 各写一份。
    '''
    rows = (pa.handle('dispatch_history').get('rows') or [])
    try:
        from core.pa import receipts as _RC
        _RC.overlay_history(rows)
    except Exception:
        pass
    return rows


# ------------------------------------------------------------------ 1 要我拍的
def _row_authorize(pa, data_dir):
    items, sources = [], []
    # (a) 画像「待裁」—— 真源 ＝ profile status=proposed（⛔ 以 brief 行数充）
    try:
        prop = sorted(pa.profile.entries_by_domain(status='proposed'),
                      key=lambda e: str(e.get('date') or ''), reverse=True)
        for e in prop:
            items.append({'类': u'画像待裁', 'id': e.get('id'),
                          '题': str(e.get('value') or '')[:120], '刻': e.get('date')})
        sources.append({'面': u'GET /v9/pa/context（proposed）',
                        '径': str(pa.profile.path), '读数': len(prop)})
    except Exception as e:
        sources.append({'面': u'GET /v9/pa/context（proposed）', '径': str(pa.profile.path),
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    # (b) 交付「待授权」—— 留痕里 果 ＝ stopped 者（未授权 ⇒ 未发）
    try:
        from core.pa import mailer as _mailer
        _d = _mailer.load_trail(data_dir, None, 500)
        _rows = _d.get('rows') or []
        _stop_all = [r for r in _rows if str(r.get('果') or '').strip().lower() == 'stopped']
        _latest = {}
        for _r in reversed(_stop_all):
            _latest.setdefault(str(_r.get(u'件号') or _r.get('task_id') or ''), _r)
        _stop = list(_latest.values())
        for r in _stop[:MAX_ITEMS]:
            items.append({'类': u'交付待授权', 'id': r.get(u'件号') or r.get('task_id'),
                          '题': str(r.get(u'题') or r.get(u'授权形') or '')[:120],
                          '刻': r.get(u'何刻')})
        sources.append({'面': u'GET /v9/pa/deliver/authz（果 = stopped）',
                        '径': u'data/v9/pa/deliver_authz.jsonl', '读数': len(_stop)})
    except Exception as e:
        sources.append({'面': u'GET /v9/pa/deliver/authz（果 = stopped）',
                        '径': u'data/v9/pa/deliver_authz.jsonl',
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    return _row(1, u'要我拍的', u'没有等你拍的事', sources,
                [{'标': u'就地圈定', '端': u'#paToday（画像 ／ 交付之件在此展开）'}],
                items,
                missing=[{'源': u'审批待审',
                          '因': u'/v9/audit/approvals 唯载已决之历史（approved ／ rejected ·'
                                u' core/gateway/audit.py:304-329）；待审者在 write_gate 之内存队列'
                                u'（core/gateway/write_gate.py:23）**无读端**',
                          '据': u'core/gateway/write_gate.py:23 ／ core/gateway/audit.py:304'}])


# ------------------------------------------------------------------ 2 今天该做的
def _row_todo(pa, data_dir):
    items, sources = [], []
    try:
        open_items = sorted(pa.ledger.open_items(),
                            key=lambda i: str(i.get('due') or i.get('created') or ''))
        today = time.strftime('%Y-%m-%d')
        for i in open_items[:MAX_ITEMS]:
            _due = i.get('due')
            items.append({'类': u'待办', 'id': i.get('id'), '题': i.get('title'),
                          '刻': i.get('created'), '期': _due,
                          '逾期': bool(_due and str(_due) < today)})
        sources.append({'面': u'GET /v9/pa/ledger（open 之件 · 有期者先）',
                        '径': str(pa.ledger.path), '读数': len(open_items)})
    except Exception as e:
        sources.append({'面': u'GET /v9/pa/ledger（open 之件）', '径': str(pa.ledger.path),
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    # 派活中之件（在办者 —— 供「去办」之锚；判据取 stage，⛔ 以表长充）
    try:
        _rows = _dispatch_rows(pa)
        _doing = [r for r in _rows if str(r.get('stage') or '') == u'在做']
        sources.append({'面': u'GET /v9/pa/dispatch/history（在做）',
                        '径': str(pa.dispatch_rec.path), '读数': len(_doing)})
    except Exception as e:
        sources.append({'面': u'GET /v9/pa/dispatch/history（在做）',
                        '径': str(pa.dispatch_rec.path),
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    return _row(2, u'今天该做的', u'今天没有非做不可的', sources,
                [{'标': u'去办', '端': u'POST /v9/pa/ledger/done（办完划掉）'}], items)


# ------------------------------------------------------------------ 3 在等的
def _row_waiting(pa, data_dir, uid, sid):
    items, sources = [], []
    # (a) PES 在跑（run 投影 —— 只读）
    try:
        from core.pa.pes_projection import project_runs
        _p = project_runs(session_id=(sid or None), user_id=(uid or None), limit=50)
        _runs = _p.get('runs') or []
        _live = [r for r in _runs
                 if str(r.get('status') or r.get('state') or '').lower()
                 in ('running', 'queued', 'pending', 'in_progress')]
        for r in _live[:MAX_ITEMS]:
            items.append({'类': u'在跑', 'id': r.get('run_id') or r.get('id'),
                          '题': str(r.get('goal') or r.get('title') or '')[:120]})
        sources.append({'面': u'GET /v9/pes/runs', '径': u'data/v9/pes/runs.jsonl',
                        '读数': len(_live),
                        '降级': [d.get('code') for d in (_p.get('degradations') or [])]})
    except Exception as e:
        sources.append({'面': u'GET /v9/pes/runs', '径': u'data/v9/pes/runs.jsonl',
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    # (b) 派活「待回执」—— 判据与 dispatch/history 同（to_seat 非空 ∧ stage != 已收口）
    try:
        _rows = _dispatch_rows(pa)
        _seat = [r for r in _rows if str(r.get('to_seat') or '').strip()]
        _wait = [r for r in _seat if str(r.get('stage') or '') != u'已收口']
        for r in _wait[:MAX_ITEMS]:
            items.append({'类': u'待回执', 'id': r.get('task_id'),
                          '题': str(r.get('objective') or '')[:120],
                          '席': r.get('to_seat'), '段': r.get('stage')})
        sources.append({'面': u'GET /v9/pa/dispatch/history（待回执）',
                        '径': str(pa.dispatch_rec.path), '读数': len(_wait)})
    except Exception as e:
        sources.append({'面': u'GET /v9/pa/dispatch/history（待回执）',
                        '径': str(pa.dispatch_rec.path),
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    # (c) 线程（未收之线）
    try:
        from core.pa.threads import ThreadStore
        _ts = ThreadStore(data_dir)
        _st = _ts.load(uid)
        _th = _st.get('threads') or []
        for t in _th[:MAX_ITEMS]:
            items.append({'类': u'线程', 'id': (t or {}).get('id'),
                          '题': str((t or {}).get('title') or '')[:120]})
        sources.append({'面': u'GET /v9/pa/threads', '径': str(_ts._path(uid)),
                        '读数': len(_th)})
    except Exception as e:
        sources.append({'面': u'GET /v9/pa/threads', '径': u'data/v9/pa/threads_<uid>.json',
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    # (d) 开机（末次开机之攒件）—— 真源与 GET /v9/pa/resume **同一处**（⛔ 另判一套）
    try:
        from core.pa import resume_face as _RF
        _bs = _RF.boot_summary(root=_RF.root_for_data_dir(data_dir))
        for _cid in list(_bs.get(u'现况攒件') or [])[:MAX_ITEMS]:
            items.append({'类': u'开机攒件', 'id': _cid})
        _src = {'面': u'GET /v9/pa/resume（末次开机之攒件）',
                '径': (_bs.get(u'径') or {}).get(u'攒件箱'), '读数': _bs.get(u'现况攒件_n'),
                '末次开机': _bs.get(u'末次开机'),
                '攒件数_末次账': _bs.get(u'攒件数'), '续办数_末次账': _bs.get(u'续办数')}
        if not _bs.get(u'跑过'):
            _src['因'] = u'未跑（⛔ 未跑过 boot_resume ⇒ ⛔ 以 0 充「无攒件」）'
        sources.append(_src)
    except Exception as e:
        sources.append({'面': u'GET /v9/pa/resume（末次开机之攒件）',
                        '径': u'data/v9/pa/inbox',
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    return _row(3, u'在等的', u'手上没有在等的事', sources,
                [{'标': u'看进度', '端': u'#faceTabs（任务面）'}], items)


# ------------------------------------------------------------------ 4 近来之痕
def _row_recent(pa, data_dir, uid):
    items, sources = [], []
    _sdir = Path(data_dir) / 'sessions'
    _since = time.time() - RECENT_DAYS * 86400
    # (a) 会话（近 N 日）
    try:
        _sess = []
        if _sdir.is_dir():
            for p in _sdir.glob('session_*.jsonl'):
                try:
                    if p.stat().st_mtime >= _since:
                        _sess.append((p.stat().st_mtime, p.stem, p))
                except Exception:
                    continue
        _sess.sort(reverse=True)
        for _m, _sid_name, _p in _sess[:MAX_ITEMS]:
            items.append({'类': u'会话', 'id': _sid_name, '刻': _mtime_stamp(_p)})
        sources.append({'面': u'（读盘）data/v9/pa/sessions/**', '径': str(_sdir),
                        '读数': len(_sess), '窗': u'近 %d 日' % RECENT_DAYS})
    except Exception as e:
        sources.append({'面': u'（读盘）data/v9/pa/sessions/**', '径': str(_sdir),
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    # (b) 归档（threads 档之 archived）
    try:
        from core.pa.threads import ThreadStore
        _ts = ThreadStore(data_dir)
        _st = _ts.load(uid)
        _arc = _st.get('archived') or []
        for a in _arc[:MAX_ITEMS]:
            items.append({'类': u'归档', 'id': (a or {}).get('id'),
                          '题': str((a or {}).get('title') or '')[:120],
                          '刻': (a or {}).get('archived_at')})
        sources.append({'面': u'GET /v9/pa/threads（archived）', '径': str(_ts._path(uid)),
                        '读数': len(_arc)})
    except Exception as e:
        sources.append({'面': u'GET /v9/pa/threads（archived）',
                        '径': u'data/v9/pa/threads_<uid>.json',
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    # (c) 事件之痕（events.jsonl —— 无独立 HTTP 端，本处唯读盘）
    try:
        _ev = pa.events.tail(MAX_ITEMS)
        sources.append({'面': u'（读盘）data/v9/pa/events.jsonl（**无独立 HTTP 端**）',
                        '径': str(pa.events.path), '读数': len(_ev)})
    except Exception as e:
        sources.append({'面': u'（读盘）data/v9/pa/events.jsonl',
                        '径': str(pa.events.path),
                        '读数': None, '因': u'%s: %s' % (type(e).__name__, e)})
    return _row(4, u'近来之痕', u'昨天没有可记之事', sources,
                [{'标': u'看当日之事', '端': u'#paToday（会话 ／ 归档在此展开）'}], items)


# ------------------------------------------------------------------ 门
def build(data_dir=None, user_id=None, session_id=None):
    u'''四行合体（一处出四类）—— **唯读** · ⛔ 硬编。

    返回 {ok, at, 刻之性, 行:[...]}；某行某源读不动 ⇒ 该源 读数 = None ＋ 因（⛔ 充 0）。
    '''
    from core.pa.pa_core import PaCore

    _dd = str(data_dir or os.getenv('PA_DATA_DIR', 'data/v9/pa'))
    _uid = str(user_id or 'default')
    _sid = str(session_id or '')
    pa = PaCore(data_dir=_dd)
    rows = [
        _row_authorize(pa, _dd),
        _row_todo(pa, _dd),
        _row_waiting(pa, _dd, _uid, _sid),
        _row_recent(pa, _dd, _uid),
    ]
    return {
        'ok': True,
        'at': time.strftime('%Y-%m-%d %H:%M:%S'),
        '刻之性': u'读时（活面：逐源现读 ⇒ 数随刻变 · ⛔ 冻结面）',
        '用户': _uid,
        '行': rows,
        '判据之在': u'core/pa/today.py（一处定形 · ⛔ 前端各判 —— 承 pm_1824 §二.1）',
    }
