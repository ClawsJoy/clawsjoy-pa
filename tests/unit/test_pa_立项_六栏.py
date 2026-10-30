# -*- coding: utf-8 -*-
"""test_pa_立项_六栏.py —— 试卡「立项六栏」之齿（承 PM 2149 §三.1 · 源 PM _试卡之法_v1_4 之 §八.1）。

判据（一处定形）：凡「试卡」（信通之件 · front matter 载六栏）⇒ 六栏缺一即红：
  立项 ／ 主 ／ 期 ／ 判据 ／ 阶段 ／ 结论（缺一 ⇒ 未立项 ⇒ 不计）。
  ⚠ 本齿唯报「缺栏之名」，不判栏内之实 —— 「栏在」与「栏之实合格」二者分书
  （后者归 CEO 域 codex/_CEO面核.py --trial 之射程）。

治具（照本仓之例 · 用内嵌之形 · 不读活箱）：件一归档即假红 ⇒ 故以真件之形为样例
（2026-10-09 真件 _卡_TD_2144_试卡一在线视频录音转文字.md 之同形）。

正控：六栏俱全 ⇒ 缺栏 ＝ 0。
反控：逐栏抽掉 ⇒ 必恰点名该栏（六咬）；空白件 ⇒ 六栏皆缺。
用法：python -X utf8 -B tests/unit/test_pa_立项_六栏.py --self-test
"""
import sys

六栏 = (u"立项", u"主", u"期", u"判据", u"阶段", u"结论")


def 取值(件文, 栏):
    u"""件文 ⇒ 栏之值（无 ⇒ None）。口径（与 PM _立项state.py 同源）：行首之「栏:」或「栏：」。"""
    for ln in (件文 or u"").splitlines():
        st = ln.strip()
        for sep in (u":", u"："):
            p = 栏 + sep
            if st.startswith(p):
                v = st[len(p):].strip()
                if v:
                    return v
    return None


def 缺栏(件文):
    u"""件文 ⇒ 缺栏之名表（空表 ＝ 俱全）。⛔ 空值不作为「有栏」。"""
    return [k for k in 六栏 if 取值(件文, k) is None]


_样例 = chr(10).join([
    u"---",
    u"type: 试",
    u"from: 技术总监（f202f89）",
    u"序号: 2144",
    u"类别: 试",
    u"status: open",
    u"立项: 2140",
    u"主: 技术总监（f202f89）",
    u"期: 2026-10-12",
    u"判据: 三条（成 ∨ 废 之尺 · 逐条可判）",
    u"阶段: ⒈取音轨 到点 2026-10-10 应缴 yt-dlp 装成 ＋ 一例音频 ｜ ⒉本机 ASR 出字 到点 2026-10-11 应缴 一例带时码之 md ｜ ⒊入 PA 到点 2026-10-12 应缴 一件入册",
    u"结论: 待收口（预计 2026-10-12 判 · 成 ／ 废 ／ 存 ＋ 去处）",
    u"---",
    u"",
    u"## 一 六栏（正文）",
    u"",
])


def 抽栏(件文, 栏):
    u"""抽掉某栏（该行之首即栏名 ⇒ 整行去）⇒ 新件文。"""
    keep = []
    for ln in 件文.splitlines():
        st = ln.strip()
        if st.startswith(栏 + u":") or st.startswith(栏 + u"："):
            continue
        keep.append(ln)
    return chr(10).join(keep)


def test_正控_六栏俱全():
    缺 = 缺栏(_样例)
    assert 缺 == [], u"正控失败：真件之形应六栏俱全，实测缺 %s" % 缺


def test_正控_取值口径不越名():
    assert 取值(_样例, u"立项") == u"2140"
    assert 取值(_样例, u"期") == u"2026-10-12"
    assert 取值(_样例, u"阶段").startswith(u"⒈取音轨")
    assert 取值(u"期望: 三千", u"期") is None, u"取值口径过宽：期望 不得充 期"
    assert 取值(u"期:", u"期") is None, u"空值不得充「有栏」"


def test_反控_逐栏抽掉必恰点名():
    未咬 = []
    for k in 六栏:
        got = 缺栏(抽栏(_样例, k))
        if got != [k]:
            未咬.append((k, got))
    assert not 未咬, u"反控未咬（每抽一栏应恰点名该栏）：%s" % 未咬


def test_反控_空白件六栏皆缺():
    assert 缺栏(u"") == list(六栏)
    assert 缺栏(u"---" + chr(10) + u"type: 试" + chr(10) + u"---") == list(六栏)


def self_test():
    u"""正控 ／ 反控 之数（承 PM 2149 §三.4：各带反控且真咬）。"""
    正控 = 反控 = 0
    败 = []
    if 缺栏(_样例) == []:
        正控 += 1
    else:
        败.append(u"正控1（六栏俱全）")
    if (取值(_样例, u"立项") == u"2140" and 取值(_样例, u"期") == u"2026-10-12"
            and 取值(u"期望: 三千", u"期") is None and 取值(u"期:", u"期") is None):
        正控 += 1
    else:
        败.append(u"正控2（口径不越名）")
    for k in 六栏:
        if 缺栏(抽栏(_样例, k)) == [k]:
            反控 += 1
        else:
            败.append(u"反控（抽 %s）" % k)
    if 缺栏(u"") == list(六栏):
        反控 += 1
    else:
        败.append(u"反控（空白件）")
    print(u"[test_pa_立项_六栏] 正控 %d ／ 反控 %d ／ %s"
          % (正控, 反控, u"全 PASS" if not 败 else u"败：%s" % 败))
    return 0 if not 败 else 2


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    print(u"用法：--self-test（本件由 pytest 收为齿 · 此为自证入口）")
    sys.exit(3)
