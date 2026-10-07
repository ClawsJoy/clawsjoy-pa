# -*- coding: utf-8 -*-
"""故障注入 #17：前端不得硬编码文件系统路径（2026-09-13 批71，C1 的静态防线）。

为什么需要它：C1 的设计要点是「**后端决定落盘位置**，前端只调端点、只用返回值拼 URL」。
历史上缩略图的真实来源是灵犀导出的 Windows 目录，C 块实测过 UNC 直写可行 ——
但**让前端拼 UNC 路径正是要消灭的东西**：live 与 sandbox 路径不同 ⇒ 会写错地方。

所以设一道**静态防线**：web/ 下任何文件都不许出现
  - UNC 路径
  - Windows 盘符
  - WSL 挂载 /mnt/
  - 本机绝对路径 /home/
这样即使以后有人为了图省事把路径写回前端，也会立刻红。
"""
import os
import re

import pytest

BANNED = [
    # 2026-10-06（承 pm 1336 §二.3 · 正判据 · 一改一底）：UNC 须锚「值首 ∨ 行首」。
    # 形：值首之二反斜杠 ＋ 名 ＋ 反斜杠；⛔ 「径中任一处之二反斜杠」。
    # 病（一手 · 扩面首逮）：JS 转义形态之相对径（实为 data\v9\pa\x 者）经 _unescape_js
    # 得单反斜杠，而**原文**仍含「双反斜杠＋名＋反斜杠」⇒ 旧判据（裸形）误判为 UNC
    # （today.js:209/218/219/220 ／ selfdesc.js:1488/3106 ＝ 本批四假红）。
    # 正：二反斜杠之前须为「值之起」（行首 ∨ 引号 ∨ 反引号 ∨ = , ( [ ∨ 空白）。
    #   ⚠ ⛔ 含「：」—— D:\\…（盘符 ＋ 转义之二反斜杠）亦以「：」入门 ⇒ 假红（本刻一手）；
    #   而「：」之真例（key: \\srv）皆带空白 ⇒ \s 已覆盖 ⇒ 删「：」（无损失）。
    ("UNC", r'''(?:^|[\s\x22'\x60=,(\[])\\\\[A-Za-z0-9_.-]+\\'''),
    ("Windows 盘符", r"\b[A-Za-z]:\\"),
    ("WSL 挂载", r"/mnt/[a-z]/"),
    ("本机绝对路径", r"/home/[A-Za-z0-9_.-]+/"),
]

# 拆面（承 pm 1334 §二.2）：面 ＝ 壳 ＋ 诸支（径逐字 · 取自 CW 1333 §一 之活面表 · ⛔ 通配 ／ ⛔ 手列）
TARGETS = [
    "web/pa.html",
    "web/pa/boot.js",
    "web/pa/core.js",
    "web/pa/faces.json",
    "web/pa/pa.css",
    "web/pa/pa_v3.css",
    "web/pa/ui_state.json",
    "web/pa/测试痕_清单.json",
    "web/pa/faces/archive.js",
    "web/pa/faces/authz.js",
    "web/pa/faces/caliber.js",
    "web/pa/faces/cards.js",
    "web/pa/faces/chat.js",
    "web/pa/faces/collect.js",
    "web/pa/faces/config.js",
    "web/pa/faces/drawer.js",
    "web/pa/faces/files.js",
    "web/pa/faces/input.js",
    "web/pa/faces/more.js",
    "web/pa/faces/products.js",
    "web/pa/faces/profile.js",
    "web/pa/faces/selfdesc.js",
    "web/pa/faces/send.js",
    "web/pa/faces/session.js",
    "web/pa/faces/shell.js",
    "web/pa/faces/sources.js",
    "web/pa/faces/status.js",
    "web/pa/faces/tasks.js",
    "web/pa/faces/today.js",
]


def _unescape_js(line):
    """JS 源码里的路径常写成**转义形态**（分隔符前带反斜杠）—— 先还原再匹配。

    为什么必须还原（2026-09-28 实测）：把 `/mnt/d/...` 写成 反斜杠加斜杠 的形态时，
    `/mnt/[a-z]/` **匹配不到**（分隔符前有反斜杠）⇒ 门报绿、而路径其实**写死在前端**。
    ⛔ 不还原 ⇒ 本门对「JS 转义形态」恒盲（判据在场、却不生效）。
    """
    return line.replace(chr(92) + "/", "/").replace(chr(92) * 2, chr(92))


def _scan(path):
    """返回 [(行号, 名称, 该行)]；**跳过整行注释**（注释里说明「不要写路径」是合法的）。"""
    hits = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            s = line.strip()
            if s.startswith("//") or s.startswith("*") or s.startswith("/*") or s.startswith("<!--"):
                continue
            _un = _unescape_js(line)
            for name, rx in BANNED:
                if re.search(rx, line) or re.search(rx, _un):
                    hits.append((i, name, s[:110]))
    return hits


@pytest.mark.parametrize("target", TARGETS)
def test_no_hardcoded_fs_path_in_frontend(target):
    """前端源码不得出现 UNC / 盘符 / /mnt/ / /home/ —— C1 的「后端定位置」契约靠它守。"""
    if not os.path.exists(target):
        pytest.skip(target + " 不存在")
    hits = _scan(target)
    assert not hits, "前端出现硬编码文件系统路径（C1 契约：后端定落盘位置，前端只用 url_base）：\n" + "\n".join("  L%d [%s] %s" % h for h in hits)


def test_scanner_has_teeth(tmp_path):
    """防误伤 + 防失效自检：造的样本必须被检出，干净样本必须不报（体检项 5/36）。"""
    bad = tmp_path / "bad.html"
    bad.write_text(
        "const u=" + chr(34) + "C:" + chr(92) + chr(92) + "Users" + chr(92) + chr(92) + "x" + chr(34) + ";\n",
        encoding="utf-8",
    )
    assert _scan(str(bad)), "盘符样本未被检出（扫描器失效）"
    good = tmp_path / "good.html"
    good.write_text("img.src=URL_BASE+name;\n", encoding="utf-8")
    assert not _scan(str(good)), "干净样本被误报"
    # 2026-10-06（承 pm 1336 §二.3 · 正判据之对控 · 承「器之效须有实证」）：
    # 正后之 UNC 判据仍须逮「值首之二反斜杠」—— ⛔ 削其的（防「削的以就己」）。
    unc = tmp_path / "unc.html"
    unc.write_text(
        "<img src=" + chr(34) + chr(92) * 2 + "srv" + chr(92) + "share" + chr(92) + "a.png" + chr(34) + ">" + chr(10),
        encoding="utf-8",
    )
    assert _scan(str(unc)), "真 UNC（值首之二反斜杠）未被检出（UNC 判据被削）"

def test_scanner_sees_js_escaped_paths(tmp_path):
    """⛔ 盲区回归：JS **转义形态**的写死路径必须被检出（否则门假绿）。

    一手事故（2026-09-28）：web/pa.html 曾以「转义形态」写死 vault 路径，而当时的门**报绿**
    —— 因为 `/mnt/[a-z]/` 撞不上「分隔符前带反斜杠」的写法。
    """
    esc = tmp_path / "esc.html"
    sample = "  const re=/" + chr(92) + "/mnt" + chr(92) + "/d/x.md/g;" + chr(10)
    esc.write_text(sample, encoding="utf-8")
    hits = _scan(str(esc))
    assert hits, "JS 转义形态的写死路径未被检出（门有盲区）"
