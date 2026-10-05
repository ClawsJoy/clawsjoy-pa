# -*- coding: utf-8 -*-
"""杂项路由（P1 拆出，Blueprint）—— TTS / 语音转文字 / 数字资产列表。"""

import base64
import json
import os
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request

from core.gateway import _proc as _proc  # ⭐ 子进程唯一出口（窗隐）

bp = Blueprint("misc_routes", __name__)

# ===== ⭐ T2-刀12 §二（2026-10-05 · PM 补令）：产出面之**测试痕**辨 ====
#   级 A · 名形：dir 名以**器名**起（门禁/探针）⇒ 铁定测试痕
#   级 B · 内容：产物之题/内容含「检测到重复操作」（回路闸）∨「E2E」（端到端探针）
PLAN_TRACE_NAME_PREFIXES = ("canary_", "pm011_", "session_stream_test", "p9_", "pa_selftest", "probe_", "e2e_", "test_")
PLAN_TRACE_TEXT_MARKS = ("检测到重复操作", "E2E")


def _plan_trace_filter_meta(view):
    """⭐ T2-刀12 §二：滤之「形」之自陈（面／判据逐条 ⇒ 可复算）。"""
    return {
        "面之径逐字": "data/plans",
        "view": view,
        "名形判据": list(PLAN_TRACE_NAME_PREFIXES),
        "内容判据": list(PLAN_TRACE_TEXT_MARKS),
        "注": "名形 ⇒ 器名即门禁/探针（铁定）；内容 ⇒ 回路闸/E2E 之痕（逐条可核）",
    }


