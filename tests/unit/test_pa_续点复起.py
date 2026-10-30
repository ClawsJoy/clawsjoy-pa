# -*- coding: utf-8 -*-
"""test_pa_续点复起.py —— 续点「可复起」之齿（承 PM 2149 §三.3 · 源 PM _续点复起之试_v1 之 §一 ／ §五）。

判据（一处定形）：换席不断 ⇒ 唯给「载入之最小集」（台账行 ＋ 件 ＋ 续点段）⇒ 四事实必可复起：
  当前阶段 ／ 动作 ／ 候谁 ／ 到点（逐字）。且续点之「下一步」须为五元俱全：
  动作 ＋ 器 ＋ 命令 ＋ 应缴 ＋ 到点（缺一 ⇒ 悬空 ⇒ 红）。

⭐ 齿律（PM 一手之逮 · 本齿之要）：复起之齿须用「中段之例」（件 ⛔ 载进度）——
   由：首阶段之例 ⛔ 具判别力（件自足 ⇒ 抽掉续点段亦命中 ⇒ 反控不咬 ⇒ 齿盲）。
   ⇒ 故本齿把「判别力」也算一物，且**首阶段例须被标为不具判别力**（防齿盲）。

正控：中段例 ＋ 续点段 ⇒ 四事实逐字命中 ／ 五元俱全。
反控（真咬）：中段例 ⛔ 续点段 ⇒ 落错（证续点段之增值）；五元逐一抽掉 ⇒ 必点名（五咬）；
              首阶段例 ⛔ 续点段 ⇒ 仍命中 ⇒ 必被标「不具判别力」。
  ⭐ 副本之锁版（承 PM 2160 §五 · 取 ⒝ 锁版）：本齿内嵌之「件文 ⇒ 阶段表」口径 ＝ PM 域
    `_pm/_立项state.py` 之**锁版副本**（PM 报印 `36580b90710b02b1` ／ 一手复算 `49e30fc5086e19df` ／
    取数刻 2026-10-09T07:06）。⛔ 随其漂：PM 升版 ⇒ 须同步此副本（免「各器自写口径」之族 · 承 CEO 2153 §六.2）。
用法：python -X utf8 -B tests/unit/test_pa_续点复起.py --self-test
"""
import sys

四事实 = (u"当前阶段", u"动作", u"候谁", u"到点")
五元 = (u"动作", u"器", u"命令", u"应缴", u"到点")

def 取值(件文, 栏):
    u"""件文 ⇒ 栏之值（无 ⇒ None）。口径同 PM _立项state.py。"""
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
    u"""段 ⇒ 首个 YYYY-MM-DD（无 ⇒ None）。⛔ 逐字扫（免正则之反斜杠）。"""
    for i in range(max(0, len(seg) - 9)):
        w = seg[i:i + 10]
        if w[4:5] == u"-" and w[7:8] == u"-" and (w[:4] + w[5:7] + w[8:]).isdigit():
            return w
    return None

def 阶段表(件文):
    u"""件文 ⇒ 阶段表（名 ／ 到点 ／ 应缴）。口径同 PM _pm/_立项state.py。"""
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

def 凭件(件文, 今天):
    u"""唯凭件（层一之真源）⇒ 四事实之试答。口径：首个 到点 ≥ 今 之阶」为当前。"""
    当 = None
    for x in 阶段表(件文):
        if x[u"到点"] and x[u"到点"] >= 今天:
            当 = x
            break
    return {u"当前阶段": (当 or {}).get(u"名"), u"动作": (当 or {}).get(u"应缴"),
            u"候谁": 取值(件文, u"主"), u"到点": (当 or {}).get(u"到点")}

def 复起(件文, 续点段, 今天):
    u"""最小集（件 ＋ 续点段）⇒ 四事实。续点段为 None ⇒ 唯凭件。"""
    if 续点段:
        return dict((k, 续点段.get(k)) for k in 四事实)
    return 凭件(件文, 今天)

def 悬空(续点段):
    u"""续点之「下一步」五元 ⇒ 缺者之名表（空表 ＝ 不悬空）。⛔ 空串不作「有」。"""
    if not 续点段:
        return list(五元)
    return [k for k in 五元 if not str(续点段.get(k) or u"").strip()]

def 具判别力(件文, 续点段, 今天):
    u"""抽掉续点段 ⇒ 答案是否即变（变 ⇒ 该例具判别力 ／ 不变 ⇒ 齿盲）。"""
    return 凭件(件文, 今天) != 复起(件文, 续点段, 今天)

