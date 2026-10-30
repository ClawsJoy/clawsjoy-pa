"""pa_run_worker.py -- 独立 subprocess worker（P0-2c-fix）.

由 routes/v9_chat.py::_chat_entry_runner 以 subprocess 调起；**不重入 Flask**：
本进程只 urllib POST http://127.0.0.1:<port>/v9/agent/chat（stream=False），
把结果以**单行 JSON**写到 stdout：

    {"status": "done"|"failed", "output": <chat payload>, "error": "..."}

退出码：0 = done ／ 1 = failed（含 HTTP/JSON/超时）。
只读、无模型依赖、无 Flask import；stdout 唯 JSON（诊断走 stderr）。
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="pa_run_worker.py", description="PA chat 子进程 worker")
    ap.add_argument("--port", default="5102", help="本机网关端口（默认 5102）")
    ap.add_argument("--user", default="default", help="user_id")
    ap.add_argument("--session", default="default", help="session_id")
    ap.add_argument("--model", default="", help="模型名（可空）")
    ap.add_argument("--task", required=True, help="任务原文")
    ap.add_argument("--timeout", type=float, default=60.0, help="HTTP 超时秒")
    return ap.parse_args(argv)


def _emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + chr(10))
    sys.stdout.flush()


def main(argv=None):
    args = _parse_args(argv)
    if args.timeout <= 0:
        _emit({"status": "failed", "output": None, "error": "timeout must be > 0"})
        return 1
    url = f"http://127.0.0.1:{str(args.port)}/v9/agent/chat"
    body = {
        "user_id": args.user,
        "session_id": args.session,
        "model": args.model,
        "messages": [{"role": "user", "content": args.task}],
        "stream": False,
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=float(args.timeout)) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raw = ""
        try:
            raw = exc.read().decode("utf-8", "replace")[:2000]
        except Exception:  # noqa: BLE001
            pass
        _emit({"status": "failed", "output": None, "error": f"chat HTTP {exc.code}: {raw[:300]}"})
        return 1
    except Exception as exc:  # noqa: BLE001
        _emit({"status": "failed", "output": None, "error": f"chat transport: {type(exc).__name__}: {str(exc)[:300]}"})
        return 1
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001
        _emit({"status": "failed", "output": None, "error": "chat non-json: " + str(raw)[:300]})
        return 1
    ok = True
    if isinstance(payload, dict):
        ok = payload.get("ok", payload.get("success", True))
    if ok:
        _emit({"status": "done", "output": payload, "error": ""})
        return 0
    err = ""
    if isinstance(payload, dict):
        err = str(payload.get("error") or payload.get("message") or "chat failed")
    _emit({"status": "failed", "output": payload, "error": err[:300]})
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