@bp.route("/v5/tts", methods=["POST"])
def tts_endpoint():
    from core.lib.voice_service import voice_service

    data = request.json
    text = data.get("text", "")
    audio_file = voice_service.text_to_speech(text)
    if audio_file:
        with open(audio_file, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode()
        return jsonify({"audio": audio_base64})
    return jsonify({"error": "TTS failed"}), 500


@bp.route("/speech/to_text", methods=["POST"])
def speech_to_text():
    from core.lib.voice_service import voice_service

    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No audio file"}), 400

    # 保存上传的音频
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # 调用voice_service识别
        text = voice_service.speech_to_text(tmp_path)

        # 清理临时文件
        os.unlink(tmp_path)

        if text:
            return jsonify({"text": text})
        else:
            return jsonify({"text": "", "error": "No speech detected"}), 200

    except Exception as e:
        # 确保清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return jsonify({"error": str(e)}), 500


@bp.route("/v9/plans/list", methods=["GET"])
def v9_plans_list():
    """#145 数字资产自动文件化：列出已归档的计划/报告/决策，按时间倒序

    Query 参数:
        session_id: 可选，按会话过滤
        kind: 可选，'plan' | 'report' | 'decision' 过滤类型
        view: 可选，'all'（缺省 · 既有之形 ⇔ 锤不破）| 'real'（真产出）| 'test'（测试痕）
    """
    _sid = request.args.get("session_id", "")
    _kind = request.args.get("kind", "")
    # ⭐ T2-刀12 §二：`view` —— 缺省 `all`（既有之形 ⇔ 零回归）；假值 ⇒ **400 点名**（假值之负控 · ⇔ 静默兜底）
    _view = (request.args.get("view") or "all").strip().lower()
    if _view not in ("all", "real", "test"):
        return jsonify({"success": False,
                        "error": "view 须 ∈ all|real|test（收 %r）—— 假值之负控" % _view,
                        "missing": ["view"], "kind": "bad_param", "route": "/v9/plans/list"}), 400
    _plans_dir = Path("data/plans")
    if not _plans_dir.exists():
        return jsonify({"success": True, "assets": [], "real": [], "test_trace": [],
                        "counts": {"面之径逐字": "data/plans", "dirs_total": 0, "files_total": 0,
                                   "before": 0, "real": 0, "test_trace": 0, "shown": 0,
                                   "truncated": False},
                        "filter": _plan_trace_filter_meta(_view)})
    _dirs = [_plans_dir / _sid] if _sid else sorted(_plans_dir.iterdir())
    assets = []
    for _d in _dirs:
        if not _d.is_dir():
            continue
        for _f in sorted(_d.glob("*"), reverse=True):
            try:
                _meta = {"session_id": _d.name, "file": _f.name, "path": str(_f)}
                if _f.suffix == ".json":
                    _data = json.loads(_f.read_text(encoding="utf-8"))
                    _meta["kind"] = _data.get("kind", "")
                    _meta["title"] = _data.get("title", "")
                    _meta["ts"] = _data.get("ts", "")
                    _meta["status"] = _data.get("status", "")
                    _meta["content"] = _data.get("content", "")[:500]
                else:
                    _meta["kind"] = _f.stem.split("_")[0]
                    _meta["title"] = _f.stem
                    _meta["ts"] = _f.stat().st_mtime
                    _meta["content"] = ""
                # ⭐ T2-刀12 §二：本件之「痕」之判（名形 ⇒ 头 400 B 之内容痕）
                #   ⚠ 修正①：非 `.json` 之 `title` 为文件名词干、`content` 恒空
                #             ⇒ 旧判恒不命中（假接线）；今直读文件头
                #   ⚠ 修正②：判**先于** `kind` 滤（滤移至后）⇒ 免「痕件被滤
                #             ⇒ 该 dir 漏判」（假绿之同族）
                _why = ""
                if str(_d.name).lower().startswith(PLAN_TRACE_NAME_PREFIXES):
                    _why = "名形"
                else:
                    _head = ""
                    try:
                        with _f.open("rb") as _fh:
                            _head = _fh.read(400).decode("utf-8", "replace")
                    except Exception:
                        _head = ""
                    _blob = "%s %s %s" % (_meta.get("title") or "", _meta.get("content") or "", _head)
                    for _mk in PLAN_TRACE_TEXT_MARKS:
                        if _mk in _blob:
                            _why = "内容:" + _mk
                            break
                _meta["_mark"] = _why   # 私键 · 待后端归总后 pop（⇔ 外带）
                assets.append(_meta)
            except Exception:
                continue
    _dirs_n = sum(1 for _d in _dirs if _d.is_dir())
    # ⭐ T2-刀12 §二：`kind` 滤（移至此 ⇒ 判据 ⇔ 被滤）
    _kept = [a for a in assets if (not _kind) or a.get("kind") == _kind]
    _name_trace = set()
    for _a in _kept:
        if str(_a.get("session_id") or "").lower().startswith(PLAN_TRACE_NAME_PREFIXES):
            _name_trace.add(_a.get("session_id") or "")
    for _a in _kept:
        _mark = _a.pop("_mark", "")
        _why = ("名形" if (_a.get("session_id") or "") in _name_trace else _mark) or ""
        _a["trace"] = bool(_why)
        _a["trace_why"] = _why
    _real = [a for a in _kept if not a.get("trace")]
    _trace = [a for a in _kept if a.get("trace")]
    _sel = {"all": _kept, "real": _real, "test": _trace}[_view]
    _shown = _sel[:100]
    return jsonify({
        "success": True,
        "assets": _shown,
        "real": _real[:100],
        "test_trace": _trace[:100],
        "counts": {"面之径逐字": "data/plans", "dirs_total": _dirs_n,
                   "files_total": len(_kept), "before": len(_kept),
                   "real": len(_real), "test_trace": len(_trace),
                   "shown": len(_shown), "truncated": len(_sel) > 100},
        "filter": _plan_trace_filter_meta(_view),
    })


@bp.route("/api/endpoints", methods=["GET"])
def list_endpoints():
    from flask import current_app

    endpoints = [
        {"path": rule.rule, "methods": list(rule.methods)}
        for rule in current_app.url_map.iter_rules()
        if not rule.rule.startswith("/static")
    ]
    return jsonify({"endpoints": endpoints, "total": len(endpoints)})


@bp.route("/api/v5/project/list", methods=["GET"])
def project_list():
    from core.lib.code_repo import get_code_repo

    return jsonify(
        {"success": True, "projects": get_code_repo(request.args.get("user_id", "codex_user")).list_projects()}
    )


from datetime import datetime


@bp.route("/api/v5/feedback", methods=["POST"])
def submit_feedback():
    data = request.json
    rating = data.get("rating", 0)
    question = data.get("question", "")
    answer = data.get("answer", "")
    user_id = data.get("user_id", "anon")
    intent = data.get("intent", "")
    skill = data.get("skill", "")

    # ========== 1. 原有逻辑：存入 feedback.json ==========
    feedback_file = Path("data/feedback.json")
    existing = json.loads(feedback_file.read_text(encoding="utf-8")) if feedback_file.exists() else {"success": [], "failure": []}
    category = "success" if rating >= 4 else "failure"
    existing[category].append(
        {
            "user_id": user_id,
            "question": question,
            "answer": answer[:200],
            "rating": rating,
            "timestamp": datetime.now().isoformat(),
        }
    )
    feedback_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

    # ========== 2. 新增：存入统一训练数据集 ==========
    train_file = Path("data/training/training_data.json")
    if train_file.exists():
        with open(train_file, "r", encoding="utf-8") as f:
            train_data = json.load(f)
    else:
        train_data = []

    # 只存储高质量数据 (rating >= 4)
    if rating >= 4 and question and answer:
        train_data.append(
            {
                "input": question,
                "output": answer,
                "rating": rating,
                "intent": intent,
                "skill": skill,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
            }
        )
        with open(train_file, "w", encoding="utf-8") as f:
            json.dump(train_data, f, indent=2, ensure_ascii=False)
        print(f"[Feedback] 新增训练数据: {question[:30]}... (总数: {len(train_data)})")

    # ========== 3. 新增：触发自学习 ==========
    if rating >= 4:
        try:
            from engine.evolution.self_learning import self_learning

            self_learning.learn_from_interaction(
                user_id=user_id, query=question, intent=intent, skill_used=skill, success=True, confidence=rating / 5.0
            )
        except Exception as e:
            print(f"[Feedback] 自学习失败: {e}")

    # ========== 4. 新增：检查是否需要触发训练 ==========
    if rating >= 4:
        try:
            from scripts.auto_train_trigger import check_and_trigger

            check_and_trigger()
        except ImportError:
            if len(train_data) >= 10:
                print(f"[Feedback] 训练数据达 {len(train_data)} 条，触发训练")
                import subprocess

                _proc.popen_hidden(["python", "scripts/train_model.py", "--quick"], cwd=Path(__file__).parent)
        except Exception as e:
            print(f"[Feedback] 训练触发失败: {e}")

    return {"success": True}
