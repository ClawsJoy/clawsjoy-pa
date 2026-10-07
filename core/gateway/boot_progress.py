# -*- coding: utf-8 -*-
"""起服「准备中」之可读读数（一处定形 · pm_1616 令一~令四 · 技术总监席 f202f89 · 2026-10-07）。

病（老板一手 · pm_1616）：净机首启须下向量模型（all-MiniLM-L6-v2 · 约 79 MB ⇒ 2 到 4 分钟）
期间页面 / 健康端唯 status=starting 一词 ⇒ 用户不知在等什么、还要等多久 ⇒ 判「不能用」。

本模块 ＝ **纯状态机 ＋ 度器**：唯 `snapshot()` ／ `download_face()` 为**纯读**
  （⛔ Flask ／ ⛔ chroma ／ ⛔ 出网 ／ ⛔ 副作用）；唯二出网之处 ＝ **显式调用**之
  `start_download_probe()`（门后 · 后台 · **一次 `HEAD`** · pm_1632 §二.1）。
  * 相（phase）之序由 boot **显式**设立（一处定形 · ⛔ 猜）。
  * 下模型之进度唯自「缓存件之实字节」量（⛔ 钩库内 · 唯读 `st_size`）。
  * **总长之真源**（pm_1632 §二.1 裁 ⒜）＝ **一次 HTTP `HEAD` 之 `Content-Length`**
    （其址唯自**库内之常量** `ONNXMiniLM_L6_V2.MODEL_DOWNLOAD_URL` ⇒ ⛔ 硬编数字 ／ ⛔ 二处各写）；
    探得 ⇒ `total_bytes` ／ `frac` ／ `eta_s` 皆真；⛔ 得（无址 ／ 断网 ／ 超时 ／ 后端未给）
    ⇒ `total_bytes = null` ∧ `note` ＝「总长不可量（后端未给）」（其因另出 `note_why`）——
    **「不可量」之由唯后端 `note` 承**（pm_1637 §三.1 裁：去重 ⇒ 前端唯书「已下 X MB」· 一处定形）。
  * 态三：starting | ready | failed；failed 必附「因 ＋ 去处」（承「凡不可用必有因＋去处」）。

以何形调用（判通 / 断须附）：
  python -X utf8 -B -m pytest tests/unit/test_boot_progress_1616.py tests/unit/test_boot_progress_1632.py -q
"""
import logging
import os
import threading
import time

#: 日志（**一处定形**）—— pm_1643 §一.2：技术因（`note_why`）**须入机器面之「日志」**（⛔ 唯内存）。
_LOG = logging.getLogger(__name__)

ONNX_TOTAL_ENV = "PA_ONNX_TOTAL_BYTES"
#: 「总长不可量」之明书（一处定形 · pm_1632 §二.1）—— 面（web）据此显「已下 X · 总长不可量」。
UNMEASURABLE_TOTAL_NOTE = "总长不可量（后端未给）"
#: 探总长之超时（秒）—— 一次 HEAD（pm_1632 §二.1 守 ⒝）。
ONNX_TOTAL_TIMEOUT = 5.0


def onnx_cache_path():
    """chromadb 默认 EF（ONNX MiniLM）之缓存件之径 —— 一处定形（与库内 Path.home() 同源）。"""
    return os.path.join(os.path.expanduser("~"), ".cache", "chroma", "onnx_models",
                        "all-MiniLM-L6-v2", "onnx.tar.gz")


def onnx_model_url():
    """向量模型之真址 —— **真源 ＝ 库内之常量**（`ONNXMiniLM_L6_V2.MODEL_DOWNLOAD_URL` ·
    一处定形 ⇒ ⛔ 二处各写 ／ ⛔ 硬编）。读不得（库缺 ／ 名变）⇒ `None` ⇒ 明书「总长不可量」。
    ⚠ ⛔ 钩库内（⛔ 猴补 ／ ⛔ 改其行为）—— 唯**读**其常量。
    """
    try:
        from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
        u = str(getattr(ONNXMiniLM_L6_V2, "MODEL_DOWNLOAD_URL", "") or "").strip()
        return u or None
    except Exception:                                            # noqa: BLE001 — 照实降级
        return None


