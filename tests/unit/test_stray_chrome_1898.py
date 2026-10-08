# -*- coding: utf-8 -*-
"""1898 ③ · 「跑毕必收」之齿 —— `scripts/dev/查散落浏览器.py` 之纯逻辑。

正控：无头 ∧ 根 ∧ 非 guard ⇒ 计（归属按 profile 名）。
反控：① 子进程（父亦 chrome）⇒ ⛔ 计　② 非无头 ⇒ ⛔ 计　③ guard 之 `chrome_cdp`
常驻 ⇒ ⛔ 计　④ 器 **只读** —— 源码 ⛔ 含任何杀/停进程之调用。

⚠ 本件 ⛔ 起真浏览器 · ⛔ 杀任何进程（唯读源码 ＋ 纯逻辑）。
"""
import importlib.util
import io
import os
import re

import pytest

_MOD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "scripts", "dev", "查散落浏览器.py",
)


def _load():
    spec = importlib.util.spec_from_file_location("stray_chrome_1898", _MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def M():
    assert os.path.exists(_MOD), "器不在盘: %s" % _MOD
    return _load()


def test_器在盘且只读(M):
    src = io.open(_MOD, encoding="utf-8").read()
    for bad in ("Stop-Process", "taskkill", "TerminateProcess", "os.kill", "p.Kill"):
        assert bad not in src, "器须只读，⛔ 含 %s" % bad


def test_正控_无头根实例应计(M):
    T = M.BS + "Temp" + M.BS
    procs = [{
        "ProcessId": 10, "ParentProcessId": 9, "Name": "chrome.exe",
        "CommandLine": "chrome.exe --headless=new --remote-debugging-port=9223 --user-data-dir=" + T + "cw1807cdp_x",
    }]
    assert M.find_strays(procs) == [(10, "CodexWindows线", 9223, T + "cw1807cdp_x")]


def test_反控_子进程不计(M):
    T = M.BS + "Temp" + M.BS
    procs = [
        {"ProcessId": 10, "ParentProcessId": 9, "Name": "chrome.exe",
         "CommandLine": "chrome.exe --headless=new --user-data-dir=" + T + "cw1_x"},
        {"ProcessId": 11, "ParentProcessId": 10, "Name": "chrome.exe",
         "CommandLine": "chrome.exe --headless=new --user-data-dir=" + T + "cw1_x"},
    ]
    assert [p[0] for p in M.find_strays(procs)] == [10], "子进程须随根走，⛔ 各计"


def test_反控_非无头不计(M):
    T = M.BS + "Temp" + M.BS
    procs = [{"ProcessId": 10, "ParentProcessId": 9, "Name": "chrome.exe",
              "CommandLine": "chrome.exe --user-data-dir=" + T + "cw1_x"}]
    assert M.find_strays(procs) == []


def test_反控_guard常驻不计(M):
    C = M.BS + "Users" + M.BS + "x" + M.BS + ".clawsjoy" + M.BS
    procs = [{"ProcessId": 10, "ParentProcessId": 9, "Name": "chrome.exe",
              "CommandLine": "chrome.exe --headless=new --user-data-dir=" + C + "chrome_cdp"}]
    assert M.find_strays(procs) == [], "guard 之常驻 ⛔ 当散落"


def test_归属按全径归一(M):
    P = M.BS + "paseo-workspace" + M.BS
    assert M.attribute(P + "_tmp" + M.BS + "ts_scratch" + M.BS + "p1468" + M.BS + "cdp_profile") == "技术总监"
    assert M.attribute(P + ".paseo-pm" + M.BS + "x") == "项目经理"
    assert M.attribute(M.BS + "Temp" + M.BS + "zzz").startswith("?")
    assert M.attribute("").startswith("?")


def test_自证八例(M):
    assert M._self_test() == 0