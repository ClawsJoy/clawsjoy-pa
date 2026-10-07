# -*- coding: utf-8 -*-
u"""pm_1811 §一.2⒝ 之齿：**仓洁之阈**（`core/lib/workspace_hygiene.py`）。

以何形调用：
  python -X utf8 -B -m pytest tests/unit/test_workspace_hygiene_1811.py -q

由（一手 · 承 pm_1767 ／ pm_1779 ／ pm_1810）：Paseo 之 `workspace-git-service` 每轮数
「未入仓 ＋ 被忽略」之件（同 `GIT_COUNT_ARGV`）⇒ 其**单次耗时随件数而增**
（`186,980` 件 ⇒ 超 `30 s` ⇒ daemon 瘫 ／ `1,240` 件 ⇒ `0.45 s`）。
⇒ 故须**一条可查之阈**：逾 ⇒ 告警入日志 ＋ 报 PM。

判据（正控 5 ＋ 反控 6）：
  ⒈ **正控**：阈**一处定形** ＝ `THRESHOLD_UNTRACKED_IGNORED == 5000` ∧ `check` 之缺省即取之
     （⛔ 逐处硬编）。
  ⒉ **正控**：真跑于本仓 ⇒ `count()` ⇒ 整数 ≥ 0 ∧ `rc == 0` ∧ 有耗（⛔ 空果）。
  ⒊ **正控**：阈大于件数 ⇒ `verdict == "ok"` ∧ `exceeded is False`。
  ⒋ **正控**：`_main` 未逾 ⇒ 退码 **0**。
  ⒌ **正控**：日志径 ＝ `<根>/logs/workspace_hygiene.log`。
  ⒍ **反控**：`GIT_COUNT_ARGV` 之**真身**于**非仓**之目录 ⇒ `count is None` ∧
     `rc != 0` ∧ `why` 显因 ⇒ `verdict == "unknown"` ∧ `_main` 退码 **4**
     （⭐ ⛔ 以 `ok` 充 `unknown` —— 承「**空 ⛔ 混 缺**」）。
  ⒎ **反控**：逾阈 ⇒ `verdict == "over"` ∧ `exceeded is True` ∧ `_main` 退码 **2**。
  ⒏ **反控**：逾阈 ⇒ **告警入日志**（一行 · 含 件 ／ 阈 ／ 根 ／ 刻）。
  ⒐ **反控**：未逾 ⇒ **⛔ 落日志**（⛔ 以「无警」充「有警」）。
  ⒑ **反控**：`unknown` ⇒ **⛔ 落日志**（探败 ⛔ 充「逾」—— 以「告警」充「探败」亦病）。
  ⒒ **反控**：用法错 ⇒ 退码 **3**。
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.lib import workspace_hygiene as wh  # noqa: E402


def _fake(count, rc=0, seconds=0.01, why=u""):
    def _c(root=None, timeout=20.0):
        return {"root": str(root or wh.repo_root()), "count": count, "seconds": seconds,
                "rc": rc, "why": why}
    return _c


# ── 正控 ────────────────────────────────────────────────────────────────

def test_正控一_阈一处定形():
    assert wh.THRESHOLD_UNTRACKED_IGNORED == 5000, wh.THRESHOLD_UNTRACKED_IGNORED
    assert wh.check(threshold=None)["threshold"] == wh.THRESHOLD_UNTRACKED_IGNORED
    assert wh.GIT_COUNT_ARGV == ["git", "ls-files", "-o", "-i", "--directory",
                                 "--exclude-standard"], wh.GIT_COUNT_ARGV


def test_正控二_真跑于本仓_有件有耗非空果():
    d = wh.count(str(ROOT))
    assert d["rc"] == 0, d
    assert isinstance(d["count"], int) and d["count"] >= 0, d
    assert d["seconds"] > 0, d
    assert d["why"] == u"", d


def test_正控三_未逾则判_ok():
    d = wh.check(str(ROOT), threshold=10 ** 9)
    assert d["verdict"] == "ok", d
    assert d["exceeded"] is False, d


def test_正控四_cli_未逾退码零():
    assert wh._main(["--threshold", str(10 ** 9)]) == 0


def test_正控五_日志径在根下_logs():
    assert wh.log_path(str(ROOT)) == os.path.join(str(ROOT), "logs", "workspace_hygiene.log")


# ── 反控 ────────────────────────────────────────────────────────────────

def test_反控六_非仓则未知_退码四_勿以ok充():
    # 用系统临时目录（⭐ 须在**非仓**之处 ⇒ 承 pm_1811 §一.2⒜ 之常例：弃树 ⛔ 落仓内）
    d0 = tempfile.mkdtemp(prefix="hy_norepo_")
    try:
        assert not str(Path(d0).resolve()).startswith(str(ROOT) + os.sep), d0
        d = wh.count(d0)
        assert d["count"] is None, d
        assert d["rc"] not in (0, None), d
        assert d["why"], d
        got = wh.check(d0)
        assert got["verdict"] == "unknown", got
        assert got["exceeded"] is False, got
        assert u"未量得" in got["why_verdict"], got
        assert wh._main(["--root", d0]) == 4, u"未知 ⇒ 退码 4（⛔ 以 0 充「干净」）"
    finally:
        try:
            os.rmdir(d0)
        except OSError:
            pass


def test_反控七_逾阈判_over_退码二(monkeypatch):
    monkeypatch.setattr(wh, "count", _fake(6000))
    d = wh.check(threshold=5000)
    assert d["verdict"] == "over", d
    assert d["exceeded"] is True, d
    assert wh._main(["--threshold", "5000"]) == 2


def test_反控八_逾阈则告警入日志(monkeypatch, tmp_path):
    monkeypatch.setattr(wh, "count", _fake(6000))
    lp = str(tmp_path / "h.log")
    d = wh.warn_if_exceeded(threshold=5000, log=lp)
    assert d["verdict"] == "over", d
    assert d["log"] == lp, d
    line = Path(lp).read_text(encoding="utf-8")
    assert line.endswith("\n"), repr(line)
    assert line.count("\n") == 1, repr(line)
    for tok in ("逾阈", "件=6000", "阈=5000", str(ROOT), "ls-files"):
        assert tok in line, (tok, line)


def test_反控九_未逾则不落日志(monkeypatch, tmp_path):
    monkeypatch.setattr(wh, "count", _fake(10))
    lp = str(tmp_path / "h.log")
    d = wh.warn_if_exceeded(threshold=5000, log=lp)
    assert d["verdict"] == "ok", d
    assert not os.path.exists(lp), u"未逾 ⇒ ⛔ 有警"


def test_反控十_探败则不落日志(monkeypatch, tmp_path):
    monkeypatch.setattr(wh, "count", _fake(None, rc=128, why=u"git rc=128：not a git repository"))
    lp = str(tmp_path / "h.log")
    d = wh.warn_if_exceeded(threshold=5000, log=lp)
    assert d["verdict"] == "unknown", d
    assert not os.path.exists(lp), u"探败 ⇒ ⛔ 以「告警」充之"
    assert u"not a git repository" in d["why_verdict"], d


def test_反控十一_用法错退码三():
    assert wh._main(["--bogus"]) == 3
    assert wh._main(["--threshold", "abc"]) == 3
    assert wh._main(["--threshold"]) == 3
