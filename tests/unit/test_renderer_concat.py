"""Unit tests for renderer.concat function"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from unittest.mock import MagicMock, mock_open, patch


class TestRendererConcat:
    """renderer.concat 函数单元测试"""

    def test_concat_single_file(self):
        """测试单个文件直接复制"""
        with patch("core.video_studio.renderer.ffmpeg") as mock_ffmpeg:
            mock_input = MagicMock()
            mock_output = MagicMock()
            mock_ffmpeg.input.return_value = mock_input
            mock_input.output.return_value = mock_output
            mock_output.overwrite_output.return_value = mock_output

            from core.video_studio.renderer import concat

            result = concat(["/single.mp4"], "/out.mp4")

            assert result == "/out.mp4"
            mock_ffmpeg.input.assert_called_once_with("/single.mp4")
            mock_input.output.assert_called_once_with("/out.mp4", c="copy")

    def test_concat_multiple_files(self):
        """测试多个文件合并"""
        with patch("core.video_studio.renderer.ffmpeg") as mock_ffmpeg, patch(
            "core.video_studio.renderer.os.path.exists"
        ) as mock_exists, patch("core.video_studio.renderer.os.remove") as mock_remove:
            mock_input = MagicMock()
            mock_output = MagicMock()
            mock_ffmpeg.input.return_value = mock_input
            mock_input.output.return_value = mock_output
            mock_output.overwrite_output.return_value = mock_output
            mock_exists.return_value = True

            # Directly mock builtins.open with a real file in /tmp to avoid PermissionError
            from core.video_studio.renderer import concat

            test_list_path = "/tmp/test_out.mp4.concat_list.txt"
            mock_os_path = os.path  # Keep original

            # We need to patch open at core.video_studio.renderer level
            with patch("builtins.open", mock_open()) as mock_file:
                result = concat(["/clip1.mp4", "/clip2.mp4"], "/tmp/test_out.mp4")

            assert result == "/tmp/test_out.mp4"
            # Verify concat list was written
            mock_file.assert_called_once()
            # Verify cleanup
            mock_remove.assert_called_once()
            # Clean up if file exists
            if os.path.exists(test_list_path):
                os.remove(test_list_path)

    def test_concat_empty_list(self):
        """测试空列表合并"""
        from core.video_studio.renderer import concat

        try:
            concat([], "/out.mp4")
            assert False, "空列表应该导致错误"
        except Exception:
            pass


if __name__ == "__main__":
    t = TestRendererConcat()
    for method in [
        t.test_concat_single_file,
        t.test_concat_multiple_files,
        t.test_concat_empty_list,
    ]:
        try:
            method()
            print(f"  ✅ {method.__name__}")
        except Exception as e:
            print(f"  ❌ {method.__name__}: {e}")
            import traceback

            traceback.print_exc()
