"""Unit tests for renderer.speed_change function"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from unittest.mock import MagicMock, patch


class TestRendererSpeed:
    """renderer.speed_change 函数单元测试"""

    def test_speed_up(self):
        """测试加速（2x）"""
        with patch("core.video_studio.renderer.ffmpeg") as mock_ffmpeg:
            mock_input = MagicMock()
            mock_output = MagicMock()
            mock_ffmpeg.input.return_value = mock_input
            mock_input.output.return_value = mock_output
            mock_output.overwrite_output.return_value = mock_output

            from core.video_studio.renderer import speed_change

            result = speed_change("/input.mp4", "/output.mp4", 2.0)

            assert result == "/output.mp4"
            mock_ffmpeg.input.assert_called_once_with("/input.mp4")
            mock_input.output.assert_called_once_with("/output.mp4", vf="setpts=0.5*PTS", af="atempo=2.0")
            mock_output.overwrite_output.assert_called_once()
            mock_output.run.assert_called_once_with(quiet=True)

    def test_slow_down(self):
        """测试减速（0.5x）"""
        with patch("core.video_studio.renderer.ffmpeg") as mock_ffmpeg:
            mock_input = MagicMock()
            mock_output = MagicMock()
            mock_ffmpeg.input.return_value = mock_input
            mock_input.output.return_value = mock_output
            mock_output.overwrite_output.return_value = mock_output

            from core.video_studio.renderer import speed_change

            result = speed_change("/input.mp4", "/output.mp4", 0.5)

            assert result == "/output.mp4"
            mock_input.output.assert_called_once_with("/output.mp4", vf="setpts=2.0*PTS", af="atempo=0.5")

    def test_speed_normal(self):
        """测试常速（1.0x）"""
        with patch("core.video_studio.renderer.ffmpeg") as mock_ffmpeg:
            mock_input = MagicMock()
            mock_output = MagicMock()
            mock_ffmpeg.input.return_value = mock_input
            mock_input.output.return_value = mock_output
            mock_output.overwrite_output.return_value = mock_output

            from core.video_studio.renderer import speed_change

            result = speed_change("/input.mp4", "/output.mp4", 1.0)

            assert result == "/output.mp4"
            mock_input.output.assert_called_once_with("/output.mp4", vf="setpts=1.0*PTS", af="atempo=1.0")


if __name__ == "__main__":
    t = TestRendererSpeed()
    for method in [
        t.test_speed_up,
        t.test_slow_down,
        t.test_speed_normal,
    ]:
        try:
            method()
            print(f"  ✅ {method.__name__}")
        except Exception as e:
            print(f"  ❌ {method.__name__}: {e}")
