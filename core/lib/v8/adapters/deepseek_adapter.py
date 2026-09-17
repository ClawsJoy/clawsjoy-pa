#!/usr/bin/env python3
"""DeepSeek API 适配器（OpenAI 兼容格式）"""

import requests

from . import BaseAdapter

# ProxyError 防御(2026-08-24): requests 默认 trust_env=True 会继承进程 HTTP(S)_PROXY,
# 若启动 shell 残留 http_proxy=http://127.0.0.1:7890 且本地代理未开 → ProxyError。
# 强制无代理: DeepSeek API 必须直连(国内可直连, 不走代理)。
_DS_SESSION = requests.Session()
_DS_SESSION.trust_env = False  # 忽略环境代理变量
_DS_SESSION.headers.update({"Content-Type": "application/json"})

# 批157 · 402（余额不足）专项重试策略 —— 与「参数/鉴权类 4xx」区分对待：
#   402 是**短暂**状态（充值 / 配额刷新后即恢复），而 400/401/403 重试无意义。
#   默认：最多 8 次、退避 1/2/4/8/16/32/60s（封顶 60s）、**总等待预算 5 分钟**（老板口径 5–10 次 / 上限 5 分钟）。
#   非 402 路径**完全不变**（4xx 不重试；429/5xx 仍走原来的 3 次 2/4/8s）。
import os as _os_rt402

_R402_MAX_ATTEMPTS = int(_os_rt402.getenv("DS402_MAX_ATTEMPTS", "8"))
_R402_TOTAL_BUDGET_S = float(_os_rt402.getenv("DS402_TOTAL_BUDGET_S", "300"))


def keep_last_reasoning(messages):
    """L1+Q2(2026-09-05) + 2026-09-06 修复: 发送前只保留「工具轮必需」的 reasoning_content。

    DeepSeek thinking 实测规则:
      - 带 tool_calls 的 assistant 必须携带 reasoning_content(工具轮续跑必需, 否则
        400 "reasoning must be passed back");
      - 纯文本收尾 assistant(无 tool_calls)的 reasoning_content 属于「已完成 thinking
        会话」, 后面若接新 user 则是新会话 → 带旧 reasoning 发过去 → 400
        "reasoning_content must be passed back"(前端恢复旧上下文会带多条旧 reasoning)。
    故: 只保留「带 tool_calls 的 assistant」的 reasoning; 所有纯文本 assistant 的
    reasoning 一律剥离(事件层仍全量保留, derive 每轮重建)。
    """
    msgs = list(messages or [])
    for i in range(len(msgs)):
        _m = msgs[i]
        if _m.get("role") != "assistant" or "reasoning_content" not in _m:
            continue
        if _m.get("tool_calls"):
            continue  # 保留: 工具轮 reasoning(续跑必需)
        m = dict(_m)
        m.pop("reasoning_content", None)
        msgs[i] = m
    return msgs


def _sanitize_for_api(messages):
    """2026-09-06 根治: 发送前强制净化, 保证任何上游路径产生的 messages 都满足 DeepSeek 约束。

    实测规则:
      1) tool_calls assistant 必须带 reasoning_content 键(值可为空串; 无键 400);
      2) tool 消息必须紧跟带匹配 tool_calls 的 assistant(孤儿 tool 400);
      3) 纯文本 assistant 的 reasoning_content 属已完成会话, 剥离防另一类 400。
    本函数是发送层兜底 — 上游(derive/finalize/回退内存)任何漏网消息在此修正。
    """
    msgs = [dict(m) for m in (messages or [])]
    # 收集有效 tool ids(有 assistant tool_calls 引用 + 有 tool result)
    tool_ids = set()
    asst_tool_ids = set()
    for m in msgs:
        if m.get("role") == "tool" and m.get("tool_call_id"):
            tool_ids.add(m.get("tool_call_id"))
    for m in msgs:
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                if isinstance(tc, dict) and tc.get("id"):
                    asst_tool_ids.add(tc["id"])
    valid_tool_ids = tool_ids & asst_tool_ids
    out = []
    for m in msgs:
        role = m.get("role")
        if role == "assistant":
            tcs = m.get("tool_calls")
            if tcs:
                # 只保留有 tool result 的 tool_calls
                keep = [tc for tc in tcs if isinstance(tc, dict) and tc.get("id") in valid_tool_ids]
                if not keep:
                    nm = dict(m)
                    nm.pop("tool_calls", None)
                    nm.pop("reasoning_content", None)  # 无工具轮的纯文本
                    out.append(nm)
                    continue
                nm = dict(m)
                nm["tool_calls"] = keep
                # 关键: tool_calls assistant 必须带 reasoning_content 键(str, 可空串)
                rc = nm.get("reasoning_content")
                nm["reasoning_content"] = rc if isinstance(rc, str) else ""
                out.append(nm)
            else:
                nm = dict(m)
                nm.pop("reasoning_content", None)  # 纯文本剥离 reasoning
                out.append(nm)
        elif role == "tool":
            if m.get("tool_call_id") in valid_tool_ids:
                out.append(m)
            # 孤儿 tool 丢弃
        else:
            out.append(m)
    return out


