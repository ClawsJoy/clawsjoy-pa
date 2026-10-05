# -*- coding: utf-8 -*-
u'''PA 发信器 v1（2026-10-05 · T1 后端稿 · 技术总监席 f202f89 出稿 · 落归 PM b136893）

由（PM 071 §二 · 承 069 §三）：T1 程 ＝ 「交付面入产品」⇒ **接线既有器官**
（`plan` ／ `decision` ＋ `decision_log` ／ `ledger` ＋ `events`）⇒ 把「以用户名义对外交付」
做成**可查账的一步**（⛔ 造新子系统 · 承 PM-1115 手法）。

本模块 ＝ **纯函数层**（便于**落地前成对验收**）；`core/pa/gateway_routes.py` 只加三行包装。

═══ T2-刀15 三补（2026-10-05 · 承 PM 刀15／刀15-补 · `C1` 催信首案）═══
 补① **四件填满**：①「回了什么」②「凭什么」**＋引哪封来信（件号 ＋ sha16 ＋ 面之径逐字）**
     ③「花了多少」**真读数**（wall_s ／ bytes ／ tokens ／ money 皆后端取）④「谁批的」（decision_id ＋ 人 ＋ 刻）
 补② **逐次授权留痕**：每次**发出之意图** ⇒ `data/v9/pa/deliver_authz.jsonl` 一行
     `{件号, 谁批, 何刻, 授权形, decision_id, 果, 报给谁}` ｜ 面 `GET /v9/pa/deliver/authz`
 补③ **`$/件`**：口径 ＝ 该单总花费 ÷ 该单件数（⛔ `$/步` ／ ⛔ 以 token 数代）｜**印须载器**（路由附 `印`）

═══ 判据（皆可机检 · 见 08_工具/闸_T1交付邮件.py）═══
 ⒜ **拍板闸 fail-closed**：⛔ 缺 `decision_id` ∨ 其 ⛔ 在 `decision_log` ∨ 其 ⛔ 「采纳」⇒ 拒发（403）
 ⒝ **口令**（`CJ_MAIL_PASS`）⛔ 入屏 ／ 日志 ／ 回执 ／ 台账：本模块对它**只回布尔**
 ⒞ **幂等**：重放同 `task_id` ⇒ 返既有回执（⛔ 重发）
    幂等键 ＝ `sha256(交办 ＋ 收件人 ＋ 正文散列)`（两端可复算 · 承 071 §二）
 ⒟ **⛔ 失败静默**：回执明写「**停在哪一步** ＋ **报给谁**」（`报给谁` ＝ 停手收件人）
 ⒠ **甲形限域**（红线 063 附）：v1 收件人**只许本人**（`CJ_MAIL_USER`）∨ `PA_MAIL_ALLOW_TO` 白名单；
    对外（第三人）唯**乙形** ＝ 提醒 ＋ 转交 ＋ **人点**（⛔ 代发第三方内容）
 ⒡ **入参 `stop_to`**（T1.1 · 承 PM 072 §六）：**可选**（⛔ 必填）—— 缺省 ⇒ 自解「本人」（＝现网行为 · ⛔ 破现网）；
    唯入回执之「报给谁」（判据 ⒟）；⭐ **⛔ 入幂等键**（幂等仍 ＝ `sha256(task_id, to, body)` ⇒ 换报给谁 ⛔ 当新交办）
 ⒢ **脱敏按字段之职分**（T1.2 · 承 PM 073 §二）：唯抹 `CRED_KEYS`（口令之族）⇒ ⛔ 抹 `收件人` ／ `报给谁` ／ `停在哪一步`（**回执之要件**）；
    由：**过脱敏 ＝ 回执自证不能**（真人律师问「发给了谁」我方须能答 ⇒ ⛔ 以「更安全」为名抹要件）

═══ 界（硬）═══
 ⛔ 收编 `core/lib/proactive_service.py`（其自带 gmail 配置 ⇒ ⛔ 用 `CJ_MAIL_*`）⇒ 唯**另立**薄器；
 ⛔ 「去 AI 标识」之能（R4 · 《生成合成内容标识办法》第 10 条）；⛔ 代他方平台操作（063 附 新律）。
 ⭐ 凭据唯自 **ROOT/.env** —— ROOT ＝ 含 `core/` 之仓根（由**本文件位置**推得 ⇒ **⛔ 按 CWD**）。
   由：今晨 `PortUnconfigured` 即「按 CWD 取件」之实证（承 PM 070 §五 及格一）。

═══ 退出码语义（承 PM 070 §一 · 域内硬条）═══
 0 全过 ｜ 2 判红 ｜ 3 **未全核**（⛔ 不得当放行）｜ 1 运行错 ｜ ⚠ 3 ≠ 2：未核 ≠ 判红（假红亦病）
'''
import datetime
import hashlib
import json
import os
import smtplib
import ssl
import time
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid
from pathlib import Path

#: ROOT ＝ 含 `core/` 之仓根（本文件 = <ROOT>/core/pa/mailer.py ⇒ parents[2]）
ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = os.environ.get('PA_MAIL_ENV_FILE') or str(ROOT / '.env')

WRITER = 'pa.deliver_mail'          # 写者标识（承 core/pa/state_out 之族）
STOP_TO_KEY = 'PA_MAIL_STOP_TO'     # 停手收件人（⛔ 失败静默之「报给谁」）
ALLOW_TO_KEY = 'PA_MAIL_ALLOW_TO'   # 甲形白名单（逗号分隔）
ENV_KEYS = ('CJ_MAIL_USER', 'CJ_MAIL_PASS', 'CJ_MAIL_HOST', 'CJ_MAIL_PORT',
            'CJ_MAIL_FROM', STOP_TO_KEY, ALLOW_TO_KEY)
#: ⭐ 抹值之**凭据字段**（承 PM 073 §二 · T1.2）—— ⛔ 含 `CJ_MAIL_USER`：
#:   其值 ＝ 收件人之一（本人）⇒ **回执之要件** ⇒ 抹之即「过脱敏」（回执自证不能 ∧ 授权链断）。
CRED_KEYS = ('CJ_MAIL_PASS',)
TRAIL_FILE = 'deliver_authz.jsonl'   #: 补② 逐次授权留痕（⛔ 覆写 · 追加）
#: 补② 授权形之枚举（**逐次可辨** · ⛔ 一言蔽之）
AUTHZ_FORMS = ('decision:采纳', 'decision:缺', 'decision:非采纳',
                '停手（未授权 ⇒ ⛔ 未发）', '白名单外 ⇒ 拒（甲形限域）', '凭据未配')
