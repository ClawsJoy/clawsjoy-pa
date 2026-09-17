"""Unit tests for renderer.trim function"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from unittest.mock import MagicMock, patch


class TestRendererTrim:
    """renderer.trim 函数单元测试"""

    def test_trim_basic(self):
        """测试基本裁剪功能"""
        with patch("core.video_studio.renderer.ffmpeg") as mock_ffmpeg:
            # Setup mock chain
            mock_input = MagicMock()
            mock_output = MagicMock()
            mock_ffmpeg.input.return_value = mock_input
            mock_input.output.return_value = mock_output
            mock_output.overwrite_output.return_value = mock_output

            from core.video_studio.renderer import trim

            result = trim("/input.mp4", "/output.mp4", 10.0, 20.0)

            assert result == "/output.mp4"
            mock_ffmpeg.input.assert_called_once_with("/input.mp4", ss=10.0, t=10.0)
            mock_input.output.assert_called_once_with("/output.mp4", c="copy")
            mock_output.overwrite_output.assert_called_once()
            mock_output.run.assert_called_once_with(quiet=True)

    def test_trim_custom_times(self):
        """测试自定义时间裁剪"""
        with patch("core.video_studio.renderer.ffmpeg") as mock_ffmpeg:
            mock_input = MagicMock()
            mock_output = MagicMock()
            mock_ffmpeg.input.return_value = mock_input
            mock_input.output.return_value = mock_output
            mock_output.overwrite_output.return_value = mock_output

            from core.video_studio.renderer import trim

            result = trim("/in.mp4", "/out.mp4", 5.5, 15.5)

            assert result == "/out.mp4"
            mock_ffmpeg.input.assert_called_once_with("/in.mp4", ss=5.5, t=10.0)

    def test_trim_zero_duration(self):
        """测试零时长裁剪"""
        with patch("core.video_studio.renderer.ffmpeg") as mock_ffmpeg:
            mock_input = MagicMock()
            mock_output = MagicMock()
            mock_ffmpeg.input.return_value = mock_input
            mock_input.output.return_value = mock_output
            mock_output.overwrite_output.return_value = mock_output

            from core.video_studio.renderer import trim

            result = trim("/in.mp4", "/out.mp4", 10.0, 10.0)

            assert result == "/out.mp4"
            mock_ffmpeg.input.assert_called_once_with("/in.mp4", ss=10.0, t=0.0)


if __name__ == "__main__":
    t = TestRendererTrim()
    for method in [
        t.test_trim_basic,
        t.test_trim_custom_times,
        t.test_trim_zero_duration,
    ]:
        try:
            method()
            print(f"  ✅ {method.__name__}")
        except Exception as e:
            print(f"  ❌ {method.__name__}: {e}")
