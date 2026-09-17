"""归档模块 — 从 agent_gateway_enhanced.py 抽取"""

import logging
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

def _archive_asset(kind, session_id, title, content, messages=None):
    """#145 数字资产自动文件化：将计划/报告/决策写入 data/plans/{session_id}/，并入库 SAG

    Args:
        kind: 'plan' | 'report' | 'decision'
        session_id: 会话 ID
        title: 资产标题
        content: 资产正文
        messages: 可选，用于生成会话摘要
    Returns:
        str: 写入的文件路径；失败返回 ""
    """
    try:
        _ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        _dir = Path(f"data/plans/{session_id}")
        _dir.mkdir(parents=True, exist_ok=True)
        _now_iso = datetime.now().isoformat()
        _body = (content or "")[:8000]
        # 从正文提取步骤列表（供 OS 读取执行）
        import re as _re_ar
        _steps = []
        for _sl in _body.splitlines():
            _sl_stripped = _sl.strip()
            if not _sl_stripped:
                continue
            if _re_ar.match(r'^(\d+[.、）)]|[-*•])\s*\S', _sl_stripped) or _re_ar.match(r'^步骤\s*\d*[一二三四五六七八九十]?\s*[：:]', _sl_stripped):
                _steps.append(_re_ar.sub(r'^(\d+[.、）)]|[-*•])\s*', '', _sl_stripped))
        if not _steps:
            _steps = [_body[:500]] if _body else []
        _meta = {
            "kind": kind,
            "session_id": session_id,
            "title": (title or "")[:200],
            "ts": _now_iso,
            "source": "auto_archive",
            "content": _body,
            "messages_count": len(messages) if messages else 0,
        }
        if kind in ("plan", "decision"):
            _fname = f"{kind}_{_ts}.json"
            _fpath = _dir / _fname
            _payload = dict(_meta)
            if kind == "plan":
                _payload["steps"] = _steps
                _payload["status"] = "pending"
                _payload["executable"] = True
            else:
                _payload["decision"] = _body[:2000]
            _fpath.write_text(json.dumps(_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            _fname = f"{kind}_{_ts}.md"
            _fpath = _dir / _fname
            _md = f"# {kind.capitalize()}: {(title or '')[:120]}\n\n"
            _md += f"- 归档时间: {_now_iso}\n"
            _md += f"- 会话: {session_id}\n"
            _md += f"- 类型: {kind}\n\n"
            _md += "## 内容\n\n" + _body + "\n"
            if messages:
                _summary_lines = []
                for _m in messages[-20:]:
                    _role = _m.get("role", "")
                    _c = str(_m.get("content", "") or "")[:200].replace("\n", " ")
                    if _c:
                        _summary_lines.append(f"- [{_role}] {_c}")
                if _summary_lines:
                    _md += "\n## 会话摘要\n\n" + "\n".join(_summary_lines) + "\n"
            _fpath.write_text(_md, encoding="utf-8")
        logger.info(f"[AUTO_ARCHIVE] 已写入 {_fpath}")
        # 同时调 store_step_summary 入库 SAG
        try:
            from core.lib.code_entity_extractor import extractor as _ar_extractor
            _ar_extractor.store_step_summary(
                task_name=f"{kind}_{session_id}_{_ts}",
                step_number=1,
                summary_json={
                    "kind": kind,
                    "title": (title or "")[:200],
                    "content": (content or "")[:2000],
                    "file": str(_fpath),
                    "source": "auto_archive",
                    "ts": _now_iso,
                },
            )
            logger.info(f"[AUTO_ARCHIVE] 已入库 SAG: {kind}_{session_id}_{_ts}")
        except Exception as _ar_e:
            logger.info(f"[AUTO_ARCHIVE] SAG 入库失败: {_ar_e}")
        return str(_fpath)
    except Exception as _e_ar:
        logger.info(f"[AUTO_ARCHIVE] 文件化失败: {_e_ar}")
        return ""




def _archive_user_message(role, content, session_id, agent_name, user_id="default"):
    """#166 用户消息自动入库 SAG + JSONL：将对话消息追加到 data/v8/user_messages/{session_id}.jsonl，并入库 SAG

    Args:
        role: 消息角色（user / assistant）
        content: 消息内容
        session_id: 会话 ID
        agent_name: Agent 名称
    Returns:
        str: 追加的 JSONL 行；失败返回 ""
    """
    try:
        _now_iso = datetime.now().isoformat()
        _dir = Path("data/v8/user_messages")
        _dir.mkdir(parents=True, exist_ok=True)
        _fpath = _dir / f"{session_id}.jsonl"
        _entry = {
            "role": role,
            "content": (content or "")[:8000],
            "session_id": session_id,
            "agent_name": agent_name or "",
            "ts": _now_iso,
        }
        _line = json.dumps(_entry, ensure_ascii=False)
        with open(_fpath, "a", encoding="utf-8") as _f:
            _f.write(_line + "\n")
        # 沙箱镜像：写完全局后，同步写入沙箱 {sid}.jsonl
        try:
            _uid = str(user_id or "default")
            _sandbox_dir = Path("data/projects") / _uid / session_id / "clawsjoy_dev" / "data" / "v8" / "user_messages"
            _sandbox_dir.mkdir(parents=True, exist_ok=True)
            _sfpath = _sandbox_dir / f"{session_id}.jsonl"
            with open(_sfpath, "a", encoding="utf-8") as _sf:
                _sf.write(_line + "\n")
            logger.info(f"[USER_MSG_ARCHIVE] 已镜像写入沙箱 {_sfpath}")
        except Exception as _e_sb:
            logger.info(f"[USER_MSG_ARCHIVE] 沙箱镜像写入失败: {_e_sb}")
        # 入库 SAG
        try:
            from core.lib.code_entity_extractor import extractor as _um_extractor
            _um_extractor.store_step_summary(
                task_name=f"user_message_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                step_number=1,
                summary_json={
                    "role": role,
                    "content": (content or "")[:2000],
                    "session_id": session_id,
                    "agent_name": agent_name or "",
                    "file": str(_fpath),
                    "source": "user_message_archive",
                    "ts": _now_iso,
                },
            )
        except Exception as _um_e:
            logger.info(f"[USER_MSG_ARCHIVE] SAG 入库失败: {_um_e}")
        logger.info(f"[USER_MSG_ARCHIVE] 已写入 {_fpath}")
        return _line
    except Exception as _e_um:
        logger.info(f"[USER_MSG_ARCHIVE] 失败: {_e_um}")
        return ""


# H9 历史回填：live 正本与沙箱镜像行数差异超过阈值时，自动补齐缺失部分（只补不删，幂等）
_BACKFILL_THRESHOLD = 100  # 行数差异阈值


def backfill_user_message_mirror(user_id="default", session_id="", threshold=_BACKFILL_THRESHOLD):
    """启动时对比 live 正本与沙箱镜像的 user_messages 行数，缺失超过阈值则补齐。

    - 只补不删：镜像永远不删除正本已有的内容
    - 幂等：重复调用不产生重复行（只追加镜像比正本少的尾部行）
    - 返回补写的行数；无差异或不可用返回 0
    """
    if not session_id:
        return 0
    try:
        _dir = Path("data/v8/user_messages")
        _fpath = _dir / f"{session_id}.jsonl"
        _uid = str(user_id or "default")
        _sandbox_dir = Path("data/projects") / _uid / session_id / "clawsjoy_dev" / "data" / "v8" / "user_messages"
        _sfpath = _sandbox_dir / f"{session_id}.jsonl"
        if not _fpath.exists():
            return 0  # 正本不存在，无从回填
        _mirror_dir = Path("data/projects") / _uid / session_id / "clawsjoy_dev" / "data" / "v8" / "user_messages"
        _mirror_dir.mkdir(parents=True, exist_ok=True)
        # 行数对比（按行数差补齐；假设两边都是追加式，缺失在尾部）
        _live_count = 0
        with open(_fpath, "r", encoding="utf-8") as _lf:
            _live_count = sum(1 for _ in _lf)
        _mirror_count = 0
        if _sfpath.exists():
            with open(_sfpath, "r", encoding="utf-8") as _mf:
                _mirror_count = sum(1 for _ in _mf)
        _diff = _live_count - _mirror_count
        if _diff <= threshold:
            return 0
        # 补齐：从正本读取镜像缺失的尾部行（跳过已镜像的前 _mirror_count 行）
        _missing_lines = []
        with open(_fpath, "r", encoding="utf-8") as _lf:
            for _i, _line in enumerate(_lf):
                if _i >= _mirror_count:
                    _missing_lines.append(_line)
        with open(_sfpath, "a", encoding="utf-8") as _mf:
            _mf.writelines(_missing_lines)
        logger.info(f"[USER_MSG_BACKFILL] 补齐 {len(_missing_lines)} 行到沙箱镜像 {_sfpath}（live={_live_count} mirror={_mirror_count}）")
        return len(_missing_lines)
    except Exception as _bf_e:
        logger.info(f"[USER_MSG_BACKFILL] 回填失败: {_bf_e}")
        return 0


_EXECUTION_POLICY_CACHE = None