#: ⭐ T2-刀26（PM 2026-10-05 17:56 · 红线级）：授权形之**新族** —— **人点**（老板当场那一下）
#:   ≠ **席决**（席之拍板）。旧形（`decision:*`）**逐字保留**（既有行不改 · 承「⛔ 删旧键」）。
AUTHZ_PREFIX = (u'人点:', u'席决:')
DEFAULT_HOST = 'smtp.163.com'
DEFAULT_PORT = 465
NL = chr(10)


def _redact(text, vals):
    u'''把**凭据字段之值**从文本里抹掉（兜底 · ⛔ 主防线）—— 承 判据 ⒝ ∧ PM 073 §二。

    ⭐ **按字段之职分**：唯抹 `CRED_KEYS`（口令之族）⇒ ⛔ 按「值 ≡ `CJ_MAIL_USER`」抹 —— 由：
    `收件人` ／ `报给谁` ／ `停在哪一步` ＝ **回执之要件**（判据 3 之字段在而值失 ⇒ 留痕失据 · 授权链断）。
    '''
    s = str(text or '')
    for k in CRED_KEYS:
        v = (vals or {}).get(k) or ''
        if v:
            s = s.replace(v, '***')
    return s


def _seal16(*objs):
    u'''⭐ **器之印**（承 PM 089 §二「印须载器」）—— 本模块**自印**：`sha16(器之源)`。

    由：回执行（`deliver_authz.jsonl` 之每行）须载 `印` ⇒ 读者可判「此数出何版之器」
    （⛔ 载器 ⇒ 印在而义亡）。取不到源 ⇒ `None`（照实「未核」 · ⛔ 以缺器之印充载器之印）。
    ⚠ 本模块 ⛔ 依赖路由之 `_code_sha16`（那是路由面之器）⇒ 自持一份（同法 · 同取源法 ⇒ 可复算）。
    '''
    import hashlib as _h_s
    import inspect as _i_s

    _parts = []
    for _x in objs:
        try:
            _parts.append(_i_s.getsource(_x).encode('utf-8'))
        except Exception:
            return None
    return _h_s.sha256(b''.join(_parts)).hexdigest()[:16]


def _read_env_file(path):
    u'''读 ROOT/.env（唯白名单键 · 写法与 PM 两封真发之器**逐字同构**）。⛔ 回值。'''
    d = {}
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('#') or '=' not in s:
                    continue
                k, v = s.split('=', 1)
                k = k.strip()
                if k in ENV_KEYS:
                    v = v.strip()
                    if v:
                        d[k] = v
    except OSError:
        pass
    return d


def cfg():
    u'''凭据之面：唯**布尔** ＋ 来源标注（⛔ 值 ⛔ 入屏）。返回 (面, 值)。'''
    f = _read_env_file(ENV_FILE)
    vals, src = {}, {}
    for k in ENV_KEYS:
        e = os.environ.get(k)
        if e and e.strip():
            vals[k], src[k] = e.strip(), 'env:os'
        elif k in f:
            vals[k], src[k] = f[k], 'env:file'
        else:
            src[k] = '缺'
    user = vals.get('CJ_MAIL_USER', '')
    host = vals.get('CJ_MAIL_HOST') or (('smtp.' + user.split('@')[-1]) if '@' in user else DEFAULT_HOST)
    try:
        port = int(vals.get('CJ_MAIL_PORT') or DEFAULT_PORT)
    except ValueError:
        port = DEFAULT_PORT
    face = {
        'root': str(ROOT),
        'env_file': ENV_FILE,
        'env_file_exists': os.path.exists(ENV_FILE),
        'user_present': bool(user),
        'pass_present': bool(vals.get('CJ_MAIL_PASS')),
        'host': host,
        'port': port,
        'smtp': '%s:%d' % (host, port),
        'from': vals.get('CJ_MAIL_FROM') or user,
        'stop_to': vals.get(STOP_TO_KEY) or user,
        'allow_to': sorted(allow_set(vals)),
        'source': src,
    }
    face['ready'] = bool(user and vals.get('CJ_MAIL_PASS'))
    return face, vals


def allow_set(vals):
    u'''甲形限域之白名单 ＝ {本人} ∪ `PA_MAIL_ALLOW_TO`（逗号分隔）。'''
    out = set()
    u = (vals or {}).get('CJ_MAIL_USER') or ''
    if u:
        out.add(u)
    for a in ((vals or {}).get(ALLOW_TO_KEY) or '').split(','):
        a = a.strip()
        if a:
            out.add(a)
    return out


#: ⭐ T2-刀20 §二：**探针**之判（`task_id` 以 `probe` 起 ／ 含 `probe` ／ 题含「探针」⇒ **⛔ 业务**）
PROBE_TID_PREFIXES = ('probe', 'lv-', 'lv_')
PROBE_MARKS = ('probe', u'探针', u'自检', u'复验', u'验收', 'selfcheck', 'selftest',
               'e2e', 'canary', 'test_', '_test')   # ⭐ 与 `刀19-补` 之「非业务」同族（承 PM 刀20 §二）
#: ⭐ `usage` 之**别名归一**（T2-刀21 §三 · 我补）：⛔ **静默假空** —— 前形 `usage=probe` 与 `探针` ⛔ 同
#: ⇒ 静默返 `0` 行；而前端（CW）正发 `probe ／ business` ⇒ 必踩。未知值 ⇒ 由面 `400`。
USAGE_ALIASES = {
    'probe': u'探针', 'test': u'探针', u'探针': u'探针', u'测试': u'探针', 'canary': u'探针', 'dry': u'探针',
    'business': u'业务', 'biz': u'业务', 'real': u'业务', u'业务': u'业务', u'真': u'业务',
    'all': u'全量', '*': u'全量', u'全量': u'全量',
}


def norm_usage(raw):
    u'''`usage` 之入参 ⇒ `探针 ／ 业务 ／ 全量`；⛔ 认 ⇒ `None`（⇒ 面 `400` · ⛔ 静默假空）。缺 ／ 空 ⇒ `None`（＝不滤）。'''
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return USAGE_ALIASES.get(s.lower())


