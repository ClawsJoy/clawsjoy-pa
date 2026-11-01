# -*- coding: utf-8 -*-
"""PA 路由 · notes（第二大脑 P0）。

只挂 /v9/pa/notes*；文件是唯一真相，索引可重建。
"""
import os
import tempfile

from flask import jsonify, request
from core.pa.pa_routes_common import bp, err, ok, _loopback
from core.pa import notes as N
from core.pa import classify as C
from core.pa import labels as L
from core.pa import voice as V
from core.pa import screen as S


def _body():
    d = request.get_json(silent=True) or {}
    return d if isinstance(d, dict) else {}


def _guard():
    if not _loopback(request):
        return err("仅本机", 403)
    return None


def register(bp):
    @bp.route("/v9/pa/notes", methods=["GET"])
    def pa_notes_list():
        g = _guard()
        if g:
            return g
        try:
            q = request.args.get("q", "")
            limit = request.args.get("limit", "50")
            return ok({"notes": N.list_notes(q=q, limit=int(limit))})
        except Exception as e:
            return err("取笔记失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notes", methods=["POST"])
    def pa_notes_create():
        g = _guard()
        if g:
            return g
        d = _body()
        try:
            n = N.create(d.get("title", ""), d.get("body", ""), d.get("tags") or [])
            return ok({"note": n})
        except N.NoteError as e:
            return err(str(e), 400)
        except Exception as e:
            return err("建笔记失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notes/voice", methods=["POST"])
    def pa_notes_voice():
        g = _guard()
        if g:
            return g
        f = request.files.get("file")
        if f is None:
            return err("须上传 file（音频）", 400)
        try:
            raw = f.read(V.MAX_AUDIO + 1)
            out = V.voice_note(filename=f.filename or "voice.webm", audio_bytes=raw,
                               language=(request.form.get("language") or "zh"))
            return ok(out)
        except Exception as e:
            return err("语音转写失败：%s" % str(e)[:300], 400)

    @bp.route("/v9/pa/notes/transcribe", methods=["POST"])
    def pa_notes_transcribe():
        g = _guard()
        if g:
            return g
        f = request.files.get("file")
        if f is None:
            return err("须上传 file（音频）", 400)
        tmp = ""
        try:
            raw = f.read(V.MAX_AUDIO + 1)
            if not raw:
                return err("空音频", 400)
            suffix = os.path.splitext(f.filename or "clip.webm")[1] or ".webm"
            fd, tmp = tempfile.mkstemp(prefix="pa_caption_", suffix=suffix)
            os.close(fd)
            with open(tmp, "wb") as out:
                out.write(raw)
            tr = V.transcribe_audio(tmp, language=(request.form.get("language") or "zh"))
            return ok({"transcript": tr})
        except Exception as e:
            return err("字幕转写失败：%s" % str(e)[:300], 400)
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

    @bp.route("/v9/pa/notes/screen", methods=["POST"])
    def pa_notes_screen():
        g = _guard()
        if g:
            return g
        f = request.files.get("file")
        if f is None:
            return err("须上传 file（视频）", 400)
        try:
            raw = f.read(S.MAX_SCREEN + 1)
            out = S.screen_note(filename=f.filename or "screen.webm", video_bytes=raw,
                                language=(request.form.get("language") or "zh"))
            return ok(out)
        except Exception as e:
            return err("录屏处理失败：%s" % str(e)[:300], 400)

    @bp.route("/v9/pa/notes/ask", methods=["POST"])
    def pa_notes_ask():
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
            out = N.ask(d.get("q", ""), limit=d.get("limit", 6), model=_model)
            return ok(out)
        except N.NoteError as e:
            return err(str(e), 400)
        except Exception as e:
            return err("问答失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/labels", methods=["GET", "POST"])
    def pa_labels():
        g = _guard()
        if g:
            return g
        if request.method == "GET":
            return ok({"labels": L.list_labels()})
        d = _body()
        try:
            return ok({"label": L.add(d.get("name"))})
        except ValueError as e:
            return err(str(e), 400)

    @bp.route("/v9/pa/labels/<path:name>", methods=["PATCH", "DELETE"])
    def pa_label_item(name):
        g = _guard()
        if g:
            return g
        if request.method == "DELETE":
            return ok(L.delete(name))
        d = _body()
        try:
            return ok(L.rename(name, d.get("name")))
        except ValueError as e:
            return err(str(e), 400)

    @bp.route("/v9/pa/notes/<note_id>/label", methods=["POST"])
    def pa_note_label(note_id):
        g = _guard()
        if g:
            return g
        d = _body()
        try:
            n = N.update(note_id, category=d.get("category") or "", category_auto=False)
            return ok({"note": n})
        except N.NoteError as e:
            return err(str(e), 404 if "不存在" in str(e) else 400)

    @bp.route("/v9/pa/notes/unlabel_auto", methods=["POST"])
    def pa_notes_unlabel_auto():
        g = _guard()
        if g:
            return g
        return ok({"cleared": N.clear_auto_labels()})

    @bp.route("/v9/pa/notes/<note_id>/classify", methods=["POST"])
    def pa_notes_classify(note_id):
        g = _guard()
        if g:
            return g
        try:
            r = C.classify_note(note_id)
            r["suggestion"] = C.suggest_notebook(r)
            return ok(r)
        except N.NoteError as e:
            return err(str(e), 404 if "不存在" in str(e) else 400)
        except Exception as e:
            return err("整理失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notes/organize_all", methods=["POST"])
    def pa_notes_organize_all():
        g = _guard()
        if g:
            return g
        d = _body()
        try:
            return ok(C.organize_all(only_uncategorized=bool(d.get("only_uncategorized"))))
        except Exception as e:
            return err("启动整理失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notes/organize_status", methods=["GET"])
    def pa_notes_organize_status():
        g = _guard()
        if g:
            return g
        return ok(C.organize_status())

    @bp.route("/v9/pa/notes/organize", methods=["POST"])
    def pa_notes_organize():
        g = _guard()
        if g:
            return g
        d = _body()
        ids = d.get("ids")
        if not isinstance(ids, list) or not ids:
            return err("须给 ids（笔记 id 数组）", 400)
        try:
            return ok({"results": C.classify_many(ids, limit=d.get("limit", 8))})
        except Exception as e:
            return err("批量整理失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notes/<note_id>", methods=["GET"])
    def pa_notes_get(note_id):
        g = _guard()
        if g:
            return g
        try:
            return ok({"note": N.get(note_id)})
        except N.NoteError as e:
            return err(str(e), 404)
        except Exception as e:
            return err("读笔记失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notes/<note_id>", methods=["PATCH"])
    def pa_notes_update(note_id):
        g = _guard()
        if g:
            return g
        d = _body()
        try:
            n = N.update(note_id, title=d.get("title"), body=d.get("body"), tags=d.get("tags"),
                         notebook_id=d.get("notebook_id"),
                         category=d.get("category") if "category" in d else None)
            return ok({"note": n})
        except N.NoteError as e:
            return err(str(e), 404 if "不存在" in str(e) else 400)
        except Exception as e:
            return err("改笔记失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notes/<note_id>", methods=["DELETE"])
    def pa_notes_delete(note_id):
        g = _guard()
        if g:
            return g
        try:
            return ok(N.delete(note_id))
        except N.NoteError as e:
            return err(str(e), 400)
        except Exception as e:
            return err("删笔记失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notes/import", methods=["POST"])
    def pa_notes_import():
        g = _guard()
        if g:
            return g
        d = _body()
        path = str(d.get("path") or "").strip()
        if not path:
            return err("须给 path（目录）", 400)
        try:
            return ok(N.import_dir(path))
        except N.NoteError as e:
            return err(str(e), 400)
        except Exception as e:
            return err("导入失败：%s" % type(e).__name__, 500)

    @bp.route("/v9/pa/notes/reindex", methods=["POST"])
    def pa_notes_reindex():
        g = _guard()
        if g:
            return g
        try:
            return ok(N.reindex())
        except Exception as e:
            return err("重建索引失败：%s" % type(e).__name__, 500)

    return bp


register(bp)
