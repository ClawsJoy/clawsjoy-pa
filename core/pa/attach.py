# -*- coding: utf-8 -*-
u'''附件之本机端（pm_1852 §四.3 ／ 准形 ＝ pm_1847 §三）—— 技术总监席 f202f89 · 2026-10-08。

【本件之职】聊天之附件：**上传落本机** ＋ 模型侧**唯取抽取之文**（有界）。
  · 落点：`<data_dir>/attach/<刻>/<名>`（**唯本机** · ⛔ 出机）；
  · 类：`文`（`.txt .md .log .json` —— 可抽取 · **有界**）／ `图` ／ `档`（余者）；
  · ⛔ 出机（缺省）：模型侧 **⛔ 收任何内容** ⇒ 唯「**本机指路**」（名 ＋ 类 ＋ 字节 ＋ sha16 ＋ 落点）；
    须**逐件勾**（`出机`）方入体 ∧ 图 ／ 档 **恒 ⛔ 入体**（承「图 ／ 二进件唯本机指路」）；
  · 一处定形：判据（何者可出 ／ 抽取之上限 ／ 名之净）**唯在此一处**（⛔ 各调用点各判）。

【形】件之录：`{id, 名, 字节, sha16, 类, 落点, 出机}` ——
  `id` ＝ `<刻>/<名>`（**相对之径** · ⛔ 绝对径）⇒ 可回解（`resolve`）；重名 ⇒ `-2` ／ `-3`。
'''
import hashlib
import os
import time
from pathlib import Path

# 抽取之上限（有界 —— 承「模型侧唯取抽取之文 · 有界」）
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_EXTRACT_CHARS = 4000
MAX_FILES = 20

TEXT_EXT = ('.txt', '.md', '.log', '.json')
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')

KIND_TEXT = u'文'
KIND_IMAGE = u'图'
KIND_OTHER = u'档'

# Windows 文件名之非法字符（⛔ 同族之坑：目录名之刻亦须避 `:` —— 见 `_stamp`）
_BAD = '<>:"|?*'


def _sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def _stamp(now=None):
    u'''目录名之刻 —— **文件系统安全**（`:` 在 Windows 为非法 ⇒ `makedirs` 抛 OSError）。'''
    return time.strftime('%Y%m%d-%H%M%S', time.localtime(time.time() if now is None else float(now)))


def attach_root(data_dir):
    return Path(str(data_dir or os.getenv('PA_DATA_DIR', 'data/v9/pa'))) / 'attach'


def kind_of(name):
    u'''类之判 —— **唯此一处**（`文` ／ `图` ／ `档`）。'''
    e = os.path.splitext(str(name or ''))[1].lower()
    if e in TEXT_EXT:
        return KIND_TEXT
    if e in IMAGE_EXT:
        return KIND_IMAGE
    return KIND_OTHER


def safe_name(name):
    u'''名之净（唯取 `basename` ＋ 去非法 ＋ ⛔ 空 ⇒ `未名`）—— 一处定形（⛔ 越界之径）。'''
    s = str(name or '').replace('\\', '/').split('/')[-1].strip()
    s = ''.join(c for c in s if c not in _BAD and ord(c) >= 32)
    s = s.rstrip(' .')
    return s or '未名'


def _rel(data_dir, p):
    u'''落点之人话形（正斜杠）—— 生产之 `data_dir` ＝ `data/v9/pa` ⇒
    `data/v9/pa/attach/<刻>/<名>`（**承规格之逐字**）；⛔ 另造前缀。
    '''
    return str(p).replace(os.sep, '/')


# ------------------------------ 上传落本机 ------------------------------
def save(data_dir, items, now=None):
    u'''上传件落本机（**唯本机** · ⛔ 出机）⇒ `{ok, 附件:[录], 落点, 数, 略}`。

    `items` ＝ `[(名, 字节)]`；单件逾 `MAX_FILE_BYTES` ∧ 逾 `MAX_FILES` ⇒ **略**（照实载因 · ⛔ 静默弃）。
    '''
    stamp = _stamp(now)
    d = attach_root(data_dir) / stamp
    recs, skipped = [], []
    for i, item in enumerate(list(items or [])):
        name, blob = (list(item) + ['', b''])[:2]
        if i >= MAX_FILES:
            skipped.append({'名': safe_name(name), '因': u'逾一次 %d 件之限 ⇒ 略' % MAX_FILES})
            continue
        blob = bytes(blob or b'')
        if len(blob) > MAX_FILE_BYTES:
            skipped.append({'名': safe_name(name),
                            '因': u'逾 %d 字节之限（%d）⇒ 略' % (MAX_FILE_BYTES, len(blob))})
            continue
        nm = safe_name(name)
        base, ext = os.path.splitext(nm)
        rid, n = nm, 1
        while (d / rid).exists():
            n += 1
            rid = '%s-%d%s' % (base, n, ext)
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / rid).write_bytes(blob)
        except Exception as e:
            skipped.append({'名': nm, '因': u'落盘失败（%s）' % type(e).__name__})
            continue
        recs.append({'id': '%s/%s' % (stamp, rid), '名': rid, '字节': len(blob),
                     'sha16': _sha16(blob), '类': kind_of(rid), '落点': _rel(data_dir, d / rid)})
    return {'ok': True, '附件': recs, '略': skipped, '数': len(recs),
            '落点': _rel(data_dir, d), '唯本机': True,
            '明书': u'⛔ 出机（缺省）：模型侧**唯收指路**；须**逐件勾**（`attach_out`）且类为「文」方入体'}


