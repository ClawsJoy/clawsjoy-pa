# -*- coding: utf-8 -*-
u"""recipe —— 件之完（闸三）：落箱加闸一 ／ 二 ／ 三 ＋ 自证 4 之反控三。

承：pm 1294 §二（令：加「件之完」之闸三 ＋ 反控三）｜pm 1298 §三（令「即办」＋ 认剔法 ／ 半角符集）。
其的：⛔ 「半写之件」入箱（实：CW 1292 之落箱残 10,590 B ＋ 未落行 ＋ 未醒）。
用法：python -X utf8 -B <本件> 闸三 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

闸三 = [
    (u'投一步.py（落箱 ⇒ 件之完 闸一／二／三 ＋ 自证 4 之反控三）', 'scripts/dev/投一步.py', [
        ('sub', '4 = 落箱败（BOM ／ CR ／ 箱内异）',
         '4 = 落箱败（BOM ／ CR ／ 件之完 ／ 箱内异）'),
        ('sub', '    u"""落箱：草稿 ⇒ 箱（信通）。⭐ 硬闸：⛔ BOM ／ ⛔ CR（须 LF）；箱内已同 ⇒ ⛔ 复写；异 ⇒ 拒。"""',
         '    u"""落箱：草稿 ⇒ 箱（信通）。⭐ 硬闸：⛔ BOM ／ ⛔ CR（须 LF）／ **件之完（闸一／二／三 · 承 pm 1294 §二）**；箱内已同 ⇒ ⛔ 复写；异 ⇒ 拒。"""'),
        ('sub', '# ---------------------------------------------------------------- 落箱\ndef step_box(src, name, dry=False, box=XT):',
         '# ------------------------------------------------ 件之完（闸一 ／ 二 ／ 三 · 承 pm 1294 §二 ／ pm 1298 §三）\nHAN = u"一二三四五六七八九十"\nSUSPECT_TAIL = (u"（", u"(", u"[", u"：", u":", u"，", u",", u"、", u"＋", u"｜", u"——", u"「", u"/", u"-")\n\n\ndef han_to_int(s):\n    u"""汉字数 ⇒ 整数（唯及「十」· 本族之节号 ⛔ 越十）⇒ 失败 ⇒ None。"""\n    if not s:\n        return None\n    if len(s) == 1:\n        return HAN.index(s) + 1 if s in HAN else None\n    if s[0] == u"十" and len(s) == 2 and s[1] in HAN:\n        return 10 + HAN.index(s[1]) + 1\n    if len(s) == 2 and s[1] == u"十" and s[0] in HAN:\n        return (HAN.index(s[0]) + 1) * 10\n    return None\n\n\ndef front_matter(text):\n    u"""取 front matter 之行（⛔ 含二界之 ---）⇒ list ∨ None。"""\n    lines = text.split("\\n")\n    if not lines or lines[0].strip() != u"---":\n        return None\n    for i in range(1, len(lines)):\n        if lines[i].strip() == u"---":\n            return lines[1:i]\n    return None\n\n\nFM_FIELD = re.compile(u"^([A-Za-z_\\u4e00-\\u9fff\\u00b7][^:]*):[ \\t]?(.*)$")\n\n\ndef fm_field(fm, name):\n    u"""front matter 之某字段 ⇒ 其值（含续行 · 以空格联）∨ 空串。"""\n    out, on = u"", False\n    for l in (fm or []):\n        m = FM_FIELD.match(l)\n        if m:\n            on = (m.group(1).strip() == name)\n            if on:\n                out = m.group(2)\n            continue\n        if on and l.strip():\n            out = (out + u" " + l.strip()).strip()\n    return out\n\n\ndef promised_sections(fm):\n    u"""「动作需求」之 §〈汉字数〉 ⇒ (集, 所取之列逐字) —— ⚠ **唯取本字段** ∧ **§ 须紧接「（」**\n    （承 pm 1298 §三.1 之剔法 ＋ 实探）：本族之诺之形 ≡ （§三）／（§一 · 器取）；\n    ⛔ 取他件之引（如 §五.⒊ 之界 ／ pm 1294 §三 ⇒ 实：1222 ／ 1253 之假红）；\n    ⛔ 取变体（如（器取逐行 · §一）⇒ 宁漏 ⛔ 假红）。"""\n    f = fm_field(fm, u"动作需求")\n    got = set()\n    for m in re.finditer(u"（§[ \\t]*([%s]+)" % HAN, f):\n        n = han_to_int(m.group(1))\n        if n:\n            got.add(n)\n    return got, f\n\n\ndef heading_sections(text):\n    u"""节标题之汉字数集（## 三 ／ ### 三 ／ ## §三 任一体 —— 承 pm 1294 §二）。"""\n    got = set()\n    for m in re.finditer(u"(?m)^#{2,4}[ \\t]*§?[ \\t]*([%s]+)(?=[ \\t\\u3000\\u00b7\\uff1a\\uff0f\\uff09]|$)" % HAN, text):\n        n = han_to_int(m.group(1))\n        if n:\n            got.add(n)\n    return got\n\n\ndef int_to_han(n):\n    return HAN[n - 1] if 1 <= n <= len(HAN) else str(n)\n\n\ndef last_nonblank(text):\n    for l in reversed(text.split("\\n")):\n        if l.strip():\n            return l\n    return u""\n\n\ndef body_gate(b, text, name):\n    u"""件之完（闸一 ／ 二 ／ 三）⇒ (rc, 报) ∨ None（过）。"""\n    want, field = promised_sections(front_matter(text))\n    miss = sorted(n for n in want if n not in heading_sections(text))\n    if miss:\n        return 4, (u"落箱：⛔ 动作需求 诺之节 ⛔ 见其文（缺：%s）⇒ 疑截断（承 pm 1294 §二 闸一）"\n                   u"｜所取之列逐字 ＝ %s ｜书名 ＝ %s"\n                   % (u"／".join(u"§" + int_to_han(n) for n in miss), field, name))\n    last = last_nonblank(text)\n    if last.rstrip().endswith(SUSPECT_TAIL):\n        return 4, (u"落箱：⛔ 末行疑截断（承 pm 1294 §二 闸二）｜末行逐字 ＝ %s ｜书名 ＝ %s"\n                   % (last, name))\n    if not last:\n        return 4, u"落箱：⛔ 件为「空」（⛔ 无非空之行）｜书名 ＝ %s" % name\n    if not b.endswith(b"\\n"):\n        return 4, u"落箱：⛔ 件无尾（末字节 ⛔ ＝ \\\\n）｜书名 ＝ %s" % name\n    if not any(l.strip() for l in text.split("\\n")[:3]):\n        return 4, u"落箱：⛔ 件首三行皆空（疑残）｜书名 ＝ %s" % name\n    return None\n\n\n# ---------------------------------------------------------------- 落箱\ndef step_box(src, name, dry=False, box=XT):'),
        ('sub', '    if b"\\r" in b:\n        return 4, u"落箱：⛔ 草稿带 CR（信通之件须 LF）"\n    dst = os.path.join(box, name)',
         '    if b"\\r" in b:\n        return 4, u"落箱：⛔ 草稿带 CR（信通之件须 LF）"\n    try:\n        _t = b.decode("utf-8")\n    except Exception:\n        return 4, u"落箱：⛔ 草稿 ⛔ 合 UTF-8（译码败）"\n    _g = body_gate(b, _t, name)\n    if _g:\n        return _g\n    dst = os.path.join(box, name)'),
        ('sub', '    rc, m = step_box(os.path.join(tmp, "无此件.md"), "x.md", dry=False, box=box)\n    res(u"草不在 ⇒ 3", rc, 3)\n\n    print(u"[自证 3 醒 · 正控 / 反控（承 pm 1291 §四：反控须证其可达「非零」）]")',
         '    rc, m = step_box(os.path.join(tmp, "无此件.md"), "x.md", dry=False, box=box)\n    res(u"草不在 ⇒ 3", rc, 3)\n\n    print(u"[自证 4 落箱 · 件之完之反控三（承 pm 1294 §二 ／ pm 1298 §三）]")\n    lack = os.path.join(tmp, "d.md")\n    open(lack, "wb").write(u"---\\ntype: 报\\ndate: 2026-10-06\\n动作需求: 办一（§一）／ 办六（§六）\\n---\\n\\n## 一 甲\\n\\n正文\\n".encode("utf-8"))\n    rc, m = step_box(lack, "d.md", dry=False, box=box)\n    res(u"缺节（诺 §一／§六 · 其文唯 §一）⇒ 4", rc, 4)\n    print(u"    其报：" + m)\n    hit = (u"§六" in m) and (u"动作需求" in m)\n    print(u"  %s 其报含「所缺之节号逐字 ＋ 所取之列逐字」" % (u"OK " if hit else u"✗ "))\n    ok = ok and hit\n    susp = os.path.join(tmp, "e.md")\n    open(susp, "wb").write(u"# 甲\\n正文（\\n".encode("utf-8"))\n    rc, m = step_box(susp, "e.md", dry=False, box=box)\n    res(u"末悬（末行 ＝「正文（」）⇒ 4", rc, 4)\n    hit = (u"正文（" in m)\n    print(u"  %s 其报含「末行逐字」" % (u"OK " if hit else u"✗ "))\n    ok = ok and hit\n    blank = os.path.join(tmp, "f.md")\n    open(blank, "wb").write(b"\\n")\n    rc, m = step_box(blank, "f.md", dry=False, box=box)\n    res(u"空件（唯 \\\\n）⇒ 4", rc, 4)\n    print(u"    其报：" + m)\n    notail = os.path.join(tmp, "g.md")\n    open(notail, "wb").write(u"# 甲\\n正文".encode("utf-8"))\n    rc, m = step_box(notail, "g.md", dry=False, box=box)\n    res(u"无尾（末字节 ⛔ ＝ \\\\n）⇒ 4", rc, 4)\n\n    print(u"[自证 3 醒 · 正控 / 反控（承 pm 1291 §四：反控须证其可达「非零」）]")'),
    ]),
]
EDITS = {"闸三": 闸三}
ORDER = ["闸三"]
BASES = [
    ('闸三', 0, 'scripts/dev/投一步.py', '9be0af5e07d62e85', '4675fefe1eac7af7'),
]


if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"件之完（闸三）· 投一步.py"))