class DeepSeekAdapter(BaseAdapter):
    endpoint = "https://api.deepseek.com/chat/completions"

    def __init__(self, api_key: str = "", model: str = "", endpoint: str = "", **kwargs):
        super().__init__(api_key=api_key, model=model, **kwargs)
        if endpoint:
            self.endpoint = endpoint

    def execute(self, prompt: str, system_prompt: str = "", history: list = None) -> dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        try:
            resp = _DS_SESSION.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model or "deepseek-v4-flash",
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                timeout=180,  # 2026-08-26 读超时统一 180s(长上下文 Read timed out 修复)
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                return {"success": True, "content": content, "tokens": tokens, "model": self.model}
            else:
                return {
                    "success": False,
                    "content": f"API错误: {resp.status_code} - {resp.text[:500]}",
                    "tokens": 0,
                    "model": self.model,
                }
        except Exception as e:
            return {"success": False, "content": f"请求失败: {e}", "tokens": 0, "model": self.model}

    def execute_json(self, prompt: str, system_prompt: str = "") -> dict:
        """JSON Output 模式"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = _DS_SESSION.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model or "deepseek-v4-flash",
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                    "max_tokens": 800,
                },
                timeout=180,  # 2026-08-26 读超时统一 180s(长上下文 Read timed out 修复)
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                return {"success": True, "content": content, "tokens": tokens, "model": self.model}
            return {"success": False, "content": f"API错误: {resp.status_code} - {resp.text[:500]}", "tokens": 0}
        except Exception as e:
            return {"success": False, "content": str(e), "tokens": 0}

    def execute_with_tools(
        self,
        messages: list,
        tools: list,
        user_id: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        thinking: bool = False,
    ) -> dict:
        # L1(2026-09-05): 发送前只保留最近一条 reasoning, 旧推理不进输入上下文(事件层仍保留)
        messages = keep_last_reasoning(messages)
        # 2026-09-06 根治: 发送前强制净化(任何上游漏网消息在此修正, 见 _sanitize_for_api)
        messages = _sanitize_for_api(messages)
        body = {
            "model": self.model or "deepseek-v4-flash",
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if thinking:
            body["thinking"] = {"type": "enabled"}
        # #14 P0(2026-08-29): 重试指数退避 — 超时/5xx 重试 3 次(2/4/8s), 避免直接降级
        import time as _t_rt

        _max_retries = 3
        _last_err = ""
        # 批157：402 专项允许「多跑几轮」（余额恢复需要时间）；非 402 路径的轮数仍是 _max_retries
        # —— 把 for 换成 while + 动态上限，**循环体一行未动**（风险最小）。
        _r402_attempts = 0
        _r402_t0 = _t_rt.time()
        _allowed_attempts = _max_retries
        _attempt_rt = -1
        while True:
            _attempt_rt += 1
            if _attempt_rt >= _allowed_attempts:
                break
            try:
                resp = _DS_SESSION.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    # 读超时按模式区分: thinking(max_tokens=8000) 推理时长可达 60s+,
                    # 固定 60s 读超时在长上下文时触发 Read timed out → 放宽到 180s;
                    # 普通模式保持 60s(快速失败, 不拖慢单轮问答)。
                    timeout=(30, 180 if thinking else 60),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    # #18 P0: usage 明细(治费用不明) — input/output/reasoning/cache
                    _usage = data.get("usage", {}) or {}
                    _pd = _usage.get("prompt_tokens_details", {}) or {}
                    _cd = _usage.get("completion_tokens_details", {}) or {}
                    return {
                        "success": True,
                        "data": data,
                        "tokens": tokens,
                        "usage_detail": {
                            "input": _usage.get("prompt_tokens", 0),
                            "output": _usage.get("completion_tokens", 0),
                            "reasoning": _cd.get("reasoning_tokens", 0),
                            "cache": _pd.get("cached_tokens", 0),
                            "total": tokens,
                        },
                    }
                # 批157 · 402 专项重试（**先于**通用 4xx 分支）：
                #   余额不足是短暂状态（充值/配额刷新即恢复），与「参数/鉴权类 4xx」性质不同
                #   ⇒ 指数退避 1/2/4/8/16/32/60s + 最多 _R402_MAX_ATTEMPTS 次 + 总等待 ≤ _R402_TOTAL_BUDGET_S
                #   非 402 的 4xx 行为**保持现状**（下一个分支一行未改）。
                if resp.status_code == 402:
                    _r402_attempts += 1
                    _r402_elapsed = _t_rt.time() - _r402_t0
                    _r402_wait = min(2 ** (_r402_attempts - 1), 60)
                    if _r402_attempts > _R402_MAX_ATTEMPTS or (_r402_elapsed + _r402_wait) > _R402_TOTAL_BUDGET_S:
                        print("[RETRY] 402 达上限（已重试 %d 次 / 累计 %.0fs 未恢复），放弃" % (_r402_attempts - 1, _r402_elapsed))
                        return {
                            "success": False,
                            "error": "API错误: 402 余额不足（已按 402 专项策略重试至上限）- %s" % str(resp.text)[:200],
                        }
                    print("[RETRY] 402 第 %d 次重试，等 %ds（余额恢复后自动继续）" % (_r402_attempts, _r402_wait))
                    _t_rt.sleep(_r402_wait)
                    _allowed_attempts += 1
                    continue
                # 4xx(除429)不重试 — 参数/鉴权错误重试无意义; 429/5xx 重试
                if resp.status_code >= 400 and resp.status_code < 500 and resp.status_code != 429:
                    # 2026-09-06 临时 debug: 400 时 dump 发送的 messages 结构(定位 thinking 400)
                    try:
                        import json as _j_dbg

                        _dump = {
                            "status": resp.status_code,
                            "err": resp.text[:300],
                            "thinking": bool(thinking),
                            "msgs": [
                                {
                                    "i": i,
                                    "role": m.get("role"),
                                    "has_rc": "reasoning_content" in m,
                                    "rc_type": type(m.get("reasoning_content")).__name__
                                    if "reasoning_content" in m
                                    else None,
                                    "rc_head": str(m.get("reasoning_content"))[:60]
                                    if m.get("reasoning_content")
                                    else "",
                                    "has_tc": bool(m.get("tool_calls")),
                                    "tc_n": len(m.get("tool_calls") or []),
                                    "content_head": str(m.get("content") or "")[:40],
                                }
                                for i, m in enumerate(messages)
                            ],
                        }
                        with open("/tmp/ds_400_dump.json", "w", encoding="utf-8") as _f_dbg:
                            _f_dbg.write(_j_dbg.dumps(_dump, ensure_ascii=False, indent=1))
                    except Exception:
                        pass
                    _err_txt = resp.text[:500]
                    # 2026-09-06 根治: 400 自动降级 — reasoning_content 相关 400 表示
                    # 仍有漏网消息(reasoning 键/孤儿 tool), 剥离全部 reasoning 后重发一次,
                    # 避免任务因上游消息构造缺陷直接失败(用户可见的"一模一样"400)。
                    if resp.status_code == 400 and (
                        "reasoning_content" in _err_txt or "must be a response" in _err_txt
                    ):
                        try:
                            _deg = []
                            for _dm in messages:
                                if _dm.get("role") == "assistant":
                                    _dm2 = dict(_dm)
                                    _dm2.pop("reasoning_content", None)
                                    _deg.append(_dm2)
                                else:
                                    _deg.append(_dm)
                            body2 = dict(body)
                            body2["messages"] = _deg
                            body2.pop("thinking", None)  # 降级关 thinking, 彻底避开 reasoning 要求
                            _resp2 = _DS_SESSION.post(
                                self.endpoint,
                                headers={
                                    "Authorization": "Bearer " + str(self.api_key),
                                    "Content-Type": "application/json",
                                },
                                json=body2,
                                timeout=(30, 180),
                            )
                            if _resp2.status_code == 200:
                                _d2 = _resp2.json()
                                return {
                                    "success": True,
                                    "data": _d2,
                                    "tokens": _d2.get("usage", {}).get("total_tokens", 0),
                                    "usage_detail": {},
                                    "degraded": "reasoning_400_strip",
                                }
                            _err_txt = _resp2.text[:500]
                        except Exception:
                            pass
                    return {"success": False, "error": f"API错误: {resp.status_code} - {_err_txt}"}
                # #4 审核修复(2026-08-29 2轮): 429 读 Retry-After header — 支持秒数 + HTTP-date 两种格式
                _ra = ""
                try:
                    _ra = str(resp.headers.get("Retry-After", "") or "").strip()
                except Exception:
                    _ra = ""
                _last_err = f"HTTP {resp.status_code}: {resp.text[:300]}"
                _wait_rt_next = 0
                if resp.status_code == 429 and _ra:
                    if _ra.isdigit():
                        # 秒数格式: Retry-After: 120
                        _wait_rt_next = min(int(_ra), 30)
                    else:
                        # HTTP-date 格式: Retry-After: Wed, 29 Aug 2026 12:00:00 GMT
                        try:
                            from email.utils import parsedate_to_datetime

                            _retry_dt = parsedate_to_datetime(_ra)
                            _wait_rt_next = max(int((_retry_dt - _t_rt.time()).total_seconds()), 1)
                            _wait_rt_next = min(_wait_rt_next, 30)
                        except Exception:
                            _wait_rt_next = 2 * (2**_attempt_rt)  # 解析失败 → 指数退避
                else:
                    _wait_rt_next = 2 * (2**_attempt_rt)  # 指数退避 2/4/8
                if _attempt_rt < _max_retries - 1:
                    print(
                        f"[DS_RETRY] 第{_attempt_rt+1}次失败({_last_err[:80]}), {_wait_rt_next}s 后重试"
                        + (f" (Retry-After={_ra})" if _ra else "")
                    )
                    _t_rt.sleep(_wait_rt_next)
            except Exception as e:
                _last_err = str(e)
        return {"success": False, "error": f"重试{_max_retries}次仍失败: {_last_err}"}
