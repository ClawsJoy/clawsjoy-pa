# -*- coding: utf-8 -*-
u'''「今日」四行 ＋ 账本逐条撤回（pm_1824 §二）—— 技术总监席 f202f89 · 2026-10-08。

正控（事之实）：
  1. 四行之形（序 ／ 名 ／ 数 ／ 源 ／ 去处 ／ 空态）—— 照《「今日」一屏之定义 v1》；
  2. 数**随真源**（造件 ⇒ 数跟）—— ⛔ 硬编；
  3. 空之时**人话**（照定义页之逐字）—— ⛔ 自曝之辞；
  4. 撤回：一件一撤 ＋ 留痕 ＋ 可查（⛔ 删行）。

反控（器之牙）：
  5. 源坏 ⇒ 读数 = None（**⛔ 以 0 充「没有」** —— 承「空 ⛔ 混 缺」）；
  6. 撤不存在之件 ⇒ 404（⛔ 假装已撤）。
'''
import json
import os
import sys

sys.path.insert(0, '.')
import pytest
from flask import Flask

from core.pa.gateway_routes import register_pa_routes

# 定义页 §二 之四行（逐字 · 序不可易）
_ROWS = [u'要我拍的', u'今天该做的', u'在等的', u'近来之痕']
# 定义页 §四.3：⛔ 自曝之辞 —— 空态人话里一个都不许有
_SELF_EXPOSE = [u'未接', u'尚无后端读数', u'这个还没接上', u'暂无']


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('PA_DATA_DIR', str(tmp_path / 'pa'))
    app = Flask(__name__)
    register_pa_routes(app)
    return app.test_client()


def test_today_four_rows_shape(client):
    d = client.get('/v9/pa/today').get_json()
    assert d['ok'] is True
    rows = d[u'行']
    assert [r[u'序'] for r in rows] == [1, 2, 3, 4]
    assert [r[u'行'] for r in rows] == _ROWS
    for r in rows:
        assert isinstance(r[u'数'], int) and r[u'数'] >= 0
        assert r[u'源'], u'每行须有源'
        assert r[u'去处'], u'缺「去处」＝ 未做完（定义页 §三）'
        assert r[u'空态'], u'空态须人话'
        for _w in _SELF_EXPOSE:
            assert _w not in r[u'空态'], u'空态 ⛔ 自曝之辞：%s' % _w


def test_today_empty_state_is_human(client):
    u'''空库 ⇒ 四行之数皆 0 且空态为定义页之逐字（⛔ 编数 · ⛔ 「暂无」之属）。'''
    rows = client.get('/v9/pa/today').get_json()[u'行']
    todo = [r for r in rows if r[u'序'] == 2][0]
    assert todo[u'数'] == 0
    assert todo[u'空态'] == u'今天没有非做不可的'


def test_today_counts_follow_true_source(client):
    u'''数须**随真源**：造二待办 ＋ 一待裁画像 ⇒ 第 2 ／ 第 1 行之数跟。'''
    for _t in (u'今日真源甲', u'今日真源乙'):
        assert client.post('/v9/pa/ledger/add', json={'title': _t}).get_json()['ok']
    assert client.post('/v9/pa/sediment',
                       json={'domain': 'style', 'value': u'待裁之探针',
                             'source': 'test', 'status': 'proposed'}).get_json()['ok']

    rows = client.get('/v9/pa/today').get_json()[u'行']
    todo, auth = rows[1], rows[0]
    # 真源之尺（经公开口取）
    _open = client.get('/v9/pa/ledger').get_json()['open']
    assert todo[u'数'] == len(_open) == 2
    # 第 1 行须含该「待裁」条（画像 proposed 之数由 context 同源）
    _prop = client.get('/v9/pa/context').get_json()['proposed']
    assert len(_prop) == 1
    assert any(i.get(u'类') == u'画像待裁' for i in auth[u'件'])
    assert auth[u'数'] >= len(_prop)


def test_today_reports_judgment_home(client):
    u'''四类之判据须**唯在一处**（⛔ 前端各判 —— 承 pm_1824 §二.1）：面须自报判据之在。'''
    d = client.get('/v9/pa/today').get_json()
    assert 'core/pa/today.py' in d[u'判据之在']
    assert d['at'] and d[u'刻之性']


def test_source_broken_is_fail_loud_not_zero(client, tmp_path, monkeypatch):
    u'''反控：账本坏 ⇒ **fail-loud 409**（⛔ 返 200 载「四行 数=0」）。

    由（承「空 ⛔ 混 缺」）：账本读不动 ≈ 账本为空 ＝ **误报「今天没有非做不可的」**
      ⇒ 宁可整屏报坏（可查 `path` ／ `reason`），⛔ 以 0 充「没有」。
    '''
    _d = tmp_path / 'pa'
    _d.mkdir(parents=True, exist_ok=True)
    (_d / 'ledger.json').write_text('{ not json', encoding='utf-8')
    r = client.get('/v9/pa/today')
    assert r.status_code == 409, u'坏状态须 fail-loud'
    j = r.get_json()
    assert j['ok'] is False and j['error'] == 'pa_state_corrupt'
    assert j.get('path'), u'须载坏件之路（可查）'
    assert u'行' not in j, u'⛔ 半屏（返空四行 ＝ 假装「没有」）'


def test_ledger_revoke_marks_and_traces(client):
    u'''一件一撤：落 cancelled ＋ 刻 ／ 因；行**仍在**（可查 · ⛔ 删行）；open 里**去**。'''
    _id = client.post('/v9/pa/ledger/add', json={'title': u'待撤之件'}).get_json()['item']['id']
    r = client.post('/v9/pa/ledger/revoke', json={'id': _id, 'reason': u'不需要了'})
    assert r.status_code == 200 and r.get_json()['ok']
    _it = r.get_json()['item']
    assert _it[u'status'] == 'cancelled' and _it.get(u'revoked_at')
    assert _it.get(u'revoke_reason') == u'不需要了'
    # 可查：仍在 items 里（⛔ 删行）
    _all = client.get('/v9/pa/ledger').get_json()['items']
    assert any(i['id'] == _id for i in _all)
    # 未结里**去**
    assert all(i['id'] != _id for i in client.get('/v9/pa/ledger').get_json()['open'])
    # 面随之（第 2 行之数不增）
    assert client.get('/v9/pa/today').get_json()[u'行'][1][u'数'] == 0


def test_ledger_revoke_unknown_is_404(client):
    u'''反控：撤不存在之件 ⇒ 404（⛔ 返 ok:true 假装已撤 —— 承「空 ⛔ 混 缺」）。'''
    r = client.post('/v9/pa/ledger/revoke', json={'id': 't999'})
    assert r.status_code == 404 and r.get_json()['ok'] is False


def test_ledger_revoke_needs_id(client):
    assert client.post('/v9/pa/ledger/revoke', json={}).status_code == 400
