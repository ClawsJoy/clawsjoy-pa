# -*- coding: utf-8 -*-
u"""recipe —— 底名正形（safe_edit 之底 ⇒ 〈件名〉.before_〈印16〉 ＋ verify 之两形候）。

承：pm 1292 §四（**次批 ＝ 底名正形** · 五步：枚举 ＋ 正名 ＋ 同批 ＋ 扫引 ＋ 报印）｜pm 1183 §五（一改一底 · ⛔ 删底）。
其的：⛔ 再生点前缀之旧形（B 形）⇒ 新底皆正形；旧形唯备兼容之**读**（backup_find）。
用法：python -X utf8 -B <本件> 底名正形 [--apply]   （⛔ 无 --apply ⇒ 只演）
      python -X utf8 -B <本件> --verify
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S

底名正形 = [
    (u'safe_edit.py（backup_path ⇒ 正形 ＋ backup_find 两形候 ＋ 律二注）', 'scripts/dev/safe_edit.py', [
        ("sub",
         'def backup_path(p, h):\n    return os.path.join(os.path.dirname(p), "%s%s.%s" % (DOT_PREFIX, h, os.path.basename(p)))',
         'def backup_path(p, h):\n    u"""底之名（**正形** · 承 PM 1292 §四）：〈件名〉.before_〈印16〉 ——\n    ⛔ 点前缀之旧形（旧形唯备兼容之**读** · 承 PM 1292 §四）。"""\n    return "%s%s%s" % (p, DOT_PREFIX, h)\n\n\ndef backup_path_legacy(p, h):\n    u"""旧形（点前缀 · .before_〈印16〉.〈件名〉）—— ⛔ 再生；唯备兼容之读。"""\n    return os.path.join(os.path.dirname(p), "%s%s.%s" % (DOT_PREFIX, h, os.path.basename(p)))\n\n\ndef backup_find(p, h):\n    u"""底之两形之候（**正形先 · 旧形后**）⇒ 路 ∨ None（唯读 · ⛔ 写）。"""\n    for bp in (backup_path(p, h), backup_path_legacy(p, h)):\n        if os.path.exists(bp):\n            return bp\n    return None'),
        ("sub",
         '        bp = backup_path(p, hb)\n        if not os.path.exists(bp):\n            print(u"   [无底] %s idx=%d ／ %s" % (key, idx, bp))\n            bad.append(key)\n            continue\n',
         '        bp = backup_find(p, hb)\n        if not bp:\n            print(u"   [无底] %s idx=%d ／ %s" % (key, idx, backup_path(p, hb)))\n            bad.append(key)\n            continue\n'),
        ("sub",
         '    PM 1187 §二⒜（**assert 是冗余之闸 · ⛔ 代出处**）',
         '    PM 1187 §二⒜（**assert 是冗余之闸 · ⛔ 代出处**）\n    PM 1292 §四（**底名正形**：底 ＝ 〈件名〉.before_〈印16〉 —— ⛔ 再生点前缀之旧形 · 旧形唯备兼容之读）'),
    ]),
    (u'README.md（律二：底之名 ⇒ 正形）', 'scripts/dev/README.md', [
        ("sub",
         '2. **存底粒度 ＝ 「改」· ⛔ 「件」**（一改一底 · PM 1178 §五）：底之名 ≡ 其值（`.before_<改前印>.<件名>` · 点前缀 ⇒ 天然被扫器剔 · ⛔ 删底）。',
         '2. **存底粒度 ＝ 「改」· ⛔ 「件」**（一改一底 · PM 1178 §五）：底之名 ≡ 其值（**正形** ＝ 〈件名〉.before_〈改前印〉 · 承 PM 1292 §四 · 点前缀之旧形 .before_〈改前印〉.〈件名〉 ⛔ 再生 · ⛔ 删底）。'),
    ]),
]
EDITS = {"底名正形": 底名正形}
ORDER = ["底名正形"]
BASES = [
    ('底名正形', 0, 'scripts/dev/safe_edit.py', 'f7ade117a440a147', '4c568584601f04c8'),
    ('底名正形', 1, 'scripts/dev/README.md', '878656bf20703ed6', 'a0874870921b0b85'),
]


if __name__ == "__main__":
    sys.exit(S.cli(EDITS, ORDER, bases=BASES, title=u"底名正形 · safe_edit ＋ README"))
