# -*- coding: utf-8 -*-
u'''「今日」行 3 之「开机」源（pm_1852 §四.4）—— 技术总监席 f202f89 · 2026-10-08。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_today_boot_1852.py -q

正控（事之实）：
  1. 造 inbox 二件 ⇒ 行 3 之「开机」源 读数跟（⛔ 硬编）∧ 件含二条「开机攒件」∧ 行 3 之数随真源；
  2. 该源之「径」＝ 真 inbox 之径（⛔ 硬编）∧ 末次账（攒件数 ／ 续办数）**照录**。

反控（器之牙）：
  3. 无台账 ⇒ 该源载「因」（含「未跑」）—— ⛔ 以 0 充「无攒件」；
  4. root_for_data_dir：合形（<root>/data/v9/pa）⇒ 仓根；⛔ 合形 ⇒ None（⛔ 猜）。

⚠ 本件唯触「轻读」之源 —— 信通未读须起进程 ⇒ 唯 GET /v9/pa/resume 走（本件 ⛔ 涉）。
'''
import json
import os
from pathlib import Path

import pytest
from flask import Flask

from core.pa.gateway_routes import register_pa_routes


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('PA_DATA_DIR', str(tmp_path / 'pa'))
    app = Flask(__name__)
    register_pa_routes(app)
    return app.test_client()


def _row3(js):
    return [r for r in js[u'行'] if r[u'序'] == 3][0]


def _boot_src(js):
    src = [s for s in _row3(js)[u'源'] if u'resume' in str(s.get(u'面') or '')]
    assert len(src) == 1, _row3(js)[u'源']
    return src[0]


def _pa_dir():
    return Path(os.environ['PA_DATA_DIR'])


def test_boot_source_follows_true_source(client):
    u'''正控：inbox 之件 ⇒ 该源 读数跟 ∧ 件含之 ∧ 行 3 之数随真源（⛔ 硬编）。'''
    before = _row3(client.get('/v9/pa/today').get_json())[u'数']
    ib = _pa_dir() / 'inbox'
    ib.mkdir(parents=True, exist_ok=True)
    (ib / 'a.txt').write_text(u'甲', encoding='utf-8')
    (ib / 'b.txt').write_text(u'乙', encoding='utf-8')
    (_pa_dir() / 'boot_log.jsonl').write_text(
        json.dumps({'boot_at': '2026-10-08 04:00:00', 'gathered': 2, 'resumed': 1,
                    'failed': []}, ensure_ascii=False) + '\n', encoding='utf-8')

    js = client.get('/v9/pa/today').get_json()
    r3 = _row3(js)
    s = _boot_src(js)
    assert s[u'读数'] == 2, s
    assert s[u'末次开机'] == '2026-10-08 04:00:00', s
    assert s[u'攒件数_末次账'] == 2 and s[u'续办数_末次账'] == 1, s
    assert os.path.normcase(str(ib)) == os.path.normcase(str(s[u'径'])), s
    assert u'因' not in s, u'跑过 ⇒ ⛔ 载「未跑」之因'
    boot_items = [i for i in r3[u'件'] if i.get(u'类') == u'开机攒件']
    assert sorted(i[u'id'] for i in boot_items) == ['a.txt', 'b.txt'], boot_items
    assert r3[u'数'] == before + 2, u'行 3 之数须随真源（⛔ 硬编）'


def test_boot_source_unrun_is_loud_not_zero(client):
    u'''反控：无台账 ⇒ 该源载「因」（未跑）—— ⛔ 静默以 0 充「无攒件」。'''
    (_pa_dir() / 'inbox').mkdir(parents=True, exist_ok=True)
    s = _boot_src(client.get('/v9/pa/today').get_json())
    assert s.get(u'因') and u'未跑' in s[u'因'], s


def test_boot_source_broken_dir_is_fail_loud(client, monkeypatch):
    u'''反控：读源忽炸 ⇒ 该源 读数 = None ＋ 因（⛔ 以 0 充「没有」—— 承「空 ⛔ 混 缺」）。'''
    from core.pa import resume_face as RF

    def _boom(root=None):
        raise RuntimeError(u'探针：源坏')

    monkeypatch.setattr(RF, 'boot_summary', _boom)
    s = _boot_src(client.get('/v9/pa/today').get_json())
    assert s[u'读数'] is None and u'探针' in (s.get(u'因') or ''), s


def test_root_for_data_dir():
    u'''root_for_data_dir：合形 ⇒ 仓根；⛔ 合形 ／ 空 ⇒ None（⛔ 猜）。'''
    from core.pa import resume_face as RF

    assert RF.root_for_data_dir('D:/x/data/v9/pa') == 'D:' + os.sep + 'x'
    assert RF.root_for_data_dir(os.path.join('D:', os.sep, 'x', 'data', 'v9', 'pa')) == 'D:' + os.sep + 'x'
    assert RF.root_for_data_dir(os.path.join('D:', os.sep, 'x', 'pa')) is None
    assert RF.root_for_data_dir('') is None
    assert RF.root_for_data_dir(None) is None