def _is_real_send(row):
    u'''⭐ T2-刀25 §二（PM 裁）：**真发**之判 ＝ 「果」为 `ok`（＝ SMTP 动作已发生）∨ `delivered` 为真。'''
    r = row or {}
    kind = str(r.get(u'果') or r.get('kind') or '').strip().lower()
    if kind == 'ok':
        return True
    d = r.get('delivered')
    if isinstance(d, bool):
        return d
    return str(d or '').strip().lower() in ('true', '1', 'yes')


def trail_usage(row, with_reason=False):
    u'''留痕 ／ 台账之**用途**（T2-刀25 §二 · PM 裁：**以果判 · ⛔ 以名判**）。

    ⭐ 判据 ＝ **有无真发（SMTP 动作）**：`果 = ok`（真发）⇒ **业务**（**果覆初筛**）；
    否则以 `PROBE_TID_PREFIXES` ／ `PROBE_MARKS` **初筛**（名形）；命中 ⇒ **探针**；否则 **业务**（默认）。
    '''
    r = row or {}
    if _is_real_send(r):
        return (u'业务', u'果=ok（真发 · SMTP 动作）⇒ 业务（果覆初筛）') if with_reason else u'业务'
    tid = str(r.get(u'件号') or r.get('task_id') or '')
    low = tid.lower()
    for x in PROBE_TID_PREFIXES:
        if low.startswith(x):
            return (u'探针', u'件号起 `%s`（初筛）' % x) if with_reason else u'探针'
    blob = low + ' ' + str(r.get(u'题') or r.get('subject') or '')
    for m in PROBE_MARKS:
        if m.lower() in blob:
            return (u'探针', m + u'（初筛）') if with_reason else u'探针'
    return (u'业务', '') if with_reason else u'业务'


def norm_to(raw):
    u'''`to` 之**形归一**（T2-刀19 §二.1）：认 **列表** ∨ **逗号分隔之字符串**；⛔ 把字符串当 iterable。

    ⭐ 病源：界面文案逐字为「收件人 `to`（逗号分隔）」⇒ 照文案传字符串者，旧形
    `[str(a) for a in (p.get("to") or [])]` 会**逐字符**成表（`'a@b.c'` ⇒ `['a','@','b',…]`）
    ⇒ 连**本人**亦进不了白名单 ⇒ `403`（交付链断）。此处**先归一，再入闸**。
    兼收 `;`／`；` 之分隔；保序、去重。
    '''
    out = []
    if raw is None:
        return out
    items = list(raw) if isinstance(raw, (list, tuple, set)) else [raw]
    for it in items:
        if it is None:
            continue
        s = str(it)
        for sep in (u';', u'；'):
            s = s.replace(sep, ',')
        for part in s.split(','):
            p = part.strip()
            if p and p not in out:
                out.append(p)
    return out


def to_shape(raw):
    u'''入参 `to` 之**形**（唯用于回执 ／ 排障之照实：`列表` ／ `字符串` ／ `缺`）。'''
    if raw is None or raw == "":
        return u'缺'
    if isinstance(raw, (list, tuple, set)):
        return u'列表'
    if isinstance(raw, str):
        return u'字符串'
    return type(raw).__name__


def self_addressed_ok(to_list, vals):
    u'''收件人闸（甲形）：⛔ 白名单者出列（对外须乙形）。返回 (过, 出列者)。'''
    allow = allow_set(vals)
    bad = [a for a in (to_list or []) if a not in allow]
    return (not bad), bad


def _body_bytes(body):
    if isinstance(body, bytes):
        return body
    return str(body or '').encode('utf-8')


def idem_key(task_id, to_list, body):
    u'''幂等键 ＝ sha256(交办 ＋ 收件人 ＋ 正文散列)（两端可复算 · 承 071 §二）。'''
    h = hashlib.sha256()
    h.update(str(task_id or '').encode('utf-8'))
    h.update(b'|')
    h.update(','.join(sorted(to_list or [])).encode('utf-8'))
    h.update(b'|')
    h.update(hashlib.sha256(_body_bytes(body)).hexdigest().encode('ascii'))
    return h.hexdigest()

def gate(data_dir, decision_id):
    u'''拍板闸（fail-closed）。返回 (过, 因, 拍板行)。

    ⛔ 缺 `decision_id` ⇒ 拒 ｜ ⛔ 在 `decision_log` ⇒ 拒 ｜ 在而 ⛔ 「采纳」⇒ 拒（承 069 §三.2）。
    '''
    did = str(decision_id or '').strip()
    if not did:
        return False, u'缺 decision_id：以用户名义对外交付须先有老板拍板（fail-closed ⇒ 拒发）', None
    from core.pa.decision import DecisionStore
    rows = [r for r in DecisionStore(data_dir).list(None, None, limit=1000)
            if str(r.get('id')) == did]
    if not rows:
        return False, u'decision_id 不在 decision_log：%s（fail-closed ⇒ 拒发）' % did[:60], None
    r = rows[-1]
    if r.get('decision') != u'采纳':
        return False, u'该拍板为「%s」⇒ ⛔ 采纳 ⇒ 拒执（承 069 §三.2：未采纳不得出手）' % r.get('decision'), r
    return True, '', r


def _receipts_path(data_dir):
    return Path(data_dir) / 'deliver_mail.json'


def _shape(doc):
    u'''PA 侧业务结构判据（承 core/pa/state_out 之族 · 判据留 PA 侧）。'''
    if not isinstance(doc.get('receipts'), list):
        return False, u'receipts 需为 list'
    return True, ''


def load_receipts(data_dir):
    from core.pa.state_out import read_state
    p = _receipts_path(data_dir)
    if not p.exists():
        return {'receipts': []}
    d = read_state(p, WRITER, _shape)
    d.setdefault('receipts', [])
    return d


def find_by_task(data_dir, task_id):
    u'''幂等之查：按 `task_id` 取最近一条回执行（⛔ 未得 ⇒ None）。'''
    for r in reversed(load_receipts(data_dir).get('receipts') or []):
        if r.get('task_id') == task_id:
            return r
    return None


