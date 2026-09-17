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
    ("UNC", r"\\\\[A-Za-z0-9_.-]+\\"),
    ("Windows 盘符", r"\b[A-Za-z]:\\"),
    ("WSL 挂载", r"/mnt/[a-z]/"),
    ("本机绝对路径", r"/home/flybo/"),
]

TARGETS = ["web/pa.html"]


def _scan(path):
    """返回 [(行号, 名称, 该行)]；**跳过整行注释**（注释里说明「不要写路径」是合法的）。"""
    hits = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            s = line.strip()
            if s.startswith("//") or s.startswith("*") or s.startswith("/*") or s.startswith("<!--"):
                continue
            for name, rx in BANNED:
                if re.search(rx, line):
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
