# -*- coding: utf-8 -*-
"""草稿箱插件基类 — Obsidian 草稿箱系统的统一抽象(2026-08-31)

设计(方案: draft_box_feasibility_20260831.md):
- Agent 只产出内容+格式化 → write_draft 写入 vault 草稿箱/{platform}/
- 用户 Obsidian 审核 → 手动发布 → 回传链接 → mark_published
- 图片复制进 assets/, 视频用相对路径引用(避免 vault 膨胀)

平台差异通过子类字段表达: platform/platform_dir/frontmatter_fields/cover_desc。
"""
from __future__ import annotations
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _vault_root() -> Path:
    """vault 根(与 precision_inject._vault_path 一致, 避免循环依赖直接读配置)"""
    try:
        import yaml
        with open("config/v9/execution_policy.yaml", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        p = (cfg.get("obsidian") or {}).get("vault_path", "")
        if p and Path(p).exists():
            return Path(p)
    except Exception:
        pass
    return Path("/mnt/d/Obsidian/ClawsJoy/ClawsJoy")


def _sanitize_filename(title: str) -> str:
    """标题 → 安全文件名(去非法字符, 限长)"""
    import re
    _s = re.sub(r'[\\/:*?"<>|\n\r\t]+', "-", str(title or "").strip())
    return (_s[:60] if _s else "untitled")


class DraftBoxPlugin:
    """草稿箱插件基类。子类只需覆盖 platform 相关字段。"""

    platform: str = ""          # 平台名(公众号/小红书/知乎/B站/抖音)
    frontmatter_fields: tuple = ()   # 平台额外 frontmatter 字段(在基础字段之外)
    media_note: str = ""        # 媒体说明(写入草稿尾部)

    # ---- 基础 frontmatter 字段(所有平台通用) ----
    _BASE_FIELDS = ("platform", "title", "status", "created",
                    "published", "post_url", "tags")

    def _frontmatter(self, title: str, summary: str = "", tags: List[str] = None,
                     extra: Dict[str, Any] = None) -> str:
        """按平台字段生成 frontmatter YAML 块。"""
        NL = chr(10)
        tags = [str(t).strip() for t in (tags or []) if str(t).strip()]
        lines = ["---", "platform: " + self.platform,
                 'title: "' + str(title or "").replace('"', '\"') + '"',
                 "status: draft",
                 "created: " + datetime.now().strftime("%Y-%m-%dT%H:%M"),
                 "published: null",
                 "post_url: null"]
        # 平台额外字段(cover/summary/分区 等)
        for f in self.frontmatter_fields:
            if f == "cover":
                lines.append('cover: "![[cover_' + self.cover_suffix + '.png]]"')
            elif f == "summary":
                lines.append('summary: "' + str(summary or "")[:120].replace('"', '\"') + '"')
            elif f == "分区":
                lines.append("分区: " + str((extra or {}).get("分区", "知识")))
            else:
                lines.append(f + ": " + str((extra or {}).get(f, "")))
        lines.append("tags: " + (json.dumps(tags, ensure_ascii=False) if tags else "[]"))
        lines.append("---")
        return NL.join(lines)

    def write_draft(self, title: str, content: str = "", media_files: List[str] = None,
                    summary: str = "", tags: List[str] = None,
                    extra: Dict[str, Any] = None) -> Dict[str, Any]:
        """写入草稿: 生成 frontmatter + 正文, 复制图片到 assets/, 视频相对路径引用。

        media_files: 源文件路径列表(沙箱内). 图片(<10MB)复制进 assets/;
                     视频(>=10MB 或 .mp4)用相对路径引用不复制。
        返回 {success, path, rel_path, media: [{name, type, action}]}.
        """
        try:
            root = _vault_root()
            d = root / "草稿箱" / self.platform
            assets = d / "assets"
            d.mkdir(parents=True, exist_ok=True)
            assets.mkdir(parents=True, exist_ok=True)
            fname = datetime.now().strftime("%Y-%m-%d") + "-" + _sanitize_filename(title) + ".md"
            fpath = d / fname
            fm = self._frontmatter(title, summary, tags, extra)
            body = str(content or "")[:20000]
            # 媒体处理
            media_info = []
            media_body = []
            for mf in (media_files or []):
                try:
                    src = Path(mf)
                    if not src.exists():
                        media_info.append({"name": src.name, "action": "missing", "path": str(mf)})
                        continue
                    sz = src.stat().st_size
                    is_video = src.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv", ".webm")
                    if is_video or sz >= 10 * 1024 * 1024:
                        # 视频/大文件: 相对路径引用, 不复制
                        media_info.append({"name": src.name, "type": "video" if is_video else "large",
                                           "action": "reference", "path": "../assets/" + src.name})
                        media_body.append(f"视频文件: ![[../assets/{src.name}]]")
                    else:
                        # 图片/小文件: 复制进 assets/
                        dst = assets / src.name
                        shutil.copy2(src, dst)
                        media_info.append({"name": src.name, "type": "image",
                                           "action": "copied", "path": str(dst)})
                        media_body.append(f"![[{src.name}]]")
                except Exception as e:
                    media_info.append({"name": str(mf), "action": "error", "error": str(e)})
            media_txt = (chr(10) + chr(10) + chr(10).join(media_body)) if media_body else ""
            note_txt = (chr(10) + chr(10) + "> 媒体说明: " + self.media_note) if self.media_note else ""
            fpath.write_text(fm + chr(10) + chr(10) + body + media_txt + note_txt, encoding="utf-8")
            return {"success": True, "path": str(fpath),
                    "rel_path": str(fpath.relative_to(root)), "media": media_info}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_draft(self, draft_path: str, content: str = "", title: str = "") -> Dict[str, Any]:
        """就地更新已存在的草稿(2026-09-06): 保留原 frontmatter(created/cover/分区/发布信息),
        替换正文为 content。write_draft 是「新建」语义(日期前缀文件名)无法改已有草稿 —
        「修改/调整草稿」任务必须走这里, 否则会生成新日期文件造成假完成。

        draft_path: vault 相对路径或绝对路径(如 草稿箱/抖音/xxx.md 或 list_drafts 返回的 path)。
        返回 {success, path, rel_path, changed(内容是否真的变了)}。
        """
        try:
            root = _vault_root()
            p = Path(draft_path)
            if not p.is_absolute():
                p = root / draft_path
            if not p.exists():
                p2 = root / "草稿箱" / self.platform / str(draft_path).split("/")[-1]
                if p2.exists():
                    p = p2
                else:
                    return {"success": False, "error": "草稿不存在: " + str(draft_path)}
            orig = p.read_text(encoding="utf-8")
            fm = ""
            body = orig
            if orig.startswith("---"):
                end = orig.find(chr(10) + "---", 3)
                if end > 0:
                    fm = orig[:end + 4]
                    body = orig[end + 4:]
            new_body = str(content or "").strip()[:20000]
            if title and fm:
                import re as _re_up
                fm = _re_up.sub(r'(?m)^title: ".*"$', 'title: "' + str(title).replace('"', '\\"') + '"', fm)
            new_txt = (fm + chr(10) + chr(10) + new_body) if fm else new_body
            p.write_text(new_txt, encoding="utf-8")
            changed = new_txt != orig
            return {"success": True, "path": str(p),
                    "rel_path": str(p.relative_to(root)), "changed": changed}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def mark_published(self, draft_path: str, post_url: str = "") -> Dict[str, Any]:
        """发布后更新 frontmatter: status=published, published=now, post_url。"""
        try:
            root = _vault_root()
            p = Path(draft_path)
            if not p.is_absolute():
                p = root / p
            if not p.exists():
                return {"success": False, "error": "草稿不存在: " + str(draft_path)}
            txt = p.read_text(encoding="utf-8")
            # 替换 frontmatter 字段
            now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M")
            txt = txt.replace("status: draft", "status: published")
            txt = txt.replace("published: null", "published: " + now_iso)
            if post_url:
                txt = txt.replace('post_url: null', 'post_url: \"' + str(post_url) + '\"')
            p.write_text(txt, encoding="utf-8")
            # 移入 已发布/{platform}/
            pub_dir = root / "已发布" / self.platform
            pub_dir.mkdir(parents=True, exist_ok=True)
            dst = pub_dir / p.name
            if p.parent != dst.parent:
                shutil.move(str(p), str(dst))
            return {"success": True, "path": str(dst), "status": "published"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_drafts(self, status: str = "draft") -> List[Dict[str, Any]]:
        """列出草稿箱中指定状态的草稿(按修改时间倒序)。"""
        root = _vault_root()
        d = root / "草稿箱" / self.platform
        out = []
        if not d.exists():
            return out
        for f in sorted(d.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                txt = f.read_text(encoding="utf-8", errors="ignore")
                st = "draft"
                if "status: published" in txt:
                    st = "published"
                if status and st != status:
                    continue
                out.append({"name": f.name, "path": str(f),
                            "rel_path": str(f.relative_to(root)),
                            "status": st, "mtime": f.stat().st_mtime})
            except Exception:
                continue
        return out

    def archive_media(self, files: List[str], subdir: str = "assets",
                      sandbox_base: str = "") -> Dict[str, Any]:
        """归档媒体文件到 草稿箱/{platform}/{subdir}/ (2026-09-07)。

        Agent 不知道 vault 物理路径 — 归档一律走这里, 不要读源码找路径。
        支持视频/图片/音频(全部复制, 非引用)。返回 vault 相对路径供草稿标注。
        files: 源文件路径列表(绝对, 或相对 sandbox_base; handler 层会拼沙箱 base)。
        sandbox_base: 可选沙箱根 — 相对路径拼这里(兜底, 通常由 handler 传绝对路径)。
        """
        try:
            root = _vault_root()
            d = root / "草稿箱" / self.platform
            assets = d / subdir
            assets.mkdir(parents=True, exist_ok=True)
            archived = []
            missing = []
            errors = []
            for mf in (files or []):
                try:
                    src = Path(str(mf))
                    if not src.is_absolute():
                        # 相对路径: 拼 sandbox_base(handler 传绝对路径; 兜底尝试沙箱根/项目根)
                        _sb_am2 = Path(sandbox_base) if sandbox_base else Path(".")
                        cand = _sb_am2 / src
                        if not cand.exists():
                            cand2 = Path.cwd() / src
                            if cand2.exists():
                                cand = cand2
                        src = cand
                    if not src.exists():
                        missing.append(str(mf))
                        continue
                    dst = assets / src.name
                    if dst.exists():
                        dst = assets / (src.stem + "_dup" + src.suffix)
                    shutil.copy2(src, dst)
                    archived.append({
                        "name": dst.name, "type": (src.suffix or "file").lstrip(".").lower(),
                        "bytes": dst.stat().st_size,
                        "vault_rel": str(dst.relative_to(root)),
                        "embed": "!" + chr(91) + dst.name + chr(93),
                    })
                except Exception as e:
                    errors.append({"name": str(mf), "error": str(e)[:120]})
            return {"success": True, "platform": self.platform, "subdir": subdir,
                    "dir_vault_rel": "草稿箱/" + self.platform + "/" + subdir,
                    "archived": archived, "count": len(archived),
                    "missing": missing, "errors": errors}
        except Exception as e:
            return {"success": False, "error": str(e)}
