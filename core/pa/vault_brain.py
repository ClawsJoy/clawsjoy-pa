# -*- coding: utf-8 -*-
"""Obsidian 第二大脑桥 v0(2026-09-10): 待办/进度/附件/未读/站会落盘 vault, 可编辑可提醒。

设计依据: PA方向文档 §10。
- sync_ledger: 账本 -> 《PA待办与进度.md》(checkbox, 老板可在 vault 直接勾/改)
- parse_ledger: 反向读取 vault md checkbox 状态回写账本(vault 是老板可编辑的真相源之一)
- register_asset: PDF/PPT/Excel/PNG 等二进制 -> vault 附件/<kind>/, 返回 ![[...]] 链接
- unread_index: 收件箱未读清单《_未读索引.md》(已读=移归档/或 frontmatter status: read)
- daily_standup: 《PA每日站会.md》(过期/今日/近3日), 供提醒与晨会
"""
import re
import shutil
import time
from pathlib import Path
from core.lib.paths import vault_root

VAULT_ROOT = str(vault_root())


class BrainSync:
    def __init__(self, ledger, vault_dir=VAULT_ROOT):
        self.ledger = ledger
        self.vault = Path(vault_dir)
        self.inbox = self.vault / "收件箱"
        self.archive = self.vault / "归档"
        self.assets = self.vault / "附件"

    def sync_ledger(self, path=None):
        path = Path(path or (self.inbox / "PA待办与进度.md"))
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# PA 待办与进度(自动同步, 可在本文件直接勾选改状态)",
            "",
            "> 更新于 %s; 格式: - [ ] 未做 / - [x] 完成 / (id: tN kind: xx)" % time.strftime("%Y-%m-%d %H:%M"),
            "",
        ]
        for k in ("todo", "verify", "followup", "decision"):
            items = self.ledger.open_items([k])
            if not items:
                continue
            lines.append("## %s" % k)
            for it in items:
                due = " due=%s" % it.get("due") if it.get("due") else ""
                lines.append("- [ ] %s (id: %s kind: %s%s)" % (it.get("title"), it.get("id"), k, due))
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path)

    def parse_ledger(self, path=None):
        """读回 vault md 勾选状态 -> 回写 ledger(已勾=[x] 置 done)。"""
        path = Path(path or (self.inbox / "PA待办与进度.md"))
        if not path.exists():
            return 0
        n = 0
        for ln in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*-\s+\[( |x|X)\]\s+.*\(id:\s*(t\d+)[^)]*\)", ln)
            if not m:
                continue
            done = m.group(1).lower() == "x"
            tid = m.group(2)
            it = next((i for i in self.ledger.items if i.get("id") == tid), None)
            if it is None:
                continue
            if done and it.get("status") != "done":
                self.ledger.set_status(tid, "done", note="vault 勾选完成")
                n += 1
            elif not done and it.get("status") == "done":
                self.ledger.set_status(tid, "open", note="vault 取消勾选")
                n += 1
        return n

    def register_asset(self, src_file, kind="docs", title=""):
        """二进制附件 -> vault 附件/<kind>/; 返回嵌入链接与相对路径。"""
        src = Path(src_file)
        if not src.exists():
            return {"ok": False, "error": "源不存在: %s" % src}
        dest_dir = self.assets / kind
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        link = "![[%s]]" % (dest.relative_to(self.vault).as_posix())
        return {"ok": True, "dest": str(dest), "link": link, "size": src.stat().st_size}

    def unread_index(self, path=None):
        """收件箱未读索引(约定: 收件箱文件=未读; 老板读完移 归档/ 或改 frontmatter)。"""
        path = Path(path or (self.inbox / "_未读索引.md"))
        unread = []
        for f in sorted(self.inbox.glob("*.md")):
            if f.name.startswith("_"):
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")[:500]
            if re.search(r"(?m)^status:\s*read", text):
                continue
            unread.append(f.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = ["# 收件箱未读索引(PA 维护)", ""]
        for name in unread:
            body.append("- [ ] %s" % name)
        if not unread:
            body.append("(无未读)")
        path.write_text("\n".join(body), encoding="utf-8")
        return len(unread)

    def daily_standup(self, path=None):
        """每日站会/提醒清单: 过期/今日/近3日(due 格式 YYYY-MM-DD)。"""
        today = time.strftime("%Y-%m-%d")
        path = Path(path or (self.inbox / "PA每日站会.md"))
        overdue, today_items, soon = [], [], []
        for it in self.ledger.items:
            if it.get("status") in ("done", "cancelled"):
                continue
            due = (it.get("due") or "").strip()
            if not due:
                continue
            if due < today:
                overdue.append(it)
            elif due == today:
                today_items.append(it)
            else:
                soon.append(it)
        lines = ["# PA 每日站会(%s)" % today, ""]
        lines.append("## 已过期")
        lines += ["- [x] %s (id:%s due:%s)" % (i["title"], i["id"], i.get("due")) for i in overdue] or ["(无)"]
        lines.append("")
        lines.append("## 今日")
        lines += ["- [ ] %s (id:%s)" % (i["title"], i["id"]) for i in today_items] or ["(无)"]
        lines.append("")
        lines.append("## 近 3 日")
        lines += ["- [ ] %s (id:%s due:%s)" % (i["title"], i["id"], i.get("due")) for i in soon] or ["(无)"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return {"overdue": len(overdue), "today": len(today_items), "soon": len(soon)}