def record_receipt(data_dir, row):
    u'''幂等之写：**只记成件**（失败 ⛔ 记账 ⇒ 重放可重试；失败之痕走 events）。'''
    from core.pa.state_out import write_state
    rows = list(load_receipts(data_dir).get('receipts') or [])
    rows.append(row)
    write_state(_receipts_path(data_dir), WRITER, _shape,
                {'version': 1, 'receipts': rows}, reason='pa.deliver_mail.record')


# ========================= T2-刀15 补②：逐次授权留痕 =========================
def _trail_path(data_dir):
    return Path(data_dir) / TRAIL_FILE


def authz_trail(data_dir, row):
    u'''逐次留痕：**追加**一行 JSONL（⛔ 覆写 · ⛔ 静默）。返回 (径, 错)。

    行形（承 PM 刀15-补 判据⑤）：`{件号, 谁批, 何刻, 授权形, decision_id, 果}` ＋ `报给谁`（判据⑥）。
    '''
    p = _trail_path(data_dir)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + NL)
        return str(p), ''
    except Exception as e:
        return str(p), ('%s: %s' % (type(e).__name__, e))[:200]


def load_trail(data_dir, task_id=None, limit=50, usage=None):
    u'''读留痕（⛔ 未得 ⇒ 空表 ＋ 一行 stderr · ⛔ 以 `0` 充「无留痕」）。'''
    p = _trail_path(data_dir)
    rows, bad = [], 0
    if p.exists():
        try:
            for line in open(p, encoding='utf-8', errors='replace'):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    bad += 1
        except Exception as e:
            import sys as _s
            _s.stderr.write('[mailer] 留痕不可读（%s）：%s\n' % (type(e).__name__, p))
    # ⭐ T2-刀26（PM 2026-10-05 18:02 提级）：**一件一授权**之**机械侦** —— 逐决计真发之件散列集；
    #   凡 >1 件 ⇒ 显红（承 PM 之器「决策复用之侦」）。⛔ 唯报（⛔ 改盘）。
    _reuse_map = {}
    for _r in rows:
        if str(_r.get('果') or '').strip().lower() != 'ok':
            continue
        _d0 = str(_r.get('decision_id') or '')
        if not _d0:
            continue
        _reuse_map.setdefault(_d0, set()).add(str(_r.get('件散列') or ''))
    _reuse_red = {k: sorted([x for x in v if x]) for k, v in _reuse_map.items() if len([x for x in v if x]) > 1}
    if task_id:
        rows = [r for r in rows if str(r.get(u'件号') or r.get('task_id') or '') == str(task_id)]
    # ⭐ T2-刀20 §二：逐行标「用途」（旧行同标 · ⛔ 猜）；`usage=` 可滤（默认 `all`）
    for _r in rows:
        # ⭐ T2-刀25 §二：**读时**按今律重标（果判）—— ⛔ 用写时之旧标
        _r[u'用途'], _r[u'用途之由'] = trail_usage(_r, True)
    _cnt = {u'业务': sum(1 for r in rows if r.get(u'用途') == u'业务'),
            u'探针': sum(1 for r in rows if r.get(u'用途') == u'探针'),
            u'全量': len(rows)}
    # ⭐ T2-刀21 §三：别名归一後方滤（⛔ 静默假空；未知值 ⇒ 由面 `400`）
    _u_raw = None if usage is None else str(usage).strip()
    _u = norm_usage(usage) if _u_raw else None
    if _u in (u'探针', u'业务'):
        rows = [r for r in rows if r.get(u'用途') == _u]
    n = len(rows)
    try:
        lim = max(1, min(int(limit or 50), 500))
    except Exception:
        lim = 50
    return {'面之径逐字': str(p), '行数': n, '坏行': bad, u'用途之数': _cnt,
            u'一件一授权': {'判据': u'同一 `decision_id` ⛔ 授权 >1 件**真发**（`果 = ok`）：件散列 之集 >1 ⇒ 显红（承 PM 并账器「决策复用之侦」）',
                          '复用': _reuse_red, '显红': bool(_reuse_red)},
            u'usage_入参': _u_raw, u'usage_归': _u, u'usage_认': sorted(USAGE_ALIASES),
            u'用途之判据': u'⭐ 以**果**判（承 T2-刀25 §二）：`果 = ok`（真发 · SMTP 动作）⇒ **业务**（果覆初筛）；否则初筛（`件号` 以 `probe ／ lv-` 起 ∨ 含 `probe ／ 探针`…）⇒ **探针**；否则 **业务**',
            'rows': rows[-lim:], 'truncated': bool(n > lim)}


def stop_trace(payload, data_dir, now=None):
    u'''**停手之留痕**（承 `PA-6` · 判据⑥）：任一步过不去 ⇒ 停手 ＋ 报。

    ⭐ 硬条：**「报给谁」须有字段**（⛔ 空 · ⛔ 以「未配」充「无此字段」）。
    返回 doc（含 `报给谁` ＋ `报给谁之面` ＋ 留痕径）。
    '''
    face, _vals = cfg()
    p = payload if isinstance(payload, dict) else {}
    ts = now or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    task_id = str(p.get('task_id') or '').strip()
    _st = str(p.get('stop_to') or '').strip()
    stop_to = _st or face.get('stop_to') or ''
    who_src = (u'入参 stop_to' if _st else
               (u'face.stop_to（.env PA_MAIL_STOP_TO ∨ 本人）' if face.get('stop_to') else u'缺'))
    row = {'件号': task_id, 'task_id': task_id,
           '谁批': str(p.get('user_id') or ''), '何刻': ts,
           '授权形': u'停手（未授权 ⇒ ⛔ 未发）', '果': 'stopped',
           '停在哪一步': str(p.get('stage') or u'交付'),
           '报给谁': stop_to, '报给谁之面': who_src,
           '题': str(p.get('subject') or ''), '收件人': list(p.get('to') or []),
           '面之径逐字': u'core/pa/mailer.py:stop_trace',
           # ⭐ 修③（PM 2026-10-05 17:56）：停手行亦须载 `印`（⛔ None）。
           '印': _seal16(stop_trace)}
    path, err = authz_trail(data_dir, row)
    try:
        from core.pa.pa_core import PaCore
        PaCore(data_dir).events.append('fact', 'pa_deliver_stop',
                                        {'task_id': task_id, 'stage': row['停在哪一步'],
                                         'report_to': stop_to, 'report_to_src': who_src,
                                         'user_id': row['谁批']},
                                        source='pa/deliver/stop')
    except Exception:
        pass
    return {'ok': True, '件号': task_id, '停在哪一步': row['停在哪一步'],
            '报给谁': stop_to, '报给谁之面': who_src, '何刻': ts,
            '留痕': {'面之径逐字': path, '错': err}, '授权留痕行': row,
            '注': u'停手触发即留痕（⛔ 静默）｜「报给谁」恒有字段（承 PA-6）'}


