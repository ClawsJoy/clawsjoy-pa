# -*- coding: utf-8 -*-
"""PA 路由 · notebooks（第二大脑 P1 · 对标 NotebookLM 的笔记本层）。

只挂 /v9/pa/notebooks*；来源仍是 note（/v9/pa/notes*），本层只做归属/检索/生成。
"""
from flask import request

from core.pa.pa_routes_common import bp, err, ok, _loopback
from core.pa import notebooks as NB

MAX_PDF_READ = 50 * 1024 * 1024 + 1


def _body():
    d = request.get_json(silent=True) or {}
    return d if isinstance(d, dict) else {}


def _guard():
    if not _loopback(request):
        return err("仅本机", 403)
    return None


def register(bp):
    @bp.route("/v9/pa/notebooks", methods=["GET"])
    def pa_nb_list():
        g = _guard()
        if g:
            return g
        try:
            return ok({"notebooks": NB.list_notebooks()})
        except NB.NotebookError as e:
            return err(str(e), 409)
        except Exception as e:
            return err("取笔记本失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks", methods=["POST"])
    def pa_nb_create():
        g = _guard()
        if g:
            return g
        d = _body()
        try:
            nb = NB.create(d.get("title", ""), d.get("emoji") or "📘", d.get("description") or "")
            return ok({"notebook": nb})
        except NB.NotebookError as e:
            return err(str(e), 400)
        except Exception as e:
            return err("建笔记本失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>", methods=["GET"])
    def pa_nb_get(nb_id):
        g = _guard()
        if g:
            return g
        try:
            return ok({"notebook": NB.get(nb_id)})
        except NB.NotebookError as e:
            return err(str(e), 404)
        except Exception as e:
            return err("读笔记本失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>", methods=["PATCH"])
    def pa_nb_update(nb_id):
        g = _guard()
        if g:
            return g
        d = _body()
        try:
            nb = NB.update(nb_id, title=d.get("title"), emoji=d.get("emoji"),
                           description=d.get("description"))
            return ok({"notebook": nb})
        except NB.NotebookError as e:
            return err(str(e), 404 if "不存在" in str(e) else 400)
        except Exception as e:
            return err("改笔记本失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>", methods=["DELETE"])
    def pa_nb_delete(nb_id):
        g = _guard()
        if g:
            return g
        try:
            return ok(NB.delete(nb_id))
        except NB.NotebookError as e:
            return err(str(e), 404 if "不存在" in str(e) else 400)
        except Exception as e:
            return err("删笔记本失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>/sources", methods=["GET"])
    def pa_nb_sources(nb_id):
        g = _guard()
        if g:
            return g
        try:
            return ok({"sources": NB.sources(nb_id)})
        except NB.NotebookError as e:
            return err(str(e), 404)
        except Exception as e:
            return err("取来源失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>/sources/text", methods=["POST"])
    def pa_nb_add_text(nb_id):
        g = _guard()
        if g:
            return g
        d = _body()
        body = str(d.get("body") or "")
        if not body.strip():
            return err("正文为空", 400)
        try:
            n = NB.add_text(nb_id, d.get("title", ""), body, d.get("tags") or [],
                            source="manual")
            return ok({"source": n})
        except NB.NotebookError as e:
            return err(str(e), 404)
        except Exception as e:
            return err("加来源失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>/sources/url", methods=["POST"])
    def pa_nb_add_url(nb_id):
        g = _guard()
        if g:
            return g
        d = _body()
        try:
            return ok(NB.add_url(nb_id, d.get("url", "")))
        except NB.NotebookError as e:
            return err(str(e), 400)
        except Exception as e:
            return err("抓网页失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>/sources/pdf", methods=["POST"])
    def pa_nb_add_pdf(nb_id):
        g = _guard()
        if g:
            return g
        f = request.files.get("file")
        if f is None:
            return err("须上传 file（PDF）", 400)
        try:
            raw = f.read(MAX_PDF_READ)
            return ok(NB.add_pdf(nb_id, f.filename or "source.pdf", raw))
        except NB.NotebookError as e:
            return err(str(e), 400)
        except Exception as e:
            return err("读 PDF 失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>/ask", methods=["POST"])
    def pa_nb_ask(nb_id):
        g = _guard()
        if g:
            return g
        d = _body()
        _model = None
        if str(d.get("model") or "").strip():
            from core.pa.providers import resolve_model_ex as _rm
            _model, _why = _rm(d.get("model"))
            if not _model:
                return err(_why, 400)
        try:
            _kw = {"model": _model} if _model else {}
            return ok(NB.ask(nb_id, d.get("q", ""), limit=d.get("limit", 6),
                              note_ids=d.get("note_ids"), **_kw))
        except NB.NotebookError as e:
            return err(str(e), 404 if "不存在" in str(e) else 400)
        except Exception as e:
            return err("问答失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>/studio", methods=["POST"])
    def pa_nb_studio(nb_id):
        g = _guard()
        if g:
            return g
        d = _body()
        _model = None
        if str(d.get("model") or "").strip():
            from core.pa.providers import resolve_model_ex as _rm
            _model, _why = _rm(d.get("model"))
            if not _model:
                return err(_why, 400)
        try:
            _kw = {"model": _model} if _model else {}
            return ok(NB.studio(nb_id, d.get("kind") or "summary", note_ids=d.get("note_ids"),
                                options=d.get("options"), **_kw))
        except NB.NotebookError as e:
            return err(str(e), 400)
        except Exception as e:
            return err("生成失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>/outputs", methods=["GET"])
    def pa_nb_outputs(nb_id):
        g = _guard()
        if g:
            return g
        try:
            return ok({"outputs": NB.recent_outputs(nb_id)})
        except NB.NotebookError as e:
            return err(str(e), 404)
        except Exception as e:
            return err("取产出失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notebooks/<nb_id>/notes", methods=["POST"])
    def pa_nb_save_output(nb_id):
        g = _guard()
        if g:
            return g
        d = _body()
        body = str(d.get("body") or "")
        if not body.strip():
            return err("正文为空", 400)
        try:
            n = NB.save_output(nb_id, d.get("title", ""), body, d.get("kind") or "summary")
            return ok({"note": n})
        except NB.NotebookError as e:
            return err(str(e), 404)
        except Exception as e:
            return err("存产出失败：%s" % type(e).__name__, 500)

    return bp


register(bp)
