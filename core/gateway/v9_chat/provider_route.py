"""Provider-aware route for V9 chat (no model-name guessing)."""

from core.pa import providers as _p


def route_for_model(name):
    """用户选中 model ⇒ 注册表 route；默认/未识 ⇒ default_route()。"""
    _id, _note = _p.resolve_model_ex(name)
    if _id:
        for _pid, _prov in _p.PROVIDERS.items():
            if not _p.is_enabled(_pid):
                continue
            for _m in _prov.get("models") or []:
                if _m.get("id") == _id:
                    return ({"provider": _pid, "model": _id, "thinking": None}, _note)
    return _p.default_route()
