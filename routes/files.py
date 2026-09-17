# -*- coding: utf-8 -*-
"""文件中心路由（P1 拆出，Blueprint）—— 薄包装 → core.gateway.file_center"""

from flask import Blueprint

bp = Blueprint("files", __name__)


@bp.route("/v9/files", methods=["GET"])
def v9_files_list():
    from core.gateway.file_center import v9_files_list_handler

    return v9_files_list_handler()


@bp.route("/v9/files/content", methods=["GET"])
def v9_files_content():
    from core.gateway.file_center import v9_files_content_handler

    return v9_files_content_handler()


@bp.route("/v9/files/diffs", methods=["GET"])
def v9_files_diffs():
    from core.gateway.file_center import v9_files_diffs_handler

    return v9_files_diffs_handler()


@bp.route("/v9/files/download", methods=["GET"])
def v9_files_download():
    from core.gateway.file_center import v9_files_download_handler

    return v9_files_download_handler()


@bp.route("/v9/media", methods=["GET"])
def v9_media():
    from core.gateway.file_center import v9_media_handler

    return v9_media_handler()


@bp.route("/v9/files/save", methods=["POST"])
def v9_files_save():
    from core.gateway.file_center import v9_files_save_handler

    return v9_files_save_handler()
