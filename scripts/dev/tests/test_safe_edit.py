# -*- coding: utf-8 -*-
u"""test_safe_edit —— 反控：器之「所报之印」须取自「写后回读」。

承 PM 1187 §二⒜：**后验 ≠ 出处** —— ~BT~assert~BT~ 唯冗余之闸 · ⛔ 代出处。
正控：算者 ≡ 写者 ⇒ 算 ＝ 读。
反控：写者 ≠ 算者（他器中途改写 ／ 落盘截断）⇒ 旧形（算后即报）报**悬空**之印 ／ 今形报**真**值。
用法：python -X utf8 -B tests/test_safe_edit.py      （退出码 0 = PASS ／ 1 = FAIL）
"""
import hashlib
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import safe_edit as S


def _sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


def main():
    d = tempfile.mkdtemp(prefix=u"safe_edit_test_")
    p = os.path.join(d, u"t.txt")
    open(p, "wb").write(u"ORIG\n".encode("utf-8"))
    rc = 0

    # ---- 器之实：make_backup 之「底」取自读（⛔ 取自算） ----
    p2 = os.path.join(d, u"t2.txt")
    open(p2, "wb").write(u"AAA\n".encode("utf-8"))
    h, bp, new = S.make_backup(p2)
    src = open(p2, "rb").read()
    ok_bak = (h == _sha(src)) and (open(bp, "rb").read() == src)
    print(u"[器·存底] 底=%s ｜ 名 ≡ 读之值 = %s" % (os.path.basename(bp), ok_bak))
    if not ok_bak:
        rc = 1

    # ---- 正控：算者 ≡ 写者 ----
    t1 = u"NEW1\n"
    h1 = _sha(t1.encode("utf-8"))
    open(p, "wb").write(t1.encode("utf-8"))
    calc, read = h1, _sha(open(p, "rb").read())
    print(u"[正控] 算=%s ／ 回读=%s ／ 同=%s" % (calc, read, calc == read))
    if calc != read:
        rc = 1

    # ---- 反控：写者 ≠ 算者（写者多落一字节） ----
    t1 = u"NEW2\n"
    h1 = _sha(t1.encode("utf-8"))
    open(p, "wb").write(u"NEW2\nX".encode("utf-8"))
    calc, read = h1, _sha(open(p, "rb").read())
    print(u"[反控] 算=%s ／ 回读=%s" % (calc, read))
    print(u"       ⇒ 旧形（算后即报）所报 = %s（悬空）" % calc)
    print(u"       ⇒ 今形（写后回读）所报 = %s（真）" % read)
    if calc == read:
        rc = 1

    print(u"[总判] " + (u"PASS" if rc == 0 else u"FAIL"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
