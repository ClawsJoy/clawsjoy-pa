"""链路追踪 - 全链路追踪"""

import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, List, Optional

trace_id_var: ContextVar = ContextVar("trace_id", default="")
span_id_var: ContextVar = ContextVar("span_id", default="")


class Span:
    """追踪跨度"""

    def __init__(self, name: str, trace_id: str, parent_id: str = None):
        self.name = name
        self.trace_id = trace_id
        self.span_id = str(uuid.uuid4())
        self.parent_id = parent_id
        self.start_time = datetime.now()
        self.end_time = None
        self.tags = {}
        self.logs = []

    def finish(self):
        self.end_time = datetime.now()

    def set_tag(self, key: str, value: str):
        self.tags[key] = value

    def log(self, message: str):
        self.logs.append({"message": message, "timestamp": datetime.now().isoformat()})

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0


class Tracer:
    """链路追踪器"""

    def __init__(self):
        self.spans = []
        self._current_span = None

    def start_span(self, name: str, parent_id: str = None) -> Span:
        """开始一个 Span"""
        trace_id = trace_id_var.get()
        if not trace_id:
            trace_id = str(uuid.uuid4())
            trace_id_var.set(trace_id)

        span = Span(name, trace_id, parent_id)
        self.spans.append(span)
        span_id_var.set(span.span_id)
        self._current_span = span
        return span

    def finish_span(self, span: Span):
        """结束 Span"""
        span.finish()
        self._current_span = None

    def get_current_span(self) -> Optional[Span]:
        return self._current_span

    def get_trace(self, trace_id: str) -> List[Dict]:
        """获取完整追踪"""
        return [
            {
                "name": s.name,
                "span_id": s.span_id,
                "parent_id": s.parent_id,
                "duration_ms": s.duration_ms,
                "start_time": s.start_time.isoformat(),
                "tags": s.tags,
            }
            for s in self.spans
            if s.trace_id == trace_id
        ]

    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_spans": len(self.spans),
            "traces": len(set(s.trace_id for s in self.spans)),
        }

    def clear(self):
        self.spans.clear()


tracer = Tracer()