_中件 = chr(10).join([
    u"---",
    u"type: 试",
    u"序号: 3001",
    u"类别: 试",
    u"status: open",
    u"立项: 3001",
    u"主: CodexWindows线（b2a5182）",
    u"期: 2026-10-12",
    u"判据: 四条（成 ∨ 废）",
    u"阶段: ⒈取料 到点 2026-10-08 应缴 料齐 ｜ ⒉清洗 到点 2026-10-09 应缴 净本 ｜ ⒊入 PA（一件之最小形） 到点 2026-10-12 应缴 一件入册",
    u"结论: 待收口",
    u"---",
    u"",
])
_中续 = {u"当前阶段": u"⒊入 PA（一件之最小形）", u"动作": u"跑 E2E 一例并入册",
        u"器": u"pytest", u"命令": u"python -m pytest tests/e2e -k 入册",
        u"应缴": u"一例 E2E 之 rc ＋ 印", u"候谁": u"CodexWindows线（b2a5182）", u"到点": u"2026-10-12"}
_中真 = {u"当前阶段": u"⒊入 PA（一件之最小形）", u"动作": u"跑 E2E 一例并入册",
        u"候谁": u"CodexWindows线（b2a5182）", u"到点": u"2026-10-12"}

_首件 = chr(10).join([
    u"---",
    u"type: 试",
    u"序号: 2144",
    u"类别: 试",
    u"status: open",
    u"立项: 2140",
    u"主: 技术总监（f202f89）",
    u"期: 2026-10-12",
    u"判据: 三条（成 ∨ 废）",
    u"阶段: ⒈取音轨 到点 2026-10-10 应缴 yt-dlp 装成 ＋ 一例音频 ｜ ⒉本机 ASR 出字 到点 2026-10-11 应缴 一例带时码之 md ｜ ⒊入 PA 到点 2026-10-12 应缴 一件入册",
    u"结论: 待收口",
    u"---",
    u"",
])
_首续 = {u"当前阶段": u"⒈取音轨", u"动作": u"yt-dlp 装成 ＋ 一例音频", u"器": u"pip",
        u"命令": u"pip install yt-dlp", u"应缴": u"yt-dlp 可执行 ＋ 一例音频",
        u"候谁": u"技术总监（f202f89）", u"到点": u"2026-10-10"}

今 = u"2026-10-09"

def test_正控_中段例给续点段则四事实逐字命中():
    got = 复起(_中件, _中续, 今)
    assert got == _中真, u"正控失败：中段例 ＋ 续点段 应四事实逐字命中 ⇒ 实测 %s" % got
    assert 悬空(_中续) == [], u"正控失败：续点之五元应俱全"

def test_反控_中段例抽掉续点段则落错():
    got = 凭件(_中件, 今)
    assert got != _中真, u"反控未咬：中段例抽掉续点段应落错"
    assert got[u"当前阶段"] == u"⒉清洗", u"落错应落在 ⒉清洗（件不足以判「当前」）⇒ 实测 %s" % got

def test_反控_首阶段例不具判别力须被标():
    assert 具判别力(_中件, _中续, 今) is True, u"中段例应具判别力（抽掉即变）"
    assert 具判别力(_首件, _首续, 今) is False, (
        u"首阶段例应被标为不具判别力（件自足 ⇒ 反控不咬）—— 此即齿盲，须防")

def test_反控_五元逐一抽掉必点名():
    未咬 = []
    for k in 五元:
        cut = dict(_中续)
        cut.pop(k, None)
        if 悬空(cut) != [k]:
            未咬.append((k, 悬空(cut)))
    assert not 未咬, u"反控未咬（每抽一元应恰点名该元）：%s" % 未咬
    assert 悬空(None) == list(五元)
    assert 悬空(dict(_中续, 命令=u"   ")) == [u"命令"], u"空串不得充「有」"

def self_test():
    u"""正控 ／ 反控 之数（承 PM 2149 §三.4）。"""
    正控 = 反控 = 0
    败 = []
    if 复起(_中件, _中续, 今) == _中真 and 悬空(_中续) == []:
        正控 += 1
    else:
        败.append(u"正控1（中段例逐字命中 ＋ 五元俱全）")
    if 凭件(_中件, 今) == {u"当前阶段": u"⒉清洗", u"动作": u"净本",
                           u"候谁": u"CodexWindows线（b2a5182）", u"到点": u"2026-10-09"}:
        正控 += 1
    else:
        败.append(u"正控2（唯凭件之落点可预）")
    if 凭件(_中件, 今) != _中真:
        反控 += 1
    else:
        败.append(u"反控1（中段例抽续点段 ⇒ 应落错）")
    if 具判别力(_中件, _中续, 今) is True:
        反控 += 1
    else:
        败.append(u"反控2（中段例具判别力）")
    if 具判别力(_首件, _首续, 今) is False:
        反控 += 1
    else:
        败.append(u"反控3（首阶段例须判齿盲）")
    for k in 五元:
        cut = dict(_中续)
        cut.pop(k, None)
        if 悬空(cut) == [k]:
            反控 += 1
        else:
            败.append(u"反控（抽 %s）" % k)
    print(u"[test_pa_续点复起] 正控 %d ／ 反控 %d ／ %s"
          % (正控, 反控, u"全 PASS" if not 败 else u"败：%s" % 败))
    return 0 if not 败 else 2

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    print(u"用法：--self-test（本件由 pytest 收为齿 · 此为自证入口）")
    sys.exit(3)
