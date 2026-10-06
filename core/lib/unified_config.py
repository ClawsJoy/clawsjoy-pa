#!/usr/bin/env python3
"""Unified Config - Unified Config 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


_MISS = object()   # 「无此键」之哨（判「同值」· pm_1520 §二.2⒞）


def _sha16(s: str) -> str:
    """文本之 `sha256` 前 16 hex（存底名之印 —— 承 `core/lib/paths.py` 之派生名预算 `.before_<16hex>`）。"""
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


class UnifiedConfig:
    """统一配置管理器 - 单例模式"""

    _instance = None
    _config: Dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _find_file(self, candidates: list) -> Optional[Path]:
        """在多个候选路径中查找文件"""
        for candidate in candidates:
            path = Path(candidate)
            if path.exists():
                return path
        return None

    def _load_yaml(self, path: Path, key: str = None):
        """加载 YAML 文件"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if key:
                    self._config[key] = data
                else:
                    self._config.update(data)
            print(f"[CONFIG] 加载: {path}")
            return True
        except Exception as e:
            print(f"[CONFIG] 加载失败 {path}: {e}")
            return False

    def _load(self):
        """加载所有配置 - 支持多路径查找"""
        print("[CONFIG] 初始化统一配置管理器")

        # 主配置文件（**装根** · 依 CWD 之相对候选）
        main_paths = [
            "config/system/system_unified.yaml",
            "config/system.yaml",
            "config/config.yaml",
        ]
        main_path = self._find_file(main_paths)
        # ⭐ pm_1520 §二.1（甲 · 件二）：记**实载**之主件 ⇒ `set_and_save()` 之写处**唯此一处**（⛔ 二处各判）
        self._main_path = main_path
        if main_path:
            self._load_yaml(main_path)
        # ⭐ pm_1520 §二.1：**用户级层**（`%APPDATA%\ClawsJoy\system_unified.yaml`）——
        #   序在装根之次 ⇒ **覆盖**装根层（净机之装根 ⛔ 可写 ⇒ 写端落此处 · 承 §二.2）。
        #   ⚠ **深并**（⛔ 整块替 —— 免丢 `paths` 之他键）。
        _u = self._user_config_path()
        if _u is not None and _u.exists():
            try:
                with open(_u, "r", encoding="utf-8") as f:
                    _ud = yaml.safe_load(f) or {}
                if isinstance(_ud, dict):
                    self._deep_merge(self._config, _ud)
                print(f"[CONFIG] 加载（用户级 · 覆盖）: {_u}")
            except Exception as e:
                print(f"[CONFIG] 加载失败 {_u}: {e}")

        # 路由配置
        routes_paths = ["config/routes/routes.yaml", "config/routes.yaml"]
        routes_path = self._find_file(routes_paths)
        if routes_path:
            self._load_yaml(routes_path, "routes")

        # Agent Soul 配置
        soul_paths = ["config/agents_soul/agents_soul.yaml", "config/agents_soul.yaml"]
        soul_path = self._find_file(soul_paths)
        if soul_path:
            self._load_yaml(soul_path, "agents_soul")

        # 关键词配置 (统一关键词配置)
        keywords_paths = [
            "config/keywords.yaml",
        ]
        keywords_path = self._find_file(keywords_paths)
        if keywords_path:
            self._load_yaml(keywords_path, "keywords")

    # ===== ⭐ 甲 · 件二（pm_1520 §二.1）：`paths.vault_root` 之**定点写** —— 一处定形 =====
    _USER_REL = ("ClawsJoy", "system_unified.yaml")   # `%APPDATA%` 之下

    def _user_config_path(self) -> Optional[Path]:
        r"""用户级配置之径（`%APPDATA%\ClawsJoy\system_unified.yaml`）—— `APPDATA` 缺 ⇒ `None`。"""
        base = (os.environ.get("APPDATA") or "").strip()
        return Path(base).joinpath(*self._USER_REL) if base else None

    def _deep_merge(self, dst: dict, src: dict) -> None:
        """递归并（用户级层**覆盖**装根层；同 `dict` ⇒ 下潜 · ⛔ 整块替）。"""
        for k, v in (src or {}).items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                self._deep_merge(dst[k], v)
            else:
                dst[k] = v

    def _deep_set(self, path: str, value) -> None:
        """内存中之点径写（与写盘**同刻** ⇒ 免重起即见 · 承 pm_1517 §二.4）。"""
        keys = path.split(".")
        cur = self._config
        for k in keys[:-1]:
            nxt = cur.get(k)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[k] = nxt
            cur = nxt
        cur[keys[-1]] = value

    @staticmethod
    def _yaml_scalar(value) -> str:
        """值 ⇒ YAML 标量字面（一处定形 · ⛔ 手拼引号）。"""
        try:
            sv = yaml.safe_dump(value, allow_unicode=True, default_flow_style=True).strip()
        except Exception:
            sv = str(value)
        if sv.endswith("..."):
            sv = sv[:-3].strip()
        return (sv.splitlines() or [u"''"])[0]

    @staticmethod
    def _inline_comment(body: str) -> str:
        """行内注释（首个「空白 ＋ `#`」起 · **含其前之空白** —— 保其原形）；无 ⇒ `''`。"""
        for i in range(1, len(body)):
            if body[i] == "#" and body[i - 1] in " \t":
                j = i
                while j > 0 and body[j - 1] in " \t":
                    j -= 1
                return body[j:]
        return ""

    @staticmethod
    def _get_nested(d, path: str):
        """点径读取（无 ⇒ `_MISS`）—— 判「同值重写」用（承 pm_1520 §二.2⒞）。"""
        cur = d
        for k in path.split("."):
            if not isinstance(cur, dict) or k not in cur:
                return _MISS
            cur = cur[k]
        return cur

    def _splice(self, raw: str, path: str, value):
        """（新文, 何形）：`path` 之值 ⇒ **定点换** ∨ 附于父块之后（**保他行 ／ 保注释** · 一处定形）。"""
        import re as _re
        keys = path.split(".")
        if len(keys) < 2:
            raise ValueError("set_and_save 须给「父块.键」之点径（如 paths.vault_root）")
        pname = keys[-2]
        leaf = keys[-1]
        val = self._yaml_scalar(value)
        nl = "\r\n" if "\r\n" in raw else "\n"
        lines = raw.splitlines(keepends=True)

        def _ind(b):
            return len(b) - len(b.lstrip(" "))

        # (1) 父块（顶层块式 · `paths:` 之后唯空 ／ 注释）
        p_start = None
        for i, ln in enumerate(lines):
            b = ln.rstrip("\r\n")
            if not b.strip() or b.lstrip().startswith("#"):
                continue
            if _ind(b) == 0:
                if _re.match("^" + _re.escape(pname) + r":\s*(#.*)?$", b):
                    p_start = i
                    break
                if _re.match("^" + _re.escape(pname) + r":\s*\S", b):
                    raise ValueError("父块 `%s:` 非块式 YAML（inline）⇒ 拒写（⛔ 静默）" % pname)
        if p_start is None:                       # 父块皆无 ⇒ 文末立之
            if lines and not lines[-1].endswith("\n"):
                lines[-1] = lines[-1] + nl
            lines.append("%s:%s" % (pname, nl))
            lines.append("  %s: %s%s" % (leaf, val, nl))
            return "".join(lines), "append-block"
        # (2) 块界
        p_end = len(lines)
        for j in range(p_start + 1, len(lines)):
            b = lines[j].rstrip("\r\n")
            if not b.strip() or b.lstrip().startswith("#"):
                continue
            if _ind(b) <= 0:
                p_end = j
                break
        # (3) 键在 ⇒ 定点换（保缩进 ＋ 保行内注释）
        for j in range(p_start + 1, p_end):
            b = lines[j].rstrip("\r\n")
            m = _re.match("^(?P<ind>[ ]*)" + _re.escape(leaf) + r":(?P<rest>.*)$", b)
            if m:
                ln_nl = "\r\n" if lines[j].endswith("\r\n") else "\n"
                lines[j] = "%s%s: %s%s%s" % (m.group("ind"), leaf, val,
                                             self._inline_comment(m.group("rest")), ln_nl)
                return "".join(lines), "replace-line"
        # (4) 键 ⛔ 在 ⇒ 附于父块之后
        lines.insert(p_end, "  %s: %s%s" % (leaf, val, nl))
        return "".join(lines), "append-key"

    def _write_target(self):
        """（原文, 径）：装根主件（在 ∧ 可写）⇒ 否 ⇒ 用户级（一处定形 · pm_1520 §二.1）。"""
        p = getattr(self, "_main_path", None)
        if p is not None and Path(p).exists() and os.access(str(p), os.W_OK):
            return Path(p).read_text(encoding="utf-8"), Path(p)
        u = self._user_config_path()
        if u is None:
            raise RuntimeError("装根配置 ⛔ 可写 ∧ 无 %APPDATA% ⇒ **无可写之处**（照实拒 · ⛔ 静默）")
        return (u.read_text(encoding="utf-8") if u.exists() else ""), u

    def set_and_save(self, path: str, value):
        """⭐ **定点写配置**（甲 · 件二 · pm_1520 §二.1）—— **保注释 ／ 保他行**（一处定形）。

        ⛔ 整件重写（失注 ＝ 失知识 · 承「经验落盘」）；写前**存底**（`.before_<16hex>`）；
        坏体 ⇒ **拒写**（⛔ 静默 · ⛔ 覆）。回 `{"ok","changed","file","key","backup","form"}`。
        """
        raw, target = self._write_target()
        if raw.strip():
            try:
                yaml.safe_load(raw)                # 坏体 ⇒ 早拒（⛔ 覆 · 存底亦 ⛔ 动）
            except Exception as e:
                raise ValueError("配置体不可解析 ⇒ 拒写（⛔ 覆）: %s" % e)
        _cur = self._get_nested((yaml.safe_load(raw) if raw.strip() else {}), path)
        if _cur is not _MISS and _cur == value:          # 同值 ⇒ ⛔ 动盘（pm_1520 §二.2⒞）
            return {"ok": True, "changed": False, "file": str(target), "key": path,
                    "backup": None, "form": "noop-same-value"}
        new, form = self._splice(raw, path, value)
        if new == raw:
            return {"ok": True, "changed": False, "file": str(target), "key": path,
                    "backup": None, "form": form}
        target.parent.mkdir(parents=True, exist_ok=True)
        bak = target.with_name(target.name + ".before_" + _sha16(raw))
        if not bak.exists():
            bak.write_text(raw, encoding="utf-8")
        tmp = target.with_name(target.name + ".tmp%d" % os.getpid())
        tmp.write_text(new, encoding="utf-8")
        # ⭐ 原子替换须抗 Windows 之**过性占用**（杀软 ／ 索引器 ／ 他句柄暂握 ⇒ WinError 5 ／ 32 ／ 33）
        #   ⇒ **有界重试**（⛔ 无限）；尽而仍败 ⇒ ⛔ **原样抛**（承「⛔ 静默」）—— 他错（如径 ⛔ 可写）即抛。
        _last_err = None
        for _ in range(8):
            try:
                os.replace(str(tmp), str(target))
                _last_err = None
                break
            except OSError as _e:
                if not (isinstance(_e, PermissionError) or getattr(_e, "winerror", None) in (5, 32, 33)):
                    raise
                _last_err = _e
                time.sleep(0.05)
        if _last_err is not None:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise _last_err
        self._deep_set(path, value)
        return {"ok": True, "changed": True, "file": str(target), "key": path,
                "backup": str(bak), "form": form}

    def get(self, path: str, default=None):
        """获取配置值，支持点号路径如 'llm.model'"""
        keys = path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default

    def get_port(self, service: str = "gateway") -> int:
        """获取服务端口"""
        ports = self.get("services", {})
        if isinstance(ports, dict):
            return ports.get(service, {}).get("port", 5002)
        return 5002

    @property
    def ROOT(self) -> str:
        """项目根目录"""
        return str(Path(__file__).parent.parent.parent.absolute())

    @property
    def HOST(self) -> str:
        """服务主机"""
        return self.get("services.host", "localhost")


# 全局单例
unified_config = UnifiedConfig()
