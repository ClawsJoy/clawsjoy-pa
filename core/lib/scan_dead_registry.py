# -*- coding: utf-8 -*-
u"""死件账之器（登记之谎 · 唯读）：扫 *.yaml|*.yml 之 `path:` 逐条对盘 ⇒ 分档。

域定义（逐字 · 何谓一条「path: 项」）：
  ① 起于 --root（默 D:\\clawsjoy_v9）；剔 __pycache__ / .git / node_modules
  ② 件名以 .yaml ∨ .yml 结 ∧ ⛔ 以 .before_ 起（存底件非登记）
  ③ 行形 `^\\s*(?:-\\s*)?path\\s*:\\s*(.+?)\\s*$`（含 YAML 列表项 `- path:`）
  ④ 值剥引号后 ⛔ 得空 ∧ ⛔ 得 $ / { / < 起（模板占位）
  ⑤ 「镜像树」＝ relpath 起于 data/projects/ ∨ data/tmp/ ∨ _wt_clean/
     ⇒ ⛔ 计入（同件之副本 ⇒ 重复计数之床）

分档（何谓「谎」）：
  A 路由/URL 径（`^[a-z]+://` ∨ 起于 `/`）⇒ ⛔ 文件径 ⇒ ⛔ 谎
  B 绝对盘径（`^[A-Za-z]:`）⇒ 对盘
  C 运行时生成物（首段 ∈ data/logs/tmp/… ∨ 扩展 ∈ .db/.log/…）⇒ 正常缺
  D 真缺 —— 再分：
     D1 真缺件（值含 `/` ／ 值之扩展 ∈ 已知件之扩展 ⇒ 文件径之形）
     D2 非文件径（无 `/` ∧ ⛔ 已知件之扩展 ∧ 形如 `a.b.c` 之配置键径 ∨ 占位说明文）
     D3 目录径（值以 `/` 结）
  ⇒ ⭐ **「登记之谎」＝ D1**（登记在册之文件径 · 盘上无件）

rc：0 已扫且净（D1 == 0）｜2 有 D1（判红）｜3 用法/路径错｜4 闸未跑完（坏件 yaml > 0）｜5 无件可扫

⚠ 限（照实）：**按值之形判** ⇒ ⛔ 知「运行时可达」；「0 引用 ⛔ 即无调用」之族。
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, re, sys, time

SELF = os.path.abspath(__file__)
ROOT_DEFAULT = r'D:\clawsjoy_v9'
ALT_DEFAULT = r'D:\clawsjoy'
PAT = re.compile(r'^\s*(?:-\s*)?path\s*:\s*(.+?)\s*$')
SKIP_DIRS = {'__pycache__', '.git', 'node_modules'}
MIRROR_PREFIX = ('data/projects/', 'data/tmp/', '_wt_clean/')
GEN_TOP = {'data', 'logs', 'log', 'tmp', 'cache', '.cache', 'output', 'outputs',
           'media', 'uploads', 'run', 'runtime', 'backups', 'backup'}
GEN_EXT = ('.db', '.sqlite', '.sqlite3', '.log', '.pid', '.lock', '.tmp', '.bak')
FILE_EXT = ('.py', '.json', '.yaml', '.yml', '.csv', '.md', '.txt', '.js', '.ts', '.tsx',
            '.jsx', '.html', '.css', '.sh', '.ps1', '.cmd', '.bat', '.ini', '.cfg',
            '.toml', '.xml', '.sql')
KEY_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+$')
URL_RE = re.compile(r'^[A-Za-z][A-Za-z0-9+.\-]*://')
DRIVE_RE = re.compile(r'^[A-Za-z]:')


def sha16(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 16), b''):
            h.update(blk)
    return h.hexdigest()[:16]


def norm(v):
    return v.replace('\\', '/')


def classify(v):
    u"""值 ⇒ 档码（A/B/C/D1/D2/D3）。"""
    vv = norm(v)
    if URL_RE.match(vv) or (vv.startswith('/') and not DRIVE_RE.match(vv)):
        return 'A'
    if DRIVE_RE.match(vv):
        return 'B'
    body = vv.lstrip('./')
    if body.split('/')[0].lower() in GEN_TOP or vv.lower().endswith(GEN_EXT):
        return 'C'
    if vv.endswith('/'):
        return 'D3'
    if '/' in vv:
        return 'D1'
    if vv.lower().endswith(FILE_EXT):
        return 'D1'
    if KEY_RE.match(vv):
        return 'D2'
    return 'D2'


def resolve_cands(root, yaml_path, v):
    vv = norm(v)
    if DRIVE_RE.match(vv) or vv.startswith('/'):
        return [vv.replace('/', os.sep)]
    return [os.path.join(root, vv.replace('/', os.sep)),
            os.path.join(os.path.dirname(yaml_path), vv.replace('/', os.sep))]


def scan(root, alt=None):
    rows = []
    nfile = 0
    nmirror = 0
    bad = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for name in sorted(fn):
            if not name.endswith(('.yaml', '.yml')) or name.startswith('.before_'):
                continue
            p = os.path.join(dp, name)
            rp = os.path.relpath(p, root).replace(os.sep, '/')
            try:
                txt = io.open(p, encoding='utf-8-sig').read()
            except Exception as e:
                bad.append({'file': rp, 'err': '%s' % e})
                continue
            if rp.startswith(MIRROR_PREFIX):
                nmirror += 1
                continue
            nfile += 1
            for i, ln in enumerate(txt.splitlines(), 1):
                m = PAT.match(ln)
                if not m:
                    continue
                v = m.group(1).strip().strip('"').strip(chr(39))
                if (not v) or v.startswith(('$', '{', '<')):
                    continue
                rows.append((rp, i, v))
    recs = []
    for rp, i, v in rows:
        cands = resolve_cands(root, os.path.join(root, rp.replace('/', os.sep)), v)
        if any(os.path.exists(c) for c in cands):
            continue
        code = classify(v)
        rec = {'yaml': rp, 'line': i, 'value': v, '档': code}
        if alt:
            rec['别处有'] = any(os.path.exists(c) for c in resolve_cands(alt, os.path.join(alt, rp.replace('/', os.sep)), v))
        recs.append(rec)
    cnt = {}
    for r in recs:
        cnt[r['档']] = cnt.get(r['档'], 0) + 1
    c = lambda k: cnt.get(k, 0)
    d1 = [r for r in recs if r['档'] == 'D1']
    return {
        u'器': 'core/lib/scan_dead_registry.py',
        u'器印': sha16(SELF),
        u'域': {'root': root, 'alt': alt},
        u'取数刻': time.strftime('%Y-%m-%d %H:%M:%S'),
        u'件数': nfile,
        u'镜像树件数_剔': nmirror,
        u'path项数': len(rows),
        u'盘上无者数': len(recs),
        u'分档': {'A_路由URL径': c('A'), 'B_绝对盘径': c('B'), 'C_运行时生成物': c('C'),
                 'D1_真缺件': c('D1'), 'D2_非文件径': c('D2'), 'D3_目录径': c('D3')},
        u'真缺件数': len(d1),
        u'坏件': bad,
        u'真缺': d1,
        u'非文件径': [r for r in recs if r['档'] in ('D2', 'D3')],
        u'其余': [r for r in recs if r['档'] in ('A', 'B', 'C')],
    }


def rc_of(rep):
    if rep[u'坏件']:
        return 4
    if rep[u'件数'] == 0:
        return 5
    if rep[u'真缺件数'] > 0:
        return 2
    return 0


def show(rep):
    d = rep[u'分档']
    print(u'—— 器印 %s ｜ root %s' % (rep[u'器印'], rep[u'域'][u'root']))
    print(u'   yaml 件（活树） %d ｜ 镜像树件（已剔） %d ｜ path 项 %d ｜ 盘上无者 %d ｜ 坏件 %d'
          % (rep[u'件数'], rep[u'镜像树件数_剔'], rep[u'path项数'], rep[u'盘上无者数'], len(rep[u'坏件'])))
    print(u'   分档：A 路由URL %d ｜ B 绝对盘径 %d ｜ C 运行时生成物 %d ｜ ⭐D1 真缺件 %d ｜ D2 非文件径 %d ｜ D3 目录径 %d'
          % (d['A_路由URL径'], d['B_绝对盘径'], d['C_运行时生成物'], d['D1_真缺件'],
             d['D2_非文件径'], d['D3_目录径']))
    print(u'   ⭐「登记之谎」＝ D1 ＝ %d 件（按 yaml 分）：' % rep[u'真缺件数'])
    agg = {}
    for r in rep[u'真缺']:
        agg.setdefault(r['yaml'], []).append(r)
    for f, rs in sorted(agg.items(), key=lambda kv: -len(kv[1])):
        old = sum(1 for r in rs if r.get(u'别处有'))
        print(u'      %-52s %d 条%s' % (f, len(rs), u'（别处有 %d）' % old if old else ''))


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--root', default=ROOT_DEFAULT)
    ap.add_argument('--alt', default=ALT_DEFAULT)
    ap.add_argument('--no-alt', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    if not os.path.isdir(a.root):
        sys.stderr.write(u'rc=3 用法/路径错：root ⛔ 在 → %s\n' % a.root)
        return 3
    alt = None if a.no_alt else (a.alt if os.path.isdir(a.alt) else None)
    rep = scan(a.root, alt)
    if a.out:
        with io.open(a.out, 'w', encoding='utf-8', newline=chr(10)) as f:
            f.write(json.dumps(rep, ensure_ascii=False, indent=2) + chr(10))
    if a.json:
        sys.stdout.write(json.dumps(rep, ensure_ascii=False, indent=2) + chr(10))
    else:
        show(rep)
    return rc_of(rep)


if __name__ == '__main__':
    sys.exit(main())
