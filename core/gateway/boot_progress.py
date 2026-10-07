# -*- coding: utf-8 -*-
"""起服「准备中」之可读读数（一处定形 · pm_1616 令一~令四 · 技术总监席 f202f89 · 2026-10-07）。

病（老板一手 · pm_1616）：净机首启须下向量模型（all-MiniLM-L6-v2 · 约 79 MB ⇒ 2 到 4 分钟）
期间页面 / 健康端唯 status=starting 一词 ⇒ 用户不知在等什么、还要等多久 ⇒ 判「不能用」。

本模块 ＝ **纯状态机 ＋ 度器**（⛔ Flask ／ ⛔ chroma ／ ⛔ 出网）：
  * 相（phase）之序由 boot **显式**设立（一处定形 · ⛔ 猜）。
  * 下模型之进度唯自「缓存件之实字节」量（⛔ 钩库内）；总长唯自 env PA_ONNX_TOTAL_BYTES
    ⇒ 量不得则**明书「不可量」**（承「界面态显真读数」· ⛔ 猜）。
  * 态三：starting | ready | failed；failed 必附「因 ＋ 去处」（承「凡不可用必有因＋去处」）。

以何形调用（判通 / 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_boot_progress_1616.py -q
"""
import os
import threading
import time

ONNX_TOTAL_ENV = "PA_ONNX_TOTAL_BYTES"


def onnx_cache_path():
    """chromadb 默认 EF（ONNX MiniLM）之缓存件之径 —— 一处定形（与库内 Path.home() 同源）。"""
    return os.path.join(os.path.expanduser("~"), ".cache", "chroma", "onnx_models",
                        "all-MiniLM-L6-v2", "onnx.tar.gz")


def _file_bytes(path):
    try:
        if path and os.path.isfile(path):
            return int(os.path.getsize(path))
    except OSError:
        pass
    return None


def download_face(path, total_bytes=None, spent_s=None):
    """下模型之面（纯函数 · 便于正反控）—— 量不得 ⇒ note 明书「不可量」。"""
    got = _file_bytes(path)
    tot = total_bytes
    if not tot:
        v = (os.environ.get(ONNX_TOTAL_ENV) or "").strip()
        tot = int(v) if v.isdigit() else None
    d = {"measured": got is not None, "path": path, "done_bytes": got, "total_bytes": tot,
         "frac": None, "eta_s": None,
         "note": ("" if got is not None else "不可量（缓存件未见 ⇒ ⛔ 知进度）")}
    if got is not None and tot and tot > 0 and got > 0:
        frac = min(1.0, float(got) / float(tot))
        d["frac"] = round(frac, 4)
        if got >= tot:
            d["note"] = "已毕（缓存件齐）"
        elif spent_s and spent_s > 0:
            d["eta_s"] = int(round(float(spent_s) * (1.0 - frac) / frac))
    return d


class BootProgress(object):
    """起服之进度（唯内存 · 线程安 —— 门先开之监听线程亦读之）。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._t0 = None
        self._state = "starting"
        self._phase = ""
        self._phase_at = None
        self._phases = []
        self._failed = None
        self._dl_path = None
        self._dl_total = None
        self._dl_at = None

    def reset(self):
        with self._lock:
            self._t0 = None
            self._state = "starting"
            self._phase = ""
            self._phase_at = None
            self._phases = []
            self._failed = None
            self._dl_path = None
            self._dl_total = None
            self._dl_at = None

    def begin(self, phases=None):
        """起 —— 立相之序（一处定形）。"""
        with self._lock:
            self._t0 = time.time()
            self._state = "starting"
            self._phase = ""
            self._phase_at = None
            self._failed = None
            self._phases = [{"name": str(n), "state": "pending", "at_s": None} for n in (phases or [])]

    def set_phase(self, name):
        """入相 —— 前相自动收为 done（⛔ 回调散落）。"""
        now = time.time()
        with self._lock:
            if self._t0 is None:
                self._t0 = now
            for it in self._phases:
                if it["state"] == "running":
                    it["state"] = "done"
            self._phase = str(name or "")
            self._phase_at = now
            for it in self._phases:
                if it["name"] == self._phase:
                    it["state"] = "running"
                    it["at_s"] = round(now - self._t0, 1)
                    break
            else:
                if self._phase:
                    self._phases.append({"name": self._phase, "state": "running",
                                         "at_s": round(now - self._t0, 1)})

    def set_download(self, path=None, total_bytes=None):
        """立下模型之度点（其进度唯自件之实字节）。"""
        with self._lock:
            self._dl_path = str(path) if path else None
            self._dl_total = int(total_bytes) if total_bytes else None
            self._dl_at = time.time()

    def mark_ready(self):
        now = time.time()
        with self._lock:
            if self._t0 is None:
                self._t0 = now
            for it in self._phases:
                if it["state"] in ("running", "pending"):
                    it["state"] = "done"
            self._phase = "ready"
            self._state = "ready"

    def fail(self, reason, hint=""):
        """失败之显形 —— 必附「因 ＋ 去处」（承「凡不可用必有因＋去处」）。"""
        with self._lock:
            self._state = "failed"
            self._failed = {"reason": str(reason or "未知之因"), "hint": str(hint or "")}

    def snapshot(self):
        """面（唯读数 · ⛔ 副作用）。"""
        now = time.time()
        with self._lock:
            elapsed = None if self._t0 is None else round(now - self._t0, 1)
            phase_since = None if self._phase_at is None else round(now - self._phase_at, 1)
            spent = None if self._dl_at is None else (now - self._dl_at)
            done_n = len([x for x in self._phases if x["state"] == "done"])
            tot_n = len(self._phases)
            out = {
                "state": self._state,
                "phase": self._phase,
                "since_s": elapsed,
                "phase_since_s": phase_since,
                "phases_done": done_n,
                "phases_total": tot_n,
                "phases": [dict(x) for x in self._phases],
                "failed": dict(self._failed) if self._failed else None,
                "download": download_face(self._dl_path, self._dl_total, spent),
            }
            out["progress"] = 100 if self._state == "ready" else int(round(100.0 * done_n / (tot_n or 1)))
            return out


boot_progress = BootProgress()