#: 唯一**传输缝**（本器之正控可替换 · ⛔ 生产不设伪实现 · 默认真发）
TRANSPORT = None


def _smtp_transport(face, vals, to_list, subject, body, timeout=30):
    u'''低层发信（**唯一** smtplib 处）。返回 (成, 停在哪一步, 情报)。

    写法与 PM 两封真发之器（`CASE-L02` ／ `CASE-L03`）**逐字同构**：`SMTP_SSL` ＋ `465` ＋
    `Header` ／ `formataddr` ／ `make_msgid`（⛔ 抄其**自带 gmail 配置**之件 ⇒ 另立薄器）。
    '''
    user = vals.get('CJ_MAIL_USER') or ''
    pw = vals.get('CJ_MAIL_PASS') or ''
    if not (user and pw):
        miss = [k for k in ('CJ_MAIL_USER', 'CJ_MAIL_PASS') if not vals.get(k)]
        return False, u'凭据', {'error': u'凭据未配（缺 %s）' % u'、'.join(miss)}
    frm = face.get('from') or user
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = formataddr((str(Header('ClawsJoy PA', 'utf-8')), frm))
    msg['To'] = ', '.join(to_list)
    msg['Message-ID'] = make_msgid(domain=(frm.split('@')[-1] or 'clawsjoy'))
    t0 = time.time()
    try:
        ctx = ssl.create_default_context()
        srv = smtplib.SMTP_SSL(face['host'], face['port'], timeout=timeout, context=ctx)
        try:
            srv.login(user, pw)
            srv.send_message(msg)
        finally:
            try:
                srv.quit()
            except Exception:
                pass
    except Exception as e:
        return False, u'发送', {'error': _redact('%s: %s' % (type(e).__name__, e), vals)[:200],
                              'wall_s': round(time.time() - t0, 3)}
    return True, u'完成', {'message_id': str(msg['Message-ID']),
                         'wall_s': round(time.time() - t0, 3),
                         'smtp': face['smtp'] + ' (SSL)',
                         'raw_bytes': len(msg.as_bytes())}


def send_mail(face, vals, to_list, subject, body, timeout=30):
    u'''发信之唯一出口（经传输缝 ⇒ 正控可换 · 生产默认真发）。'''
    return (TRANSPORT or _smtp_transport)(face, vals, to_list, subject, body, timeout)

def build_receipt(face, task_id, to_list, subject, body, ts, decision_row, transport,
                  stopped_at=None, err='', mid='', wall_s=None, bytes_out=None, dry=False,
                  in_reply_to=None):
    u'''回执四件 ＋ 人话（承 PA-4 ／ pm_1115 §一.1）—— ⭐ **读数皆后端取**（⛔ 前端估 · 承 L124）。

    四件：① 做了什么 ② 凭什么 ③ 花了多少 ④ 谁批的 ｜ ⭐ 并报「停在哪一步 ＋ 报给谁」（判据 ⒟）。
    入 ／ 出之字节**分列**；`tokens` ／ `money` 属**内部成本闸**（承 057 §一.3 之分轴）。
    '''
    b_in = len(_body_bytes(body))
    # ⭐ 补①-③ 之「照实」：**干跑 ⇒ 未发** ⇒ `bytes.out` 无值（⛔ 以 `in` 充 `out`）
    b_out = (None if dry else (b_in if bytes_out is None else int(bytes_out)))
    dec = decision_row or {}
    did = str(dec.get('id') or '')
    b16 = hashlib.sha256(_body_bytes(body)).hexdigest()[:16]
    # ⭐ 补①-③：`wall_s` 之三态 —— 真发 ⇒ 秒数 ／ 干跑 ⇒ **未走** ／ 余 ⇒ 未取得（⛔ 一言蔽「未取得」）
    if isinstance(wall_s, (int, float)):
        w = '%.3f' % wall_s
    elif dry:
        w = u'未走（干跑 ⇒ ⛔ 未发）'
    else:
        w = u'未取得（真发之刻未回 ⇒ 照实）'
    _ir = in_reply_to if isinstance(in_reply_to, dict) else {}
    _ir_rec = ({u'件号': str(_ir.get('件号') or _ir.get('id') or ''),
               u'sha16': str(_ir.get('sha16') or ''),
               u'面之径逐字': str(_ir.get('面之径逐字') or _ir.get('path') or ''),
               u'原信之刻': str(_ir.get('刻') or _ir.get('ts') or '')}
              if _ir else u'缺（未附原信 ⇒ ⛔ 装已附）')
    rec = {
        '题': subject,
        '刻': ts,
        # ⭐ 补①-①：「回了什么」—— 唯据**本件**（⛔ 前端估）
        '回了什么': {
            '件号': task_id,
            '题': subject,
            '正文字节': b_in,
            '件散列': b16,
            '首句': (str(body or '').strip().splitlines() or [''])[0][:120],
        },
        '做了什么': {
            '动作': u'以「%s」之名，向 %s 发《%s》' % (face.get('from') or u'—', u'、'.join(to_list), subject),
            'Message-ID': mid,
            '服务器': face.get('smtp') or u'—',
            '传输': transport,
            '正文字节': b_in,
            '件散列': b16,
            '不可撤销': True,
        },
        '凭什么': {
            '授权之据': u'decision %s（%s）' % (did or u'—', dec.get('decision') or u'—'),
            '内容之据': u'body_md sha16 %s ／ %d B' % (b16, b_in),
            # ⭐ 补①-②：**引哪封来信**（件号 ＋ sha16 ＋ 面之径逐字）—— C1「原来信之件」
            '引哪封来信': _ir_rec,
            '闸': u'decision_gate: pass',
        },
        '花了多少': {
            'wall_s': wall_s,
            'bytes': {'in': b_in, 'out': b_out},
            'tokens': None,
            'tokens_source': u'无（本路 ＝ smtplib 直发 · ⛔ 模型路）',
            'money': 0.0,
            'currency': 'CNY',
            'source': u'smtp:local（自有凭据 · ⛔ 外呼）',
            # ⭐ 补①-③：真读数之「代器」标注 —— ⛔ 前端估（承 L124）
            '读数之器': u'core/pa/mailer.py:_smtp_transport（wall_s ＝ smtplib 实测；bytes ＝ len(msg.as_bytes())）',
        },
        # ⭐ 补③：`$/件`（口径 ＝ 该单总花费 ÷ 该单件数 · ⛔ $/步 · ⛔ 以 token 数代）
        '成本': {
            '件数': 1,
            '口径': u'该单总花费 ÷ 该单件数（⛔ $/步 · ⛔ 以 token 数代）',
            '总花费_元': 0.0,
            '单价_元每件': 0.0,
            '币': 'CNY',
            'tokens': None,
            'tokens_之由': u'本路 ＝ smtplib 直发（⛔ 模型路）⇒ **无 token**（⛔ 以 0 充已计）',
            '本地_远端': u'本地（自有凭据 ／ 本机进程 · ⛔ 云端 API ⇒ 0 元）',
            '印': None,
            '印之由': u'**印须载器**（承 PM 089 §二）：由路由 `_code_sha16` 载入 ⇒ 模块内 ⛔ 自印',
        },
        '谁批的': {
            '人': dec.get('user_id') or '',
            'decision_id': did,
            'decision': dec.get('decision') or '',
            'note': dec.get('note') or '',
            'ts': dec.get('ts'),
        },
        'task_id': task_id,
        '收件人': list(to_list),
        '停在哪一步': stopped_at,
        '报给谁': face.get('stop_to') or '',
        '干跑': bool(dry),
        '错误': err or '',
    }
    if err:
        rec['凭什么']['闸'] = u'decision_gate: pass ／ 发送: fail'
    lines = [
        u'· 做了什么：%s' % rec['做了什么']['动作'],
        u'· 凭什么：%s（%s）' % (rec['凭什么']['授权之据'], rec['凭什么']['内容之据']),
        u'· 引哪封来信：%s' % (u'件号 %s ／ sha16 %s' % (_ir_rec['件号'], _ir_rec['sha16'])
                             if _ir else _ir_rec),
        u'· 花了多少：%s · 入 %d B ／ 出 %s · 0 元 ／ 件（本机直发 · ⛔ 外呼）'
        % (w, b_in, ('未发' if b_out is None else ('%d B' % b_out))),
        u'· 谁批的：%s（%s）' % (rec['谁批的']['人'] or u'—', rec['谁批的']['decision'] or u'—'),
    ]
    if stopped_at:
        lines.append(u'· 停在哪一步：%s ⇒ 报给 %s' % (stopped_at, rec['报给谁'] or u'（未配停手收件人）'))
    rec['人话'] = lines
    if err or stopped_at:
        rec['人话句'] = u'未发出：停在「%s」，已报 %s。' % (stopped_at or u'—', rec['报给谁'] or u'（未配停手收件人）')
    elif dry:
        rec['人话句'] = u'干跑：闸与幂等皆过，但**未真发**（承 070 §一：未核 ≠ 判红 · 真发须 --live）。'
    else:
        rec['人话句'] = u'已按你的拍板，把《%s》发到 %s（0 元 · %s 秒）。' % (subject, u'、'.join(to_list), w)
    return rec


