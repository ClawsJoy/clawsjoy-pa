# -*- coding: utf-8 -*-
u'''附件之本机端（pm_1852 §四.3 ／ 准形 ＝ pm_1847 §三）—— 技术总监席 f202f89 · 2026-10-08。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_attach_1852.py -q

正控（事之实）：
  1. 上传 ⇒ 落**本机**（`<data_dir>/attach/<刻>/<名>`）∧ 录六件齐 ∧ 落点合规格之形（⛔ 硬编）；
  2. 抽取：`文` 可抽（**有界** · 逾限截断）；`图` ／ `档` ⛔ 抽；
  3. 聊天体 `attachments:[id]`：**逐件勾**（`attach_out`）者入体（脑之 context 载其文）∧ 未勾者 ⛔ 入体 ∧ 明书载数。

反控（器之牙）：
  4. ⛔ 越界之 id（`../` ／ 绝对 ／ 盘符）⇒ 拒（⛔ 读到盘外）；
  5. 远机 ⇒ 403 ∧ 无件 ⇒ 400（⛔ 静默兜底）；
  6. 逾限之件 ⇒ **略** ＋ 因（⛔ 静默吞 —— 承「空 ⛔ 混 缺」）。
'''
import io
import os
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pa import attach as A  # noqa: E402
from core.pa.gateway_routes import register_pa_routes  # noqa: E402


class _App:
    u'''一个 app ＋ 捕脑（留 context 之实）—— 供聊天体之证。'''

    def __init__(self):
        self.seen = {}

    def brain(self, ctx):
        self.seen['ctx'] = ctx
        return u'好'


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv('PA_DATA_DIR', str(tmp_path / 'pa'))
    a = _App()
    app = Flask(__name__)
    register_pa_routes(app, brain=a.brain)
    a.client = app.test_client()
    a.data_dir = str(tmp_path / 'pa')
    return a


def _up(env, name, blob, **kw):
    if not isinstance(blob, bytes):
        blob = blob.encode('utf-8')
    return env.client.post('/v9/pa/attach',
                           data={'files': (io.BytesIO(blob), name)},
                           content_type='multipart/form-data', **kw)


# ---------------------------------------------------------------- 1 落本机 ＋ 形
def test_upload_lands_local_and_shape(env):
    r = _up(env, 'a.txt', u'你好'.encode('utf-8'))
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    j = r.get_json()
    assert j['ok'] is True and j[u'数'] == 1 and j[u'唯本机'] is True
    rec = j[u'附件'][0]
    for k in (u'id', u'名', u'字节', u'sha16', u'类', u'落点'):
        assert rec.get(k) not in (None, ''), (k, rec)
    assert rec[u'名'] == 'a.txt' and rec[u'类'] == u'文'
    assert rec[u'字节'] == len(u'你好'.encode('utf-8'))
    _stamp = rec[u'id'].split('/')[0]
    _place = rec[u'落点'].replace('\\', '/')
    assert _place == '%s/attach/%s/a.txt' % (env.data_dir.replace('\\', '/'), _stamp), _place
    assert rec[u'id'] == '%s/a.txt' % rec[u'id'].split('/')[0]
    p = Path(env.data_dir) / 'attach' / rec[u'id']
    assert p.is_file(), u'须**真落盘**（⛔ 只报不落）'
    assert p.read_bytes() == u'你好'.encode('utf-8')
    assert j[u'明书'] and u'出机' in j[u'明书']


# ---------------------------------------------------------------- 2 抽取（有界）
def test_extract_text_bounded(env):
    r = _up(env, 'n.md', u'甲' * 100)
    aid = r.get_json()[u'附件'][0][u'id']
    txt, cut, why = A.extract(env.data_dir, aid, cap=10)
    assert txt == u'甲' * 10 and cut is True, (txt, cut, why)
    txt2, cut2, _w = A.extract(env.data_dir, aid)
    assert txt2 == u'甲' * 100 and cut2 is False


