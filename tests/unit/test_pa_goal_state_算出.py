# -*- coding: utf-8 -*-
"""test_pa_goal_state_算出.py —— goal state 须由真源「算出」之齿（承 PM 2149 §三.2 · CEO 2148 §五.4）。

判据（一处定形）：state（层二之镜像）须由真源（件 ＋ 台账行）算出 —— ⛔ 手写 · ⛔ 反写。
  ⇒ 齿之形：给出一份 state ⇒ 以真源复算 ⇒ 逐字段比对 ⇒ 有一不符 ⇒ 咬（＝手写 ∨ 已陈旧）。
  ⚠ 一处出：算径与 PM 域 _pm/_立项state.py 同源（阶段之「当前」 ≡ 首个 到点 ≥ 今 之阶）。
  ⛔ 本齿不读活箱（件一归档即假红）⇒ 以中段之例（合成 3001）为真源之样。

正控：算出之 state 自比 ⇒ 差异 ＝ 0 ／ 当前阶段 ＝ ⒉清洗 ／ 红 ＝ 0。
反控（真咬）：手写「当前阶段」／「期」／「阶段表」／「红」⇒ 皆必咬；
              件缺「阶段」⇒ 算出之红 必含 缺栏:阶段（承 PM _立项state.py --selftest 之反控）。
  ⭐ 副本之锁版（承 PM 2160 §五 · 取 ⒝ 锁版）：本齿内嵌之「件文 ⇒ 阶段表」口径 ＝ PM 域
    `_pm/_立项state.py` 之**锁版副本**（PM 报印 `36580b90710b02b1` ／ 一手复算 `49e30fc5086e19df` ／
    取数刻 2026-10-09T07:06）。⛔ 随其漂：PM 升版 ⇒ 须同步此副本（免「各器自写口径」之族 · 承 CEO 2153 §六.2）。
用法：python -X utf8 -B tests/unit/test_pa_goal_state_算出.py --self-test
"""
import sys

六栏 = (u"立项", u"主", u"期", u"判据", u"阶段", u"结论")
今 = u"2026-10-09"

def 取值(件文, 栏):
    u"""件文 ⇒ 栏之值（无 ⇒ None）。口径同 PM _立项state.py（行首之「栏:」或「栏：」）。"""
    for ln in (件文 or u"").splitlines():
        st = ln.strip()
        for sep in (u":", u"："):
            p = 栏 + sep
            if st.startswith(p):
                v = st[len(p):].strip()
                if v:
                    return v
    return None

def 日期s(seg):
    u"""段 ⇒ 首个 YYYY-MM-DD（无 ⇒ None）。⛔ 用逐字扫（免正则之反斜杠）。"""
    for i in range(max(0, len(seg) - 9)):
        w = seg[i:i + 10]
        if w[4:5] == u"-" and w[7:8] == u"-" and (w[:4] + w[5:7] + w[8:]).isdigit():
            return w
    return None

def 阶段表(件文):
    u"""件文 ⇒ 阶段表（名 ／ 到点 ／ 应缴）。口径同 PM _立项state.py（｜ ／ | 分段）。"""
    txt = 取值(件文, u"阶段")
    if not txt:
        return []
    out = []
    for seg in txt.replace(u"|", u"｜").split(u"｜"):
        seg = seg.strip()
        if not seg:
            continue
        i = seg.find(u"到点")
        j = seg.find(u"应缴")
        out.append({u"名": (seg[:i] if i >= 0 else seg).strip(),
                    u"到点": 日期s(seg[i:] if i >= 0 else seg),
                    u"应缴": (seg[j + 2:].strip() if j >= 0 else None)})
    return out

def 算出(件文, 行, 今天):
    u"""真源（件 ＋ 台账行）⇒ state（⛔ 手写 · 与 PM _pm/_立项state.py 同源）。"""
    红 = [u"缺栏:" + k for k in 六栏 if 取值(件文, k) is None]
    阶 = 阶段表(件文)
    当 = None
    for x in 阶:
        if x[u"到点"] and x[u"到点"] >= 今天:
            当 = x
            break
    return {
        u"壹_头": {u"立项": 取值(件文, u"立项"), u"名": (行[4] if 行 and len(行) > 4 else None),
                   u"期": 取值(件文, u"期"), u"判据": 取值(件文, u"判据")},
        u"贰_阶段": 阶,
        u"续点": {u"当前阶段": (当 or {}).get(u"名"), u"下一步": (当 or {}).get(u"应缴"),
                  u"到点": (当 or {}).get(u"到点")},
        u"伍_收口": {u"结论": 取值(件文, u"结论")},
        u"红": 红,
    }

def 差异(手写, 件文, 行, 今天):
    u"""手写之 state ／ 真源 ⇒ 不符之表（空表 ＝ 算出 · 非手写）。"""
    真 = 算出(件文, 行, 今天)
    out = []

    def 比(径, a, b):
        if a != b:
            out.append(u"%s：手写=%r 但 算出=%r" % (径, a, b))

    比(u"壹_头.期", (手写.get(u"壹_头") or {}).get(u"期"), 真[u"壹_头"][u"期"])
    比(u"续点.当前阶段", (手写.get(u"续点") or {}).get(u"当前阶段"), 真[u"续点"][u"当前阶段"])
    比(u"续点.下一步", (手写.get(u"续点") or {}).get(u"下一步"), 真[u"续点"][u"下一步"])
    比(u"贰_阶段", 手写.get(u"贰_阶段"), 真[u"贰_阶段"])
    比(u"红", 手写.get(u"红"), 真[u"红"])
    return out

