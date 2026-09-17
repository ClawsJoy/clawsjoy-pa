"""Unit tests for Timeline model"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.video_studio.timeline import Clip, Timeline, Track


class TestTimeline:
    """Timeline 模型单元测试"""

    def test_create_empty_timeline(self):
        """创建空时间线"""
        tl = Timeline(id="tl1", name="我的时间线")
        assert tl.id == "tl1"
        assert tl.name == "我的时间线"
        assert tl.tracks == []
        assert tl.duration == 0.0
        assert tl.fps == 30.0
        assert tl.resolution == {"width": 1920, "height": 1080}

    def test_create_timeline_with_tracks(self):
        """创建包含轨道的时间线"""
        track1 = Track(id="t1", name="视频", type="video")
        track2 = Track(id="t2", name="音频", type="audio")
        tl = Timeline(id="tl2", name="项目", tracks=[track1, track2], duration=60.0)
        assert len(tl.tracks) == 2
        assert tl.duration == 60.0

    def test_timeline_to_dict(self):
        """Timeline.to_dict() 返回正确字典"""
        tl = Timeline(id="tl1", name="我的时间线", duration=30.0, fps=24.0)
        d = tl.to_dict()
        assert d["id"] == "tl1"
        assert d["name"] == "我的时间线"
        assert d["duration"] == 30.0
        assert d["fps"] == 24.0
        assert d["tracks"] == []

    def test_timeline_from_dict(self):
        """Timeline.from_dict() 从字典恢复对象"""
        data = {
            "id": "tl1",
            "name": "我的时间线",
            "tracks": [],
            "duration": 30.0,
            "fps": 24.0,
            "resolution": {"width": 1920, "height": 1080},
        }
        tl = Timeline.from_dict(data)
        assert tl.id == "tl1"
        assert tl.duration == 30.0
        assert tl.fps == 24.0

    def test_timeline_from_dict_with_tracks(self):
        """Timeline.from_dict() 从包含 Track 的字典恢复"""
        data = {
            "id": "tl1",
            "name": "时间线",
            "tracks": [
                {"id": "t1", "name": "视频", "type": "video", "clips": [], "locked": False, "hidden": False},
            ],
            "duration": 60.0,
            "fps": 30.0,
            "resolution": {"width": 1920, "height": 1080},
        }
        tl = Timeline.from_dict(data)
        assert len(tl.tracks) == 1
        assert tl.tracks[0].type == "video"

    def test_timeline_to_dict_with_nested(self):
        """包含 Track 和 Clip 的 Timeline 的 to_dict"""
        clip = Clip(id="c1", source_path="/path/v.mp4", start_time=0.0, end_time=5.0, duration=5.0, track_id="t1")
        track = Track(id="t1", name="视频", type="video", clips=[clip])
        tl = Timeline(id="tl1", name="项目", tracks=[track], duration=60.0)
        d = tl.to_dict()
        assert d["tracks"][0]["clips"][0]["id"] == "c1"

    def test_timeline_repr(self):
        """Timeline.__repr__ 格式正确"""
        tl = Timeline(id="tl1", name="测试")
        r = repr(tl)
        assert "Timeline(" in r
        assert "tl1" in r


if __name__ == "__main__":
    t = TestTimeline()
    for method in [
        t.test_create_empty_timeline,
        t.test_create_timeline_with_tracks,
        t.test_timeline_to_dict,
        t.test_timeline_from_dict,
        t.test_timeline_from_dict_with_tracks,
        t.test_timeline_to_dict_with_nested,
        t.test_timeline_repr,
    ]:
        try:
            method()
            print(f"  ✅ {method.__name__}")
        except Exception as e:
            print(f"  ❌ {method.__name__}: {e}")
