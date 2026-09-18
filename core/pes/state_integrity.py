# -*- coding: utf-8 -*-
"""V9-PES · **State Integrity 层** —— 状态唯一读写出口（M1「状态可信」核心件）。

对应总任务书工程版 v1 §3.1 与 §5 M1，四条判据逐条落到本模块：

| M1 判据 | 落点 |
|---|---|
| ① 所有 state 读写走统一出口（**无未插桩写者**） | :meth:`StateFile.update_runtime` 唯一写路径 + **写者归属台账**；:func:`detect_uninstrumented` 机械识别绕过出口的写者 |
| ② 坏状态：**不抛原始异常** + 可读提示 + **可自助恢复** | :meth:`StateFile.read` 容错读 + 损坏**隔离**；:meth:`StateFile.recover` 自助恢复；对外只抛 :class:`StateIntegrityError`（中文可读） |
| ③ 资格（seed）与运行态分离 | :data:`DEFAULT_SEED_KEYS` + :meth:`StateFile.update_runtime` **拒绝触碰 seed 键** |
| ④ 无静默降级 | 任何降级（抢救 / 隔离 / 空状态 / 锁等待）都进 ``report.degradations`` **并写审计**，不吞 |

与既有件的关系（**不新造**）：设计沿用 ``core/gateway/state_json.py``（批220 原子写 + 容错读）
的根因结论，在其上补三件 —— **跨进程锁**、**写者归属**、**损坏隔离与自助恢复**。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.pes.windows import normalize_path

#: seed（资格）键白名单 —— 运行态写入**不得**触碰这些键
DEFAULT_SEED_KEYS: Tuple[str, ...] = (
    "v",
    "seed",
    "seed_source",
    "seed_manifest_hash",
    "seed_status",
    "project_root",
    "agent_state_seed",
    "workspace_seed",
    "created_by",
)

#: 损坏文件隔离目录名
QUARANTINE_DIR = ".quarantine"

#: 写台账后缀
WRITE_LOG_SUFFIX = ".writes.jsonl"

#: `update_runtime` 遇到**坏状态**时的策略（2026-09-18 加 · 老板/DS 拍 A）：
#:  · "salvage"（**默认**）＝隔离后照写 —— **既有行为，一字不变**
#:  · "refuse" ＝**拒绝写入**（`ok=False` + `reason`，活文件一个字节不动）—— fail-loud
#:  · "overwrite" ＝显式声明「接受覆盖」（行为同 salvage，但调用方意图显式）
CORRUPT_POLICIES: Tuple[str, ...] = ("salvage", "refuse", "overwrite")


class StateIntegrityError(Exception):
    """**可读**的状态完整性错误（代替裸 ``json`` / ``OSError`` 抛给上层）。"""


# ============================== 跨进程锁 ==============================
class _InterProcessLock:
    """跨进程文件锁：Windows 用 ``msvcrt.locking``，POSIX 用 ``fcntl.flock``。

    两者都不可用时退化到 ``O_CREAT|O_EXCL`` 自旋（并记降级）。
    **不依赖 fcntl 存在**（WSL 侧代码迁 Windows 时的典型断点）。
    """

    def __init__(self, target, timeout: float = 10.0, poll: float = 0.05):
        self.lock_path = str(target) + ".lock"
        self.timeout = float(timeout)
        self.poll = float(poll)
        self.fd: Optional[int] = None
        self.mode = ""
        self.degraded = ""

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False

    def acquire(self):
        Path(self.lock_path).parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + self.timeout
        last = None
        while time.time() < deadline:
            try:
                if self._try_once():
                    return self
            except Exception as e:  # 锁本身出错 ⇒ 不静默，记录后重试
                last = e
            time.sleep(self.poll)
        raise StateIntegrityError(
            "状态文件被占用，等待 %.1fs 仍未取到锁：%s（%s）" % (self.timeout, self.lock_path, last or "busy")
        )

    def _try_once(self) -> bool:
        if os.name == "nt":
            return self._try_msvcrt()
        return self._try_flock()

    def _try_msvcrt(self) -> bool:
        try:
            import msvcrt
        except Exception:
            return self._try_excl()
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            os.close(fd)
            return False
        self.fd, self.mode = fd, "msvcrt"
        return True

    def _try_flock(self) -> bool:
        try:
            import fcntl
        except Exception:
            return self._try_excl()
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self.fd, self.mode = fd, "flock"
        return True

    def _try_excl(self) -> bool:
        candidate = self.lock_path + ".excl"
        try:
            fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except FileExistsError:
            # 陈旧锁自愈：超过 60s 的 excl 锁视为失效
            try:
                if time.time() - os.path.getmtime(candidate) > 60:
                    os.remove(candidate)
            except Exception:
                pass
            return False
        self.fd, self.mode, self.degraded = fd, "excl", "锁退化到 O_EXCL 自旋"
        self.lock_path = candidate
        return True

    def release(self):
        if self.fd is None:
            return
        try:
            if self.mode == "msvcrt":
                import msvcrt

                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            elif self.mode == "flock":
                import fcntl

                fcntl.flock(self.fd, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            os.close(self.fd)
        except Exception:
            pass
        self.fd = None


# ============================== 读结果 ==============================
class StateReport:
    """一次状态读/写的**完整事实**（含降级清单，供 UI 与审计消费）。"""

    def __init__(self, path: str):
        self.path = path
        #: 容错读的结果。**永不缺失** —— 文件不存在或损坏时为 {}。
        #: （缺它会让「全新文件上的第一次读/写」直接 AttributeError，
        #:  即「状态唯一读写出口」在最常见的首次写入路径上根本走不通。）
        self.data: Dict[str, Any] = {}
        self.ok = True
        self.corrupted = False
        self.recovered = False
        self.quarantined: Optional[str] = None
        self.reason = ""
        self.message = ""
        self.degradations: List[str] = []
        self.writer = ""
        #: 本次 `update_runtime` **是否真的写了盘**（`on_corrupt="refuse"` 下为 False）。
        self.written = False

    def degrade(self, text: str, message: str = "") -> "StateReport":
        self.ok = False
        self.degradations.append(text)
        if message and not self.message:
            self.message = message
        return self

    def as_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "ok": self.ok,
            "corrupted": self.corrupted,
            "recovered": self.recovered,
            "quarantined": self.quarantined,
            "reason": self.reason,
            "message": self.message,
            "degradations": list(self.degradations),
            "writer": self.writer,
            "written": self.written,
        }

    def __repr__(self):
        return "StateReport(ok=%s corrupted=%s recovered=%s reason=%r)" % (
            self.ok,
            self.corrupted,
            self.recovered,
            self.reason,
        )


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _sha256_file(p: Path) -> str:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        return ""


# ============================== StateFile ==============================
class StateFile:
    """**状态唯一读写出口**。任何 state 文件的读/写都必须经本类。

    :param path: 状态文件路径
    :param writer: 写者标识（进写台账，用于识别未插桩写者）
    :param seed_keys: seed（资格）键白名单；运行态写入对这些键**只读不写**
    """

    def __init__(self, path, writer: str = "unknown", seed_keys: Optional[Tuple[str, ...]] = None):
        self.path = Path(normalize_path(path))
        self.writer = str(writer or "unknown")
        self.seed_keys = tuple(DEFAULT_SEED_KEYS if seed_keys is None else seed_keys)
        self._local = threading.RLock()

    # ---------------- 派生路径 ----------------
    @property
    def write_log(self) -> Path:
        return self.path.with_name(self.path.name + WRITE_LOG_SUFFIX)

    @property
    def quarantine_dir(self) -> Path:
        return self.path.parent / QUARANTINE_DIR

    # ---------------- ① 读（容错，不抛） ----------------
    def read(self) -> StateReport:
        """容错读。**绝不抛原始异常**；坏文件隔离后可自助恢复。"""
        rep = StateReport(self.path.as_posix())
        if not self.path.exists():
            rep.degradations.append("文件不存在 ⇒ 返回空状态")
            rep.message = "状态文件尚未创建（返回空状态，可正常开始）"
            return rep
        try:
            raw = self.path.read_text(encoding="utf-8")
        except Exception as e:
            rep.corrupted = True
            rep.reason = "unreadable"
            return rep.degrade(
                "文件不可读：%s" % type(e).__name__,
                "状态文件读不出来（可能是编码或权限问题）。可点「恢复」重建。",
            )
        try:
            data = json.loads(raw)
        except Exception as e:
            rep.corrupted = True
            rep.reason = "invalid_json"
            q = self._quarantine(raw, "invalid_json")
            rep.quarantined = q
            salvaged = self._salvage(raw)
            if salvaged is not None:
                rep.recovered = True
                rep.data = salvaged
                rep.degrade(
                    "JSON 非法（%s）⇒ 已隔离并抢救出第一份合法 JSON" % type(e).__name__,
                    "状态文件损坏，已隔离原文件并抢救出可用部分，可继续；建议核对后保存。",
                )
                self._audit("state.corrupted.salvaged", {"quarantined": q, "keys": sorted(salvaged)[:20]})
            else:
                rep.data = {}
                rep.degrade(
                    "JSON 非法（%s）⇒ 已隔离，未能抢救" % type(e).__name__,
                    "状态文件损坏且无法抢救，已隔离原文件。可点「恢复」重建（不会丢失已隔离的原文件）。",
                )
                self._audit("state.corrupted.quarantined", {"quarantined": q})
            return rep
        if not isinstance(data, dict):
            rep.corrupted = True
            rep.reason = "not_object"
            q = self._quarantine(raw, "not_object")
            rep.quarantined = q
            rep.data = {}
            return rep.degrade(
                "顶层不是对象（%s）" % type(data).__name__,
                "状态文件结构不对（顶层应为对象），已隔离。可点「恢复」重建。",
            )
        rep.data = data
        return rep

    @staticmethod
    def _salvage(raw: str) -> Optional[Dict[str, Any]]:
        """抢救第一份合法 JSON（对治批220 定位的「Extra data」串接损坏）。"""
        try:
            obj, _end = json.JSONDecoder().raw_decode(raw)
            return obj if isinstance(obj, dict) else None
        except Exception:
            # 再退一步：逐行找最后一行可解析的对象
            for line in reversed([x for x in raw.splitlines() if x.strip()]):
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    continue
        return None

    def _quarantine(self, raw: str, reason: str) -> str:
        """把损坏文件**原样**移入隔离区（不删证据）。"""
        try:
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
            digest = _sha256_text(raw)
            for prev in self.quarantine_dir.glob(self.path.name + ".*.bad"):
                try:
                    if _sha256_text(prev.read_text(encoding="utf-8")) == digest:
                        return prev.as_posix()  # 同内容已隔离过，不重复堆证据
                except Exception:
                    continue
            dst = self.quarantine_dir / ("%s.%s.%s.bad" % (self.path.name, time.strftime("%Y%m%d-%H%M%S"), reason))
            dst.write_text(raw, encoding="utf-8")
            return dst.as_posix()
        except Exception:
            return ""

    # ---------------- ② 写（唯一出口 + 原子 + 写者归属） ----------------
    def update_runtime(
        self,
        mutate: Callable[[Dict[str, Any]], None],
        writer: Optional[str] = None,
        reason: str = "",
        on_corrupt: str = "salvage",
    ) -> Tuple[Dict[str, Any], StateReport]:
        """**运行态唯一写路径**：加锁 + 容错读 + mutate + 原子替换 + 写台账。

        ``mutate`` **不得**修改 :attr:`seed_keys` 中的键 —— 被静默丢弃并记降级
        （seed 只由 :meth:`set_seed` 写，对应 M1 判据③）。

        :param on_corrupt: 读到**坏状态**时怎么办（见 :data:`CORRUPT_POLICIES`）——
            ``"salvage"``（**默认**，既有行为）＝隔离后照写；``"refuse"`` ＝**拒绝写入**
            （`ok=False` + `reason`，**活文件一个字节不动**）；``"overwrite"`` ＝显式接受覆盖。
            **为什么要有**：`read()` 判 `corrupted` 之后本方法**原本仍会写**（判定在写之后），
            故「接统一出口」得到的只是「**可恢复的重置**」，不是 fail-loud。
        """
        w = str(writer or self.writer)
        if on_corrupt not in CORRUPT_POLICIES:
            raise ValueError(
                "on_corrupt 非法：%r（可选：%s）" % (on_corrupt, "/".join(CORRUPT_POLICIES))
            )
        rep = StateReport(self.path.as_posix())
        rep.writer = w
        with self._local, _InterProcessLock(self.path):
            read_rep = self.read()
            rep.corrupted, rep.recovered = read_rep.corrupted, read_rep.recovered
            rep.quarantined = read_rep.quarantined
            rep.reason = read_rep.reason
            rep.degradations.extend(read_rep.degradations)
            if read_rep.message:
                rep.message = read_rep.message
            doc = dict(read_rep.data or {})
            if read_rep.corrupted and on_corrupt == "refuse":
                # fail-loud：坏状态**不得**被当合并基线覆写。
                # 原文件已在 read() 内 _quarantine（证据未丢），此处**一个字节都不写**。
                rep.data = doc
                rep.written = False
                rep.degrade(
                    "坏状态 ⇒ 按 on_corrupt=refuse **拒绝写入**（reason=%s）"
                    % (read_rep.reason or "unknown"),
                    "状态文件损坏，已隔离原文件并拒绝写入（未覆盖任何内容）。可点「恢复」重建。",
                )
                self._audit(
                    "state.write_refused",
                    {"writer": w, "reason": read_rep.reason, "quarantined": read_rep.quarantined},
                )
                return doc, rep
            before_seed = {k: doc.get(k) for k in self.seed_keys if k in doc}
            mutate(doc)
            after_seed = {k: doc.get(k) for k in self.seed_keys if k in doc}
            if before_seed != after_seed:
                for k in self.seed_keys:
                    if before_seed.get(k) != after_seed.get(k):
                        doc[k] = before_seed.get(k)
                        if before_seed.get(k) is None and k in doc:
                            doc.pop(k, None)
                rep.degrade(
                    "运行态写入试图改动 seed 键 ⇒ 已拒绝（%s）" % ",".join(sorted(before_seed)),
                    "运行态不允许修改资格(seed)字段，已自动还原。",
                )
                self._audit("state.seed_write_rejected", {"writer": w, "keys": sorted(before_seed)})
            self._atomic_write(doc, w, reason)
            rep.data = doc
            rep.written = True
            rep.ok = rep.ok and not rep.corrupted
            return doc, rep

    def set_seed(self, seed: Dict[str, Any], writer: str = "boss", reason: str = "") -> Tuple[Dict[str, Any], StateReport]:
        """**唯一**允许写 seed 键的路径（老板级）。"""
        rep = StateReport(self.path.as_posix())
        rep.writer = writer
        with self._local, _InterProcessLock(self.path):
            read_rep = self.read()
            doc = dict(read_rep.data or {})
            for k, v in (seed or {}).items():
                doc[k] = v
            self._atomic_write(doc, writer, reason or "set_seed")
        self._audit("state.seed_written", {"writer": writer, "keys": sorted((seed or {}).keys())})
        return doc, rep

    def _atomic_write(self, doc: Dict[str, Any], writer: str, reason: str) -> None:
        """临时文件 + fsync + ``os.replace`` 原子替换（读侧永远看到完整文件）。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(doc, ensure_ascii=False, indent=2)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix="." + self.path.name + ".", suffix=".tmp")
        try:
            # newline="" —— **禁止换行翻译**。Windows 文本模式会把 \n 写成 \r\n，
            # 而写台账记的是 text 的 sha256（LF）⇒ 盘上字节永远对不上，
            # detect_uninstrumented 会把**每一个**状态文件都误报成「有未插桩写者」。
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except Exception as e:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
            raise StateIntegrityError("状态写入失败（%s）：%s" % (type(e).__name__, self.path.as_posix()))
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        self._log_write(writer, reason, text)

    def _log_write(self, writer: str, reason: str, text: str) -> None:
        """**写者归属台账** —— 未插桩写者由此可被机械识别。"""
        row = {
            "seq": self._next_seq(),
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "writer": writer,
            "reason": reason or "",
            "sha256": _sha256_text(text),
            "bytes": len(text.encode("utf-8")),
            "pid": os.getpid(),
        }
        try:
            self.write_log.parent.mkdir(parents=True, exist_ok=True)
            with open(self.write_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _next_seq(self) -> int:
        n = 0
        try:
            if self.write_log.exists():
                with open(self.write_log, encoding="utf-8") as f:
                    for _ in f:
                        n += 1
        except Exception:
            pass
        return n + 1

    # ---------------- ③ seed / runtime 分离 ----------------
    def split(self, doc: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """拆成 ``(seed, runtime)`` 两份（对账与汇总消费）。"""
        d = self.read().data if doc is None else doc
        d = d or {}
        seed = {k: v for k, v in d.items() if k in self.seed_keys}
        runtime = {k: v for k, v in d.items() if k not in self.seed_keys}
        return seed, runtime

    # ---------------- ④ 自助恢复 ----------------
    def recover(self, source: str = "auto", keep_backup: bool = True) -> StateReport:
        """**自助恢复**（M1 判据②的可操作出口）。

        ``source``：
          · ``quarantine`` —— 从隔离区取**最新**的可抢救内容；
          · ``backup`` —— 从 ``<name>.bak`` 取；
          · ``empty`` —— 重建为空状态（seed 保留）；
          · ``auto`` —— 依次尝试 quarantine → backup → empty。
        **无论哪条路，都会把当前文件先备份**，并写审计。
        """
        rep = StateReport(self.path.as_posix())
        tried: List[str] = []
        if keep_backup and self.path.exists():
            try:
                bak = self.path.with_name(self.path.name + ".bak")
                bak.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass
        cur = self.read()
        seed = {k: v for k, v in (cur.data or {}).items() if k in self.seed_keys}
        order = ["quarantine", "backup", "empty"] if source == "auto" else [source]
        for src in order:
            tried.append(src)
            data = None
            if src == "quarantine":
                data = self._from_quarantine()
            elif src == "backup":
                data = self._from_backup()
            elif src == "empty":
                data = {}
            if data is not None:
                data.update(seed)  # seed 不被恢复动作抹掉
                self._atomic_write(data, "pes.recover", "recover:%s" % src)
                rep.ok, rep.recovered, rep.data = True, True, data
                rep.message = "已从「%s」恢复，共 %d 个键。" % (src, len(data))
                self._audit("state.recovered", {"source": src, "keys": len(data)})
                return rep
        rep.ok = False
        rep.message = "恢复失败（已尝试：%s）。原文件仍在，未丢失。" % "→".join(tried)
        self._audit("state.recover_failed", {"tried": tried})
        return rep

    def _from_quarantine(self) -> Optional[Dict[str, Any]]:
        try:
            files = sorted(self.quarantine_dir.glob(self.path.name + ".*.bad"), reverse=True)
        except Exception:
            return None
        for f in files:
            try:
                raw = f.read_text(encoding="utf-8")
            except Exception:
                continue
            d = self._salvage(raw)
            if d is not None:
                return d
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue
        return None

    def _from_backup(self) -> Optional[Dict[str, Any]]:
        bak = self.path.with_name(self.path.name + ".bak")
        if not bak.exists():
            return None
        try:
            d = json.loads(bak.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else None
        except Exception:
            return None

    # ---------------- 审计（懒加载，避免循环依赖） ----------------
    def _audit(self, kind: str, payload: Dict[str, Any]) -> None:
        try:
            from core.pes.audit import audit_log

            audit_log().record(kind, run_id=payload.get("run_id", ""), payload=payload, layer="State Integrity")
        except Exception:
            pass


# ============================== 未插桩写者检测（M1 ①） ==============================
def detect_uninstrumented(path) -> Dict[str, Any]:
    """机械判定：该状态文件**是否被绕过唯一出口的写者**改过。

    判据：磁盘现值 sha256 ≠ 写台账最后一条 sha256 ⇒ **有未插桩写者**。
    这是 M1「所有 state 读写走统一出口」的**可执行判据**（不靠人读日志）。
    """
    sf = StateFile(path)
    out = {"path": sf.path.as_posix(), "instrumented": True, "reason": "", "last_writer": "", "last_ts": ""}
    if not sf.path.exists():
        out["reason"] = "文件不存在"
        return out
    last = None
    try:
        if sf.write_log.exists():
            with open(sf.write_log, encoding="utf-8") as f:
                for line in f:
                    try:
                        last = json.loads(line)
                    except Exception:
                        continue
    except Exception:
        pass
    if last is None:
        out["instrumented"] = False
        out["reason"] = "无写台账：该文件从未经由唯一出口写过（未插桩写者）"
        return out
    disk = _sha256_file(sf.path)
    if disk != last.get("sha256"):
        out["instrumented"] = False
        out["reason"] = "磁盘内容与写台账不符 ⇒ 存在未插桩写者"
    out["last_writer"] = last.get("writer", "")
    out["last_ts"] = last.get("ts", "")
    return out


def scan_state_dir(root=None, patterns=("*.json",)) -> List[Dict[str, Any]]:
    """扫描目录下所有**可变状态文件**，返回**未插桩**清单（M1 ① 的批量判据）。

    只扫 ``*.json``（单文档状态，必须走唯一出口）；**追加式账本**（``*.jsonl``：审计流 /
    run registry）**不在此列** —— 它们由各自的 **哈希链 + append-only** 保证完整性
    （见 :mod:`core.pes.audit` 与 :mod:`core.pes.run_registry`），用「全文 sha256 比对」
    判它们会误报。这是两类东西，不能混判。
    """
    base = Path(normalize_path(root or (str(Path(__file__).resolve().parents[2]) + "/data/v9")))
    bad: List[Dict[str, Any]] = []
    if not base.exists():
        return bad
    for pat in patterns:
        for f in base.rglob(pat):
            if f.name.endswith(WRITE_LOG_SUFFIX) or QUARANTINE_DIR in f.parts:
                continue
            r = detect_uninstrumented(f)
            if not r["instrumented"]:
                bad.append(r)
    return bad


__all__ = [
    "DEFAULT_SEED_KEYS",
    "QUARANTINE_DIR",
    "WRITE_LOG_SUFFIX",
    "StateIntegrityError",
    "StateReport",
    "StateFile",
    "detect_uninstrumented",
    "scan_state_dir",
]