_件 = chr(10).join([
    u"---",
    u"type: 试",
    u"序号: 3001",
    u"类别: 试",
    u"status: open",
    u"立项: 3001",
    u"主: CodexWindows线（b2a5182）",
    u"期: 2026-10-12",
    u"判据: 四条（成 ∨ 废）",
    u"阶段: ⒈取料 到点 2026-10-08 应缴 料齐 ｜ ⒉清洗 到点 2026-10-09 应缴 净本 ｜ ⒊入 PA 到点 2026-10-12 应缴 一件入册",
    u"结论: 待收口",
    u"---",
    u"",
])
_行 = [u"3001", u"2026-10-09", u"技术总监", u"项目经理", u"_卡_TD_3001_中段例.md",
       u"试", u"open", u"", u"", u"", u"2026-10-09T06:00:00+08:00"]

def 缺阶段之件():
    件缺 = chr(10).join([ln for ln in _件.splitlines() if not ln.strip().startswith(u"阶段")])
    return 件缺

def test_正控_算出之state自比无差异():
    手写 = 算出(_件, _行, 今)
    assert 差异(手写, _件, _行, 今) == [], u"正控失败：算出之 state 自比应为 0 差异"

def test_正控_算出之三数():
    s = 算出(_件, _行, 今)
    assert len(s[u"贰_阶段"]) == 3
    assert s[u"续点"][u"当前阶段"] == u"⒉清洗", u"当前阶段 应为首个 到点 ≥ 今 之阶"
    assert s[u"红"] == [], u"真源之样六栏俱全 ⇒ 红 应为空"

def test_反控_手写当前阶段必咬():
    手 = 算出(_件, _行, 今)
    手[u"续点"][u"当前阶段"] = u"⒈取料"
    d = 差异(手, _件, _行, 今)
    assert d, u"反控未咬：手写之「当前阶段」应被检出"
    assert any(u"当前阶段" in x for x in d), u"咬处应点名 当前阶段：%s" % d

def test_反控_手写期与阶段表与红皆必咬():
    手 = 算出(_件, _行, 今)
    手[u"壹_头"][u"期"] = u"2026-10-13"
    手[u"贰_阶段"] = 手[u"贰_阶段"][:2]
    d = 差异(手, _件, _行, 今)
    assert any(u"期" in x for x in d), u"反控未咬：手写之「期」应被检出 ⇒ %s" % d
    assert any(u"贰_阶段" in x for x in d), u"反控未咬：手写之「阶段表」应被检出 ⇒ %s" % d

def test_反控_缺阶段之件算出即红():
    件缺 = 缺阶段之件()
    s = 算出(件缺, _行, 今)
    assert s[u"红"] == [u"缺栏:阶段"], u"缺阶段之件 ⇒ 红 应恰为 缺栏:阶段 ⇒ 实测 %s" % s[u"红"]
    手 = dict(s)
    手[u"红"] = []
    assert 差异(手, 件缺, _行, 今), u"反控未咬：手写之「红＝空」应被检出"

def self_test():
    u"""正控 ／ 反控 之数（承 PM 2149 §三.4）。"""
    正控 = 反控 = 0
    败 = []
    if 差异(算出(_件, _行, 今), _件, _行, 今) == []:
        正控 += 1
    else:
        败.append(u"正控1（自比无差异）")
    s = 算出(_件, _行, 今)
    if len(s[u"贰_阶段"]) == 3 and s[u"续点"][u"当前阶段"] == u"⒉清洗" and s[u"红"] == []:
        正控 += 1
    else:
        败.append(u"正控2（三数）")
    手 = 算出(_件, _行, 今)
    手[u"续点"][u"当前阶段"] = u"⒈取料"
    if any(u"当前阶段" in x for x in 差异(手, _件, _行, 今)):
        反控 += 1
    else:
        败.append(u"反控1（手写当前阶段）")
    手2 = 算出(_件, _行, 今)
    手2[u"壹_头"][u"期"] = u"2026-10-13"
    if any(u"期" in x for x in 差异(手2, _件, _行, 今)):
        反控 += 1
    else:
        败.append(u"反控2（手写期）")
    手3 = 算出(_件, _行, 今)
    手3[u"贰_阶段"] = 手3[u"贰_阶段"][:2]
    if any(u"贰_阶段" in x for x in 差异(手3, _件, _行, 今)):
        反控 += 1
    else:
        败.append(u"反控3（手写阶段表）")
    件缺 = 缺阶段之件()
    if 算出(件缺, _行, 今)[u"红"] == [u"缺栏:阶段"]:
        反控 += 1
    else:
        败.append(u"反控4（缺阶段 ⇒ 红）")
    手4 = dict(算出(件缺, _行, 今))
    手4[u"红"] = []
    if 差异(手4, 件缺, _行, 今):
        反控 += 1
    else:
        败.append(u"反控5（手写红）")
    print(u"[test_pa_goal_state_算出] 正控 %d ／ 反控 %d ／ %s"
          % (正控, 反控, u"全 PASS" if not 败 else u"败：%s" % 败))
    return 0 if not 败 else 2

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    print(u"用法：--self-test（本件由 pytest 收为齿 · 此为自证入口）")
    sys.exit(3)
