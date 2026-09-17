"""Unit tests for Clip model"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.video_studio.timeline import Clip


class TestClip:
    """Clip 模型单元测试"""

    def test_create_clip_defaults(self):
        """创建 Clip，使用默认参数"""
        clip = Clip(id="c1", source_path="/path/video.mp4", start_time=0.0, end_time=10.0, duration=10.0, track_id="t1")
        assert clip.id == "c1"
        assert clip.source_path == "/path/video.mp4"
        assert clip.start_time == 0.0
        assert clip.end_time == 10.0
        assert clip.duration == 10.0
        assert clip.track_id == "t1"
        assert clip.speed == 1.0
        assert clip.volume == 1.0

    def test_create_clip_custom_params(self):
        """创建 Clip，使用自定义参数"""
        clip = Clip(
            id="c2",
            source_path="/path/audio.mp3",
            start_time=5.0,
            end_time=15.0,
            duration=10.0,
            track_id="t2",
            speed=2.0,
            volume=0.5,
        )
        assert clip.speed == 2.0
        assert clip.volume == 0.5

    def test_clip_to_dict(self):
        """Clip.to_dict() 返回正确字典"""
        clip = Clip(id="c1", source_path="/path/video.mp4", start_time=0.0, end_time=10.0, duration=10.0, track_id="t1")
        d = clip.to_dict()
        assert d["id"] == "c1"
        assert d["source_path"] == "/path/video.mp4"
        assert d["start_time"] == 0.0
        assert d["end_time"] == 10.0
        assert d["duration"] == 10.0
        assert d["track_id"] == "t1"
        assert d["speed"] == 1.0
        assert d["volume"] == 1.0

    def test_clip_from_dict(self):
        """Clip.from_dict() 从字典恢复对象"""
        data = {
            "id": "c1",
            "source_path": "/path/video.mp4",
            "start_time": 0.0,
            "end_time": 10.0,
            "duration": 10.0,
            "track_id": "t1",
            "speed": 1.5,
            "volume": 0.8,
        }
        clip = Clip.from_dict(data)
        assert clip.id == "c1"
        assert clip.speed == 1.5
        assert clip.volume == 0.8

    def test_clip_from_dict_defaults(self):
        """Clip.from_dict() 使用缺失字段的默认值"""
        data = {
            "id": "c1",
            "source_path": "/path/video.mp4",
            "start_time": 0.0,
            "end_time": 10.0,
            "duration": 10.0,
            "track_id": "t1",
        }
        clip = Clip.from_dict(data)
        assert clip.speed == 1.0
        assert clip.volume == 1.0

    def test_clip_repr(self):
        """Clip.__repr__ 格式正确"""
        clip = Clip(id="c1", source_path="/path/video.mp4", start_time=0.0, end_time=10.0, duration=10.0, track_id="t1")
        r = repr(clip)
        assert "Clip(" in r
        assert "c1" in r
        assert "/path/video.mp4" in r


if __name__ == "__main__":
    t = TestClip()
    for method in [
        t.test_create_clip_defaults,
        t.test_create_clip_custom_params,
        t.test_clip_to_dict,
        t.test_clip_from_dict,
        t.test_clip_from_dict_defaults,
        t.test_clip_repr,
    ]:
        try:
            method()
            print(f"  ✅ {method.__name__}")
        except Exception as e:
            print(f"  ❌ {method.__name__}: {e}")