def test_image_never_extracted(env):
    r = _up(env, 'p.png', b'\x89PNG\r\n' + b'x' * 8)
    rec = r.get_json()[u'附件'][0]
    assert rec[u'类'] == u'图'
    txt, cut, why = A.extract(env.data_dir, rec[u'id'])
    assert txt is None and u'文' in why, (txt, why)


# ---------------------------------------------------------------- 3 聊天体之接
def test_dialog_attachment_needs_per_file_check(env):
    aid = _up(env, 'see.txt', u'暗号甲').get_json()[u'附件'][0][u'id']
    # (a) ⛔ 未勾 ⇒ ⛔ 入体（唯本机指路）
    r1 = env.client.post('/v9/pa/dialog', json={'text': u'看附件', 'attachments': [aid]})
    assert r1.status_code == 200, r1.get_data(as_text=True)[:300]
    ctx1 = env.seen['ctx']
    assert u'暗号甲' not in ctx1, u'缺省 ⛔ 出机 ⇒ 内容 ⛔ 入体'
    assert aid.split('/')[-1] in ctx1, u'须留**本机指路**（名）'
    j1 = r1.get_json()
    assert j1[u'附件'][u'载'] == [] and len(j1[u'附件'][u'略']) == 1
    # (b) 逐件勾 ⇒ 入体
    r2 = env.client.post('/v9/pa/dialog',
                         json={'text': u'看附件', 'attachments': [aid], 'attach_out': [aid]})
    ctx2 = env.seen['ctx']
    assert u'暗号甲' in ctx2, u'勾者须入体'
    j2 = r2.get_json()
    assert len(j2[u'附件'][u'载']) == 1 and j2[u'附件'][u'略'] == []
    assert u'逐件' in j2[u'附件'][u'明书']


def test_dialog_image_stays_local_even_if_checked(env):
    aid = _up(env, 'p.png', b'\x89PNG\r\n' + b'z' * 8).get_json()[u'附件'][0][u'id']
    r = env.client.post('/v9/pa/dialog',
                       json={'text': u'看图', 'attachments': [aid], 'attach_out': [aid]})
    j = r.get_json()
    assert j[u'附件'][u'载'] == [], u'图 **恒** ⛔ 入体（勾亦 ⛔）'
    assert len(j[u'附件'][u'略']) == 1


# ---------------------------------------------------------------- 4 ⛔ 越界
def test_resolve_rejects_traversal(env):
    for bad in (u'../x.txt', u'..\\x.txt', u'C:/Windows/win.ini', u'/etc/passwd', u''):
        rec, why = A.resolve(env.data_dir, bad)
        assert rec is None and why, bad


# ---------------------------------------------------------------- 5 远机 ／ 无件
def test_remote_is_403(env):
    r = _up(env, 'a.txt', b'x', environ_base={'REMOTE_ADDR': '10.0.0.5'})
    assert r.status_code == 403, r.status_code


def test_no_files_is_400(env):
    r = env.client.post('/v9/pa/attach', data={}, content_type='multipart/form-data')
    assert r.status_code == 400, r.status_code


# ---------------------------------------------------------------- 6 逾限 ⇒ 略
def test_oversize_is_skipped_with_reason(env, monkeypatch):
    monkeypatch.setattr(A, 'MAX_FILE_BYTES', 4)
    j = _up(env, 'big.txt', b'x' * 40).get_json()
    assert j[u'附件'] == [] and j[u'数'] == 0
    assert len(j[u'略']) == 1 and u'逾' in j[u'略'][0][u'因'], j[u'略']


def test_duplicate_names_get_suffix(env):
    a = _up(env, 'a.txt', b'1').get_json()[u'附件'][0][u'名']
    b = _up(env, 'a.txt', b'2').get_json()[u'附件'][0][u'名']
    assert a == 'a.txt' and b == 'a-2.txt', (a, b)
