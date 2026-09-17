"""外部数据缓存模块 — 抓取网页、提取元数据、写入 SAG 知识图谱

功能:
1. fetch(url): 下载页面内容，存入 data/research/{domain}/
2. extract_metadata(html): 提取标题、路由、API 路径、关键文本
3. upsert_to_sag(metadata): 写入 code_entities（entity_type='external_page'/'external_api'/'external_route'）
4. query(url): 先查 SAG，未命中再 fetch

依赖: 标准库 urllib（无第三方依赖）+ psycopg2（可选，用于 SAG 读写）
"""

import os
import re
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)

try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None

try:
    from core.lib.code_entity_extractor import CodeEntityExtractor
except Exception:
    try:
        from code_entity_extractor import CodeEntityExtractor
    except Exception:
        CodeEntityExtractor = None

DEFAULT_UA = "Mozilla/5.0 (compatible; ClawsJoyBot/1.0; +https://clawsjoy.dev)"
RESEARCH_ROOT = Path("data/research")
DEFAULT_PROJECT_ID = "default"
KEY_TEXT_LIMIT = 2000
MAX_SAG_ENTITIES = 20


class WebCache:
    """外部数据缓存：抓取 -> 元数据提取 -> SAG 入库 -> 缓存查询"""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._extractor = None
        if CodeEntityExtractor is not None and self.db_url:
            try:
                self._extractor = CodeEntityExtractor(self.db_url)
            except Exception as e:
                logger.warning("[WebCache] CodeEntityExtractor 初始化失败: %s", e)

    # ---------- 1. fetch: 下载页面并存入 data/research/{domain}/ ----------

    def fetch(self, url: str, timeout: int = 30) -> dict:
        """下载页面内容，存入 data/research/{domain}/，返回 {url, html, path, cached}"""
        domain = self._domain_of(url)
        save_dir = RESEARCH_ROOT / domain
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / self._filename_for(url)

        # 本地已有缓存直接复用
        if save_path.exists():
            html = save_path.read_text(encoding="utf-8", errors="ignore")
            logger.info("[WebCache] 命中本地缓存: %s", save_path)
            return {"url": url, "html": html, "path": str(save_path), "cached": True}

        req = Request(url, headers={"User-Agent": DEFAULT_UA})
        try:
            with urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except (URLError, HTTPError, OSError, ValueError) as e:
            logger.error("[WebCache] 下载失败 %s: %s", url, e)
            raise

        save_path.write_text(html, encoding="utf-8")
        logger.info("[WebCache] 已下载并缓存: %s -> %s", url, save_path)
        return {"url": url, "html": html, "path": str(save_path), "cached": False}

    # ---------- 2. extract_metadata: 提取标题、路由、API 路径、关键文本 ----------

    def extract_metadata(self, html: str, url: str = "") -> dict:
        """从 HTML 中提取标题、路由、API 路径与关键文本"""
        metadata: dict = {
            "url": url,
            "title": "",
            "routes": [],
            "api_paths": [],
            "key_text": "",
        }

        # 标题
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if m:
            metadata["title"] = re.sub(r"\s+", " ", m.group(1)).strip()
        if not metadata["title"]:
            m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
            if m:
                metadata["title"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()

        # 路由与 API 路径（从 href/src/action 提取页面内路径）
        base = url or ""
        for href in re.findall(
            r'(?:href|src|action)=["\']([^"\']+)["\']', html, re.I
        ):
            if href.startswith(
                ("http://", "https://", "//", "mailto:", "tel:", "javascript:", "#", "data:")
            ):
                continue
            full = urljoin(base, href) if base else href
            path = urlparse(full).path
            if not path or path == "/":
                continue
            if re.search(r"/api/|/v\d+/|/graphql", path, re.I):
                if path not in metadata["api_paths"]:
                    metadata["api_paths"].append(path)
            else:
                if path not in metadata["routes"]:
                    metadata["routes"].append(path)

        # 关键文本：剔除 script/style/标签后压缩空白
        text = re.sub(
            r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S
        )
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        metadata["key_text"] = text[:KEY_TEXT_LIMIT]

        return metadata

    # ---------- 3. upsert_to_sag: 写入 code_entities ----------

    def upsert_to_sag(
        self, metadata: dict, project_id: str = DEFAULT_PROJECT_ID
    ) -> bool:
        """将页面/API/路由元数据写入 code_entities，返回是否全部成功"""
        if self._extractor is None:
            logger.warning(
                "[WebCache] SAG 写入不可用（需要 DATABASE_URL 且能初始化 CodeEntityExtractor）"
            )
            return False

        url = metadata.get("url", "")
        save_path = metadata.get("save_path", "")
        domain = self._domain_of(url)
        ok = True

        # 页面实体
        page_entity = {
            "entity_type": "external_page",
            "entity_name": url,
            "file_path": save_path,
            "signature": json.dumps(
                {
                    "title": metadata.get("title", ""),
                    "key_text": (metadata.get("key_text") or "")[:500],
                    "fetched_at": datetime.now().isoformat(),
                },
                ensure_ascii=False,
            ),
            "related_entities": list(
                dict.fromkeys(
                    metadata.get("routes", [])[:MAX_SAG_ENTITIES]
                    + metadata.get("api_paths", [])[:MAX_SAG_ENTITIES]
                )
            ),
        }
        ok = self._extractor.upsert_entity(page_entity, project_id) and ok

        # API 实体
        for api in (metadata.get("api_paths") or [])[:MAX_SAG_ENTITIES]:
            api_entity = {
                "entity_type": "external_api",
                "entity_name": f"{domain}{api}",
                "file_path": save_path,
                "signature": json.dumps(
                    {"url": url, "api": api}, ensure_ascii=False
                ),
                "related_entities": [url],
            }
            ok = self._extractor.upsert_entity(api_entity, project_id) and ok

        # 路由实体
        for route in (metadata.get("routes") or [])[:MAX_SAG_ENTITIES]:
            route_entity = {
                "entity_type": "external_route",
                "entity_name": f"{domain}{route}",
                "file_path": save_path,
                "signature": json.dumps(
                    {"url": url, "route": route}, ensure_ascii=False
                ),
                "related_entities": [url],
            }
            ok = self._extractor.upsert_entity(route_entity, project_id) and ok

        return ok

    # ---------- 4. query: 先查本地文件缓存 -> 再查 SAG -> 都未命中才 fetch ----------

    def query(self, url: str) -> dict:
        """先查本地文件缓存，再查 SAG，都未命中才 fetch -> extract -> upsert 后返回"""
        # 1. 本地文件缓存
        local_path = RESEARCH_ROOT / self._domain_of(url) / self._filename_for(url)
        if local_path.exists():
            try:
                html = local_path.read_text(encoding="utf-8", errors="ignore")
                metadata = self.extract_metadata(html, url)
                metadata["save_path"] = str(local_path)
                logger.info("[WebCache] 命中本地文件缓存: %s", url)
                return {
                    "url": url,
                    "source": "local",
                    "metadata": metadata,
                }
            except Exception as e:
                logger.warning("[WebCache] 本地缓存读取失败: %s", e)

        # 2. SAG 缓存
        hit = self._query_sag(url)
        if hit is not None:
            logger.info("[WebCache] 命中 SAG 缓存: %s", url)
            return {
                "url": url,
                "source": "sag",
                "metadata": self._parse_signature(hit),
            }

        # 3. 都未命中才 fetch
        result = self.fetch(url)
        metadata = self.extract_metadata(result["html"], url)
        metadata["save_path"] = result["path"]
        upserted = self.upsert_to_sag(metadata)
        if not upserted:
            logger.warning("[WebCache] SAG 入库失败（不影响本地缓存返回）: %s", url)
        # 第二大脑同步(2026-08-30): 抓取成功的新闻/资料 → 写入 Obsidian vault Clippings/
        # 与 data/research 原始缓存并存; 幂等去重(同 URL 不重复剪藏); 失败不影响主流程
        try:
            self._sync_to_vault_clipping(metadata)
        except Exception as e:
            logger.warning("[WebCache] vault Clippings 同步失败(忽略): %s", e)
        return {"url": url, "source": "fetch", "metadata": metadata}

    def _sync_to_vault_clipping(self, metadata: dict) -> Optional[Path]:
        """把抓取页面写入 Obsidian vault Clippings/ 作为剪藏笔记(第二大脑)。

        frontmatter: type=clipping, source_url, fetched 日期, tags(domain)。
        幂等: 同 URL 已存在剪藏(查 frontmatter source_url) → 跳过。
        vault 不可用/写失败 → 返回 None(不影响 WebCache 主流程)。
        """
        _url = str(metadata.get("url") or "").strip()
        _title = str(metadata.get("title") or "").strip()
        if not _title:
            return None
        # 2026-08-30: 无 og:url/canonical 的缓存页(如机器之心 index) → 用域名兜底 URL
        # (保留域名线索, 仍可剪藏; 幂等用 title 兜底)
        if not _url:
            _dom_hint = metadata.get("source_domain") or ""
            if not _dom_hint:
                _dom_hint = (urlparse(_title).netloc if "http" in _title else "")
            _url = f"https://{_dom_hint}/" if _dom_hint else f"https://research.local/{_title[:20]}"
        _key_text = str(metadata.get("key_text") or "")
        if not _key_text or len(_key_text) < 50:
            return None  # 无实质正文(如 400/反爬页), 不剪藏
        try:
            import yaml as _y_clip
            from core.gateway.precision_inject import _obsidian_cfg, _vault_path
            _cfg = _obsidian_cfg()
            if not _cfg.get("enabled") or not _cfg.get("sync_clippings", True):
                return None
            _root = Path(_vault_path())
            _clip_dir = _root / ( _cfg.get("clippings_dir") or "Clippings")
            _clip_dir.mkdir(parents=True, exist_ok=True)
            # 幂等: 同 URL 已有剪藏 → 跳过
            if _clip_dir.exists():
                for _f in _clip_dir.glob("*.md"):
                    try:
                        _t = _f.read_text(encoding="utf-8", errors="ignore")
                        _in_fm = False
                        if _t.startswith("---"):
                            _fm_part = _t.split("---", 2)[1] if len(_t.split("---", 2)) > 1 else ""
                            _in_fm = _url in _fm_part
                        if f"source_url: {_url}" in _t or _in_fm:
                            return None
                    except Exception:
                        continue
            _safe_title = re.sub(r'[\\/:*?"<>|\n\r\t]+', "_", _title)[:60].strip() or "clipping"
            _fname = f"{_safe_title}.md"
            _fpath = _clip_dir / _fname
            _today = datetime.now().strftime("%Y-%m-%d")
            _domain = (urlparse(_url).hostname or "").replace("www.", "")
            _clip_md = (
                "---" + "\n"
                f"type: clipping\n"
                f"source_url: {_url}\n"
                f"source_domain: {_domain}\n"
                f"clipped: {_today}\n"
                f"tags: [clipping, {_domain}]\n"
                "---\n"
                f"# {_title}\n\n"
                f"> 来源: [{_domain}]({_url})\n\n"
                f"{_key_text}\n"
            )
            if not _fpath.exists():
                _fpath.write_text(_clip_md, encoding="utf-8")
                logger.info("[WebCache] 已剪藏到 vault Clippings: %s", _fname)
            return _fpath
        except Exception as _ce:
            logger.warning("[WebCache] 剪藏失败(忽略): %s", _ce)
            return None

    # ---------- 内部工具 ----------

    def _query_sag(self, url: str) -> Optional[dict]:
        """在 code_entities 中查询 entity_type='external_page' 且 entity_name=url 的实体"""
        if psycopg2 is None or not self.db_url:
            return None
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                "SELECT * FROM code_entities "
                "WHERE project_id = %s AND entity_type = 'external_page' "
                "AND entity_name = %s ORDER BY id DESC LIMIT 1",
                (DEFAULT_PROJECT_ID, url),
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.warning("[WebCache] SAG 查询失败: %s", e)
            return None

    @staticmethod
    def _parse_signature(row: dict) -> dict:
        """将 SAG 行解析为 metadata dict（signature 为 JSON 时还原字段）"""
        metadata = {"url": row.get("entity_name", ""), "title": "", "routes": [], "api_paths": [], "key_text": ""}
        sig = row.get("signature") or ""
        try:
            data = json.loads(sig)
            if isinstance(data, dict):
                metadata["title"] = data.get("title", "")
                metadata["key_text"] = data.get("key_text", "")
                metadata["fetched_at"] = data.get("fetched_at", "")
        except (ValueError, TypeError):
            metadata["key_text"] = str(sig)[:KEY_TEXT_LIMIT]
        return metadata

    @staticmethod
    def _domain_of(url: str) -> str:
        """提取域名（去掉端口），如 https://docs.example.com:8080/x -> docs.example.com"""
        netloc = urlparse(url).netloc
        if not netloc:
            return "unknown"
        return netloc.split(":")[0]

    @staticmethod
    def _filename_for(url: str) -> str:
        """根据 url 生成稳定的缓存文件名：{leaf}_{md5前12位}.html"""
        digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
        path = urlparse(url).path
        leaf = path.rstrip("/").split("/")[-1] or "index"
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", leaf)[:60]
        return f"{safe}_{digest}.html"


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) > 1:
        wc = WebCache()
        result = wc.query(sys.argv[1])
        print(json.dumps(result, ensure_ascii=False, indent=2)[:3000])
    else:
        print("用法: python3 web_cache.py <url>")