def probe_total_bytes(url=None, timeout=ONNX_TOTAL_TIMEOUT):
    """**一次** `HEAD` 取 `Content-Length`（总长之真源 · pm_1632 §二.1）⇒ `(total, note, why)`。

    守（PM 一手 · 1632 §二.1）：唯一次（缓存归调用者 —— `start_download_probe`）｜有超时 ∧
    **失败 ⛔ 阻**（⛔ 成「准备」之门）｜**⛔ 硬编数字**（其数随上游而变）。
    得 ⇒ `(int, "", "")`；⛔ 得 ⇒ `(None, 「总长不可量（后端未给）」, 其因)` ——
    ⚠ 其辞**唯 canonical 之字**（pm_1637 §三.1 我裁：**「不可量」之由唯后端 `note` 承** ∧ 与前端同族 ⇒
      一处定形）；**其因另出**（`why` · 技术 · ⛔ 混入人话之辞）。
    ⚠ 纯函数（唯出网一次 · ⛔ 改本模块之态）。
    """
    u = str(url or onnx_model_url() or "").strip()
    if not u:
        return None, UNMEASURABLE_TOTAL_NOTE, "⛔ 知模型址"
    try:
        import urllib.request
        with urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=timeout) as r:
            v = r.headers.get("Content-Length")
        n = int(str(v).strip()) if v and str(v).strip().isdigit() else None
        if n and n > 0:
            return n, "", ""
        return None, UNMEASURABLE_TOTAL_NOTE, "后端未给 Content-Length"
    except Exception as e:                                       # noqa: BLE001 — 照实报因
        return None, UNMEASURABLE_TOTAL_NOTE, type(e).__name__



def _file_bytes(path):
    try:
        if path and os.path.isfile(path):
            return int(os.path.getsize(path))
    except OSError:
        pass
    return None


def download_face(path, total_bytes=None, spent_s=None, total_note=None, total_why=None):
    """下模型之面（纯函数 · 便于正反控）—— 量不得 ⇒ note 明书「不可量」；
    **知进度⽽ ⛔ 知总长** ⇒ note 明书「总长不可量（后端未给）」（承 pm_1632 §二.1 · ⛔ 猜）。"""
    got = _file_bytes(path)
    tot = total_bytes
    if not tot:
        v = (os.environ.get(ONNX_TOTAL_ENV) or "").strip()
        tot = int(v) if v.isdigit() else None
    if got is None:
        note = "不可量（缓存件未见 ⇒ ⛔ 知进度）"
    elif not (tot and tot > 0):
        note = total_note or UNMEASURABLE_TOTAL_NOTE
    else:
        note = ""
    d = {"measured": got is not None, "path": path, "done_bytes": got, "total_bytes": tot,
         "frac": None, "eta_s": None, "note": note,
         "note_why": (str(total_why or "") if (got is not None and not (tot and tot > 0)) else "")}
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
        self._dl_note = ""
        self._dl_why = ""
        self._dl_at = None
        self._probe_at = None

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
            self._dl_note = ""
            self._dl_why = ""
            self._dl_at = None
            self._probe_at = None

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
        """立下模型之度点（其进度唯自件之实字节）—— 一处定形。
        ⛔ 传 `total_bytes` ⇒ **保留**已探得者（`start_download_probe`）／ env 之兜底（**⛔ 擦**）。
        """
        with self._lock:
            self._dl_path = str(path) if path else None
            if total_bytes:
                self._dl_total = int(total_bytes)
                self._dl_note = ""
                self._dl_why = ""
            self._dl_at = time.time()

    def start_download_probe(self, url=None, timeout=ONNX_TOTAL_TIMEOUT):
        """**门后之一探**（唯一次 · 后台线程 · **⛔ 阻门** · pm_1632 §二.1）⇒ `bool`（是否起）。

        得 ⇒ 补「总长」之真源（⇒ `frac` ／ `eta_s` 皆真）；⛔ 得 ⇒ 唯立 `note`
        （⛔ 盖已得之 `total`）。重入（已探过）⇒ `False`（**⛔ 每相各取**）。
        """
        with self._lock:
            if self._probe_at is not None:
                return False
            self._probe_at = time.time()

        def _run():
            tot, note, why = probe_total_bytes(url, timeout)
            # ⭐ pm_1643 §一.2（技术因 ⇒ 入机器面）：探之果须入**日志** —— 客服席 ／ 诊断之据
            #   （尤「不可量」之因：`URLError` ／ `TimeoutError` ／「后端未给 Content-Length」）。
            #   ⚠ 日志 ⛔ 阻态（⛔ 成「准备」之门）。
            try:
                if tot:
                    _LOG.info(u"[BOOT_PROGRESS] 总长探得 total_bytes=%s（一次 HEAD · 门后）", tot)
                else:
                    _LOG.info(u"[BOOT_PROGRESS] 总长不可量 note=%s ｜ note_why=%s",
                              note or UNMEASURABLE_TOTAL_NOTE, why or u"（未给）")
            except Exception:                                    # noqa: BLE001 — 日志 ⛔ 阻态
                pass
            with self._lock:
                if tot:
                    self._dl_total = int(tot)
                    self._dl_note = ""
                    self._dl_why = ""
                elif not self._dl_total:
                    self._dl_note = note or UNMEASURABLE_TOTAL_NOTE
                    self._dl_why = why

        threading.Thread(target=_run, daemon=True, name="onnx-head-probe").start()
        return True

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
                "download": download_face(self._dl_path, self._dl_total, spent, self._dl_note,
                                          self._dl_why),
            }
            out["progress"] = 100 if self._state == "ready" else int(round(100.0 * done_n / (tot_n or 1)))
            return out


boot_progress = BootProgress()