def _trace(data_dir, kind, rec, task_id, did, user_id, to_list, subject, mid, body16, vals, dec=None):
    u'''落痕：`events`(fact) ＋ `ledger` 一行（⛔ 失败亦留痕 · ⛔ 静默）。⛔ 口令入此。返回缺（空=齐）。'''
    try:
        from core.pa.pa_core import PaCore
        core = PaCore(data_dir)
        core.events.append('fact', 'pa_deliver_mail',
                           {'kind': kind, 'task_id': task_id, 'decision_id': did,
                            'user_id': user_id, 'to': list(to_list or []), 'subject': subject[:80],
                            'message_id': mid, '件散列': body16,
                            'stage': rec.get('停在哪一步') or u'完成',
                            'report_to': rec.get('报给谁') or ''},
                           source='pa/deliver/mail')
        if kind == 'ok':
            # ⭐ T2-刀20 §二：探针之台账行须**自标**（⛔ 读面之「明标」唯靠猜）
            _u = trail_usage({'件号': task_id, u'题': subject})
            _pre = (u'[⛔ 探针·⛔ 业务] ' if _u == u'探针' else '')
            core.ledger.add(
                u'%s[交付·邮件] %s（%s）' % (_pre, subject[:40], u'、'.join(to_list or [])),
                kind='todo', status='done',
                note=_redact(u'刻 %s ／ 收件人 %s ／ 件散列 %s ／ Message-ID %s ／ 授权 %s'
                             % (rec.get('刻'), u'、'.join(to_list or []), body16, mid, did), vals))
    except Exception as e:
        return _redact('%s: %s' % (type(e).__name__, e), vals)[:200]
    return ''


