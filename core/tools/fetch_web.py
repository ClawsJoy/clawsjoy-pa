"""fetch_web 工具插件 — 网络抓取(只读)

移植自 Harness web_fetch 设计 + 复用 OS _is_private_host SSRF 守卫:
- http/https only + URL ≤2048 + 无凭据
- SSRF 拦截: localhost/内网/回环/链路本地(含 DNS 解析后校验)
- 同源重定向 ≤5(跨源/私网目标不自动跟随)
- 响应 ≤500KB(流式读取截断, 不无限下载)
- 超时 30s(theverge 等站点 20s 不够)
- 显式 User-Agent
- content-type: html → 去标签取文本; text → 直通(均截断 10000 字符返回)

安全边界对齐 fetch_web schema 描述: 仅 http/https 公网, 禁止 localhost/内网。
"""
import re
import urllib.parse

from core.tools.base import ToolPlugin
from core.lib.gateway_helpers import _is_private_host, _html_to_text

MAX_URL_LEN = 2048
MAX_RESPONSE_BYTES = 500 * 1024  # 500KB
FETCH_TIMEOUT = 30  # theverge.com 等慢站点 20s 不够 → 30s
MAX_REDIRECTS = 5
MAX_OUTPUT_CHARS = 10000
USER_AGENT = "clawsjoy-v9-bot/1.0 (+https://clawsjoy.com)"

REDIRECT_STATUS = {301, 302, 303, 307, 308}

FETCH_WEB_SCHEMA = {
    "type": "function",
    "function": {
        "name": "fetch_web",
        "strict": True,
        "description": "获取外部网页原始内容(HTML/JSON/文本直通)，仅适合服务端渲染的静态页面/API/数据接口；JS 动态渲染的 SPA 页面会拿到空壳，请改用 playwright_browser。返回前 10000 字符。仅允许 http/https 公网地址，禁止 localhost/内网地址。",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "url": {"type": "string", "description": "目标网页 URL(http/https)"},
            },
            "required": ["url"],
        },
    },
}


def _is_fetchable_content_type(content_type: str) -> bool:
    mime = (content_type or "").split(";")[0].strip().lower()
    if not mime:
        return False
    if "html" in mime or mime.startswith("text/"):
        return True
    return mime in ("application/json", "application/xml") or mime.endswith("+json") or mime.endswith("+xml")


class FetchWebPlugin(ToolPlugin):
    name = "fetch_web"
    quota = 10
    schema = FETCH_WEB_SCHEMA

    def execute(self, args: dict, ctx) -> dict:
        import requests as _requests

        url = str((args or {}).get("url") or "").strip()
        # ---- URL 校验(纯逻辑, 无网络) ----
        if not url:
            return {"success": False, "error": "missing required param: url"}
        if len(url) > MAX_URL_LEN:
            return {"success": False, "error": f"URL exceeds the maximum length of {MAX_URL_LEN}"}
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as exc:
            return {"success": False, "error": f"invalid URL: {exc}"}
        if parsed.scheme not in ("http", "https"):
            return {"success": False, "error": f"unsupported URL scheme {parsed.scheme!r} (only http/https are allowed)"}
        if parsed.username or parsed.password:
            return {"success": False, "error": "credentials in URLs are not allowed"}
        if _is_private_host(parsed.hostname or ""):
            return {"success": False, "error": "localhost/内网地址不允许访问"}

        # ---- 传输: 同源重定向 ≤5 + 大小限制 + 超时 ----
        current = parsed
        redirects = 0
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,text/plain,application/json,application/xml,*/*;q=0.8",
            # 请求非压缩编码: resp.raw 直接读明文(避免 gzip 字节误当文本; 仍兜底解压)
            "Accept-Encoding": "identity",
        }
        try:
            while True:
                try:
                    resp = _requests.get(current.geturl(), headers=headers, timeout=FETCH_TIMEOUT,
                                         allow_redirects=False, stream=True)
                except _requests.exceptions.Timeout:
                    return {"success": False, "error": f"timeout after {FETCH_TIMEOUT}s"}
                except _requests.exceptions.RequestException as exc:
                    return {"success": False, "error": f"request failed: {exc}"}

                if resp.status_code in REDIRECT_STATUS:
                    resp.close()
                    redirects += 1
                    if redirects > MAX_REDIRECTS:
                        return {"success": False, "error": f"exceeded the maximum of {MAX_REDIRECTS} redirects"}
                    location = resp.headers.get("Location", "")
                    if not location:
                        return {"success": False, "error": f"redirect response (HTTP {resp.status_code}) without a Location header"}
                    next_url = urllib.parse.urljoin(current.geturl(), location)
                    try:
                        next_parsed = urllib.parse.urlparse(next_url)
                    except Exception:
                        return {"success": False, "error": "redirect to invalid URL"}
                    if next_parsed.scheme not in ("http", "https"):
                        return {"success": False, "error": "redirect to unsupported scheme"}
                    if next_parsed.username or next_parsed.password:
                        return {"success": False, "error": "redirect with credentials is not allowed"}
                    # 跨源重定向不自动跟随(与 Harness web_fetch 一致)
                    if (next_parsed.hostname or "").lower() != (current.hostname or "").lower():
                        return {"success": False,
                                "error": f"cross-origin redirect to {next_parsed.netloc} is not followed automatically; retry against that URL directly"}
                    # 重定向目标同样做 SSRF 检查
                    if _is_private_host(next_parsed.hostname or ""):
                        return {"success": False, "error": "redirect target is localhost/内网地址"}
                    current = next_parsed
                    continue

                # ---- 非重定向: 校验 content-type + 大小限制 + 读 body ----
                content_type = resp.headers.get("Content-Type", "") or ""
                try:
                    with resp:
                        data = resp.raw.read(MAX_RESPONSE_BYTES + 1)
                except Exception as exc:
                    return {"success": False, "error": f"read failed: {exc}"}
                truncated_bytes = len(data) > MAX_RESPONSE_BYTES
                if truncated_bytes:
                    data = data[:MAX_RESPONSE_BYTES]

                # 兜底: 服务器忽略 identity 仍返回 gzip 时解压(再按大小截断)
                enc = (resp.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    try:
                        import gzip as _gzip
                        data = _gzip.decompress(data)
                        if len(data) > MAX_RESPONSE_BYTES:
                            data = data[:MAX_RESPONSE_BYTES]
                            truncated_bytes = True
                    except Exception:
                        return {"success": False, "error": "gzip 解压失败"}

                if not _is_fetchable_content_type(content_type):
                    return {"success": False, "error": f"unsupported content type {content_type or 'unknown'!r}"}
                try:
                    text = data.decode("utf-8", errors="replace")
                except Exception:
                    text = ""

                if "html" in content_type.lower():
                    content = _html_to_text(text, limit=MAX_OUTPUT_CHARS)
                else:
                    content = text
                content = re.sub(r"[ \t\r\f\v]+", " ", content).strip()
                truncated_chars = len(content) > MAX_OUTPUT_CHARS
                content = content[:MAX_OUTPUT_CHARS]

                return {
                    "success": True,
                    "url": current.geturl(),
                    "status_code": resp.status_code,
                    "content_type": content_type,
                    "content": content,
                    "truncated": truncated_bytes or truncated_chars,
                    "length": len(content),
                }
        except Exception as exc:
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}