# ------------------------------ 回解（⛔ 越界） ------------------------------
def _path_of(data_dir, aid):
    u'''`id` ⇒ 本机之径（**⛔ 越界**：绝对 ／ `..` ／ 盘符 ⇒ 拒）—— 一处定形。'''
    s = str(aid or '').replace('\\', '/').strip()
    if not s or s.startswith('/') or ':' in s:
        return None, u'⛔ id 非法（须为 `<刻>/<名>` 之相对径）'
    root = attach_root(data_dir)
    p = Path(os.path.normpath(str(root / s)))
    try:
        rp, rr = str(p.resolve()), str(root.resolve())
    except Exception:
        return None, u'⛔ id 不可解'
    if rp != rr and not rp.startswith(rr + os.sep):
        return None, u'⛔ 越界之径 ⇒ 拒'
    return p, ''


def resolve(data_dir, aid):
    u'''`id` ⇒ **件之录**（照实之字节 ＋ sha16 ＋ 类 ＋ 落点）∨ `(None, 因)`。'''
    p, why = _path_of(data_dir, aid)
    if p is None:
        return None, why
    try:
        sz = p.stat().st_size
    except Exception:
        return None, u'查不到该件'
    if not p.is_file():
        return None, u'查不到该件'
    if sz > MAX_FILE_BYTES:
        return None, u'逾 %d 字节之限 ⇒ ⛔ 回解' % MAX_FILE_BYTES
    b = p.read_bytes()
    return {'id': str(aid).replace('\\', '/'), '名': p.name, '字节': len(b), 'sha16': _sha16(b),
            '类': kind_of(p.name), '落点': _rel(data_dir, p)}, ''


def extract(data_dir, aid, cap=MAX_EXTRACT_CHARS):
    u'''抽取之文（唯 `文` 类 · **有界**）⇒ `(文 ∨ None, 截断, 因)`。'''
    rec, why = resolve(data_dir, aid)
    if rec is None:
        return None, False, why
    if rec['类'] != KIND_TEXT:
        return None, False, u'类非「文」（%s）⇒ ⛔ 抽取（唯本机指路：%s）' % (rec['类'], rec['落点'])
    p, _w = _path_of(data_dir, aid)
    raw = p.read_bytes()
    try:
        txt = raw.decode('utf-8-sig')
    except Exception:
        txt = raw.decode('utf-8', 'replace')
    lim = max(int(cap), 0)
    return txt[:lim], (len(txt) > lim), ''


# ------------------------------ 模型侧之块（一处定形） ------------------------------
def model_block(data_dir, ids, out_ids=None, cap=MAX_EXTRACT_CHARS):
    u'''模型侧之块：**唯**「文」且**逐件已勾**者入体；余者唯**本机指路** ⇒ `{块, 载, 略, 明书}`。

    ⚠ 「入体」＝ 抽取之文入 context（⛔ 原字节）∧ 图 ／ 档 **恒 ⛔ 入体** ∧ 未勾者 ⛔ 入体。
    '''
    allow = set(str(x) for x in (out_ids or []))
    biao, zai, lue, texts = [], [], [], []
    for aid in list(ids or [])[:MAX_FILES]:
        rec, why = resolve(data_dir, aid)
        if rec is None:
            lue.append({'id': str(aid), '因': why})
            continue
        if rec['类'] != KIND_TEXT:
            r2 = dict(rec); r2['因'] = u'类非「文」⇒ ⛔ 入体（唯本机指路）'
            lue.append(r2)
            continue
        if str(aid) not in allow:
            r2 = dict(rec); r2['因'] = u'⛔ 未勾「出机」⇒ ⛔ 入体（唯本机指路）'
            lue.append(r2)
            continue
        txt, cut, why2 = extract(data_dir, aid, cap=cap)
        if txt is None:
            r2 = dict(rec); r2['因'] = why2
            lue.append(r2)
            continue
        row = dict(rec); row['抽取字数'] = len(txt); row['截断'] = bool(cut)
        zai.append(row); texts.append((rec['名'], txt))
        biao.append(u'- %s（%s · %d 字节 · sha16=%s · 落点 %s）—— **已入体**（抽取 %d 字%s）'
                    % (rec['名'], rec['类'], rec['字节'], rec['sha16'], rec['落点'], len(txt),
                       u' · 已截断' if cut else ''))
    for rec in lue:
        biao.append(u'- %s（%s · %s · 落点 %s）—— ⛔ 入体（%s）'
                    % (rec.get('名') or rec.get('id'), rec.get('类') or u'?', rec.get('字节'),
                       rec.get('落点') or u'—', rec.get('因')))
    parts = []
    if biao:
        parts.append(u'【附件（本机）】逐件：\n' + '\n'.join(biao))
    if texts:
        parts.append(u'【附件正文（唯经逐件勾者）】\n' + '\n\n'.join(u'<<%s>>\n%s' % (n, t) for n, t in texts))
    return {'块': '\n\n'.join(parts), '载': zai, '略': lue,
            '明书': (u'附件 %d 件：入体 %d 件（皆「文」且**逐件已勾**）／ 未入体 %d 件'
                    u'（图 ／ 档恒 ⛔ 入体 · 未勾者 ⛔ 入体）') % (len(zai) + len(lue), len(zai), len(lue)),
            '出机之律': u'缺省 ⛔ 出机（唯本机指路）；逐件勾 `attach_out` 方入体；图 ／ 档恒 ⛔ 入体'}