def deliver(payload, data_dir, dry_run=False, now=None):
    u'''T1「可查账的一步交付」：拍板闸 ＋ 甲形限域 ＋ 幂等 ＋ 发 ＋ 落痕 ＋ 回执。返回 (http_code, doc)。

    序（⛔ 变 · 皆判据）：① 缺参 ② 幂等（重放 ⇒ 返既有回执）③ 拍板闸 ④ 凭据闸 ⑤ 收件人闸（甲形限域）⑥ 发 ⑦ 落痕。
    ⭐ T1.1（承 PM 072 §六）：入参可选键 `stop_to` 之解在 ⑤ 之前 ⇒ 唯入回执之「报给谁」（⛔ 入幂等键）。
    ⛔ 不改既有字段之语义（唯加键 · 承 057 §一.2）。
    ⭐ T2-刀19 §二.2：入参 `to` 之形**认「列表」∨「逗号分隔字符串」**（承界面文案逐字）；
    `;` ／ `；` 亦作分隔；归一**在闸之前**（⛔ 把字符串当 iterable）。
    '''
    p = payload if isinstance(payload, dict) else {}
    face, vals = cfg()
    # ⭐ T1.1（承 PM 072 §六）：可选键 `stop_to` —— ⛔ 必填；缺省 ⇒ 自解「本人」（＝现网行为 · ⛔ 破）；
    #   唯入回执之「报给谁」（判据 ⒟）；⭐ ⛔ 入幂等键（幂等仍 ＝ sha256(task_id, to, body)）。
    _stop_to = str(p.get('stop_to') or '').strip()
    if _stop_to:
        face['stop_to'] = _stop_to
    ts = now or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    task_id = str(p.get('task_id') or '').strip()
    decision_id = str(p.get('decision_id') or '').strip()
    _to_raw = p.get('to')
    to_list = norm_to(_to_raw)
    subject = str(p.get('subject') or '').strip()
    body = p.get('body_md') or ''
    user_id = str(p.get('user_id') or '')
    # ⭐ T2-刀26（PM 2026-10-05 17:56 · 红线级 · 修①）：**对外发之授权须可辨「人点」／「席决」**；
    #   病：老板 `17:51:47` 亲点首件，其行竟挂 `11:58:42` 之旧决 ⇒ 台账读来是「PM 自批」。
    #   入参（新键 · 旧键不动）：`人点`／`human_click` ＝ {谁, 刻, 卡}（∨ 一字「谁」）。
    _human = p.get('人点') or p.get('human_click') or p.get('人点之证')
    if _human and not isinstance(_human, dict):
        _human = {'谁': str(_human)}
    _human = _human if isinstance(_human, dict) else None
    policy = {'stop_to': face.get('stop_to') or '', 'dry_run': bool(dry_run),
              'allow_to': face.get('allow_to'), 'env_file': face.get('env_file'),
              # ⭐ T2-刀19：入参之形须照实（`字符串` 之传法 ⇒ 旧形必逐字符 ⇒ 此键即其证）
              'to_入参之形': to_shape(_to_raw), 'to_归一': list(to_list)}
    # ⭐ 补①-②：引哪封来信（C1「原来信之件」）—— 入参 `in_reply_to` ∨ `src_letter`
    _ir = p.get('in_reply_to') or p.get('src_letter') or {}
    _ir = _ir if isinstance(_ir, dict) else {}
    dec = None  # 拍板行（gate 后填）

    def _b16_of(_b):
        return hashlib.sha256(_body_bytes(_b)).hexdigest()[:16]

    def _trail_form(kind, blocked_by):
        if kind in ('ok', 'dry_run'):
            # ⭐ 修①：**人点**（老板当场那一下）优先 ⟷ **席决**（席之拍板）—— 二者 ⛔ 同形。
            if _human:
                return u'人点:%s' % (str(_human.get('卡') or _human.get('card') or u'卡')[:40])
            return u'席决:%s' % (decision_id or u'缺')
        if blocked_by == 'decision_gate':
            return (u'席决:缺' if not decision_id else u'席决:非采纳')
        if blocked_by == 'recipient_scope':
            return u'白名单外 ⇒ 拒（甲形限域）'
        if blocked_by == 'credentials':
            return u'凭据未配'
        if blocked_by == 'decision_reuse':
            return u'席决:%s（复用 ⇒ 拒 · 一件一授权）' % (decision_id or u'缺')
        return u'停手（未授权 ⇒ ⛔ 未发）'

    def _trail(kind, rec=None, blocked_by=None, body16=''):
        u'''补②：**逐次留痕**（⛔ 唯成功者才留 ⇒ ⛔ 以「留痕」充「已发」）。'''
        _r = rec if isinstance(rec, dict) else {}
        row = {'件号': task_id, 'task_id': task_id,
               '谁批': (((dec or {}).get('user_id') or '') if kind in ('ok', 'dry_run') else (user_id or '')),
               '何刻': ts, '批之刻': ((dec or {}).get('ts') if dec else None),
               '授权形': _trail_form(kind, blocked_by),
               'decision_id': decision_id, 'decision': ((dec or {}).get('decision') or ''),
               '果': kind, '停在哪一步': _r.get('停在哪一步'),
               '报给谁': _r.get('报给谁') or policy.get('stop_to') or '',
               '收件人': list(to_list), '题': subject, '件散列': body16,
               '引哪封来信': (str(_ir.get('件号') or _ir.get('id') or '') if _ir else ''),
               # ⭐ 修①：**人点**之痕（谁点 ＋ 刻）—— ⛔ 唯「谁批」一言（人与席 ⛔ 同形）。
               '人点': (dict(_human) if _human else None),
               '谁点': (str(_human.get('谁') or '') if _human else (user_id or '')),
               '人点之刻': (str(_human.get('刻') or ts) if _human else None),
               '面之径逐字': u'core/pa/mailer.py:deliver',
               # ⭐ 修③（PM 2026-10-05 17:56）：回执行须载 `印`（⛔ None）—— 印 ＝ 生此数之器之源。
               '印': _seal16(deliver)}
        row[u'用途'] = trail_usage(row)   # ⭐ T2-刀20 §二：探针 ⇒ 标「探针 · ⛔ 业务」
        path, err = authz_trail(data_dir, row)
        row['留痕径'] = path
        row['留痕错'] = err
        return row

    def _decision_reuse(_did, _b16):
        u'''修②（一件一授权）：该 `decision_id` 是否**已授权他件**之真发（`果 = ok` ∧ 件散列 异）⇒ 返其行。'''
        if not _did:
            return None
        try:
            _p = _trail_path(data_dir)
            if not _p.exists():
                return None
            for _ln in open(_p, encoding='utf-8', errors='replace'):
                _ln = _ln.strip()
                if not _ln:
                    continue
                try:
                    _r2 = json.loads(_ln)
                except Exception:
                    continue
                if str(_r2.get('decision_id') or '') != str(_did):
                    continue
                if str(_r2.get('果') or '').strip().lower() != 'ok':   # ⭐ 唯**真发**消耗（干跑 ⛔ 消耗）
                    continue
                _h2 = str(_r2.get('件散列') or '')
                if _h2 and _h2 != str(_b16):
                    return _r2
            return None
        except Exception:
            return None

    def refuse(code, why, blocked_by, rec=None):
        doc = {'ok': False, 'error': why, 'blocked_by': blocked_by, 'policy': policy}
        if rec is not None:
            doc['receipt'] = rec
        if blocked_by != 'input':   # 补②：入参错 ⛔ 算「发信之意图」；自闸以降皆留痕
            _b16 = hashlib.sha256(_body_bytes(body)).hexdigest()[:16]
            doc['授权留痕'] = _trail('refused', rec, blocked_by, _b16)
        return code, doc

    miss = [k for k, v in (('task_id', task_id), ('to', to_list), ('subject', subject),
                           ('body_md', body)) if not v]
    if miss:
        return refuse(400, u'缺 %s' % u'、'.join(miss), 'input')
    if not user_id:
        return refuse(400, u'缺 user_id（谁的交办 · 承 069 §三.1）', 'input')

    idem = idem_key(task_id, to_list, body)
    prev = find_by_task(data_dir, task_id)
    if prev is not None:
        if prev.get('idem') != idem:
            return refuse(409, u'task_id 已用于**另一交办**（幂等键 ⛔ 同）⇒ 拒返错回执；新交办请换 task_id',
                          'idem', prev.get('receipt'))
        # ⭐ 重放之轴（承 PM 075 §三）：`policy` 取**本次请求**（⛔ 生效）；生效者 ＝ 存底 `receipt`
        policy['轴'] = u'本次请求（⛔ 生效）'
        policy['生效者'] = u'receipt'
        return 200, {'ok': True, 'replayed': True, 'delivered': True, 'idem_sha16': idem[:16],
                     'receipt': prev.get('receipt'), 'policy': policy}

    okg, whyg, dec = gate(data_dir, decision_id)
    if not okg:
        return refuse(403, whyg, 'decision_gate')

    if not face.get('ready'):
        rec = build_receipt(face, task_id, to_list, subject, body, ts, dec, 'none',
                            in_reply_to=_ir, stopped_at=u'凭据',
                            err=u'凭据未配（缺 %s）' % u'、'.join(k for k in ('CJ_MAIL_USER', 'CJ_MAIL_PASS')
                                                                 if not vals.get(k)))
        rec['落痕之缺'] = _trace(data_dir, 'fail', rec, task_id, decision_id, user_id,
                                to_list, subject, '', hashlib.sha256(_body_bytes(body)).hexdigest()[:16], vals)
        return refuse(502, u'凭据未配 ⇒ 停手（报给 %s）' % (policy['stop_to'] or u'（未配）'), 'credentials', rec)

    okto, bad = self_addressed_ok(to_list, vals)
    if not okto:
        return refuse(403, u'收件人不在白名单：%s ⇒ 对外须「乙形」（提醒 ＋ 转交 ＋ 人点 · ⛔ 代发第三方内容）'
                      % u'、'.join(bad), 'recipient_scope')

    if dry_run:
        rec = build_receipt(face, task_id, to_list, subject, body, ts, dec, 'dry-run', dry=True,
                            in_reply_to=_ir)
        _t = _trail('dry_run', rec, 'dry_run', body16=_b16_of(body))
        return 200, {'ok': True, 'replayed': False, 'delivered': False, 'dry_run': True,
                     'idem_sha16': idem[:16], 'receipt': rec, 'policy': policy, '授权留痕': _t,
                     'unchecked': [u'真发（SMTP）⛔ 未核 ⇒ 干跑不证送达（承 070 §一：3 ≠ 2）']}

    # ⭐ T2-刀26（PM 裁 · 修②「一件一授权」· PM 18:02 提级为「已发生之病」）：
    #   **一条「席决」只可授权一件真发** —— `decision_id` 与 `件散列` 绑；同决被他件用过 ⇒ 拒（fail-closed）。
    #   实据（PM 并账器 18:00）：`d1791172722880` 一决 4 件真发（t4／t5／t6／t10）· 跨 5 h 53 m。
    _reuse = _decision_reuse(decision_id, _b16_of(body))
    if _reuse is not None:
        return refuse(403, u'decision_id 已授权他件（一件一授权 ⇒ 同决 ⛔ 两件）：%s ⇒ 请取新拍板'
                      % (decision_id or u'缺'), 'decision_reuse')

    oks, stage, info = send_mail(face, vals, to_list, subject, body)
    b16 = hashlib.sha256(_body_bytes(body)).hexdigest()[:16]
    if not oks:
        rec = build_receipt(face, task_id, to_list, subject, body, ts, dec, 'smtp',
                            in_reply_to=_ir,
                            stopped_at=stage, err=info.get('error') or u'发送失败',
                            wall_s=info.get('wall_s'))
        rec['落痕之缺'] = _trace(data_dir, 'fail', rec, task_id, decision_id, user_id,
                                to_list, subject, '', b16, vals)
        return refuse(502, u'发送失败 ⇒ 停手（停在「%s」· 报给 %s）'
                      % (stage, policy['stop_to'] or u'（未配）'), 'send', rec)

    mid = info.get('message_id') or ''
    rec = build_receipt(face, task_id, to_list, subject, body, ts, dec, 'smtp', mid=mid,
                        in_reply_to=_ir,
                        wall_s=info.get('wall_s'), bytes_out=info.get('raw_bytes'))
    # ① 先落痕（events ＋ ledger · ⛔ 静默）② 回执**定形**（含 落痕之缺）③ 末落幂等行
    #   由：幂等行之返件须与首件**逐值同**（承 069 §三.7）⇒ 定形之刻须在落行**之前**。
    miss_trace = _trace(data_dir, 'ok', rec, task_id, decision_id, user_id,
                        to_list, subject, mid, b16, vals)
    if miss_trace:
        rec['落痕之缺'] = miss_trace
    row = {'task_id': task_id, 'idem': idem, 'ts': ts, 'user_id': user_id,
           'decision_id': decision_id, 'to': to_list, 'subject': subject,
           'message_id': mid, 'receipt': rec}
    try:
        record_receipt(data_dir, row)
    except Exception as e:
        _m = _redact(u'deliver_mail.json 写入失败：%s: %s' % (type(e).__name__, e), vals)[:200]
        rec['落痕之缺'] = ((rec.get('落痕之缺') or u'') + u' ／ ' + _m)[:300]
    _t = _trail('ok', rec, 'ok', b16)
    return 200, {'ok': True, 'replayed': False, 'delivered': True, 'idem_sha16': idem[:16],
                 'receipt': rec, 'policy': policy, '授权留痕': _t}


if __name__ == '__main__':
    import json
    import sys
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _face, _vals = cfg()
    print(json.dumps(_face, ensure_ascii=False, indent=1))
