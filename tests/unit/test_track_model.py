"""Unit tests for Track model"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.video_studio.timeline import Clip, Track


class TestTrack:
    """Track 模型单元测试"""

    def test_create_valid_track(self):
        """创建有效类型的轨道"""
        track = Track(id="t1", name="视频轨道", type="video")
        assert track.id == "t1"
        assert track.name == "视频轨道"
        assert track.type == "video"
        assert track.clips == []
        assert track.locked is False
        assert track.hidden is False

    def test_create_invalid_track_type(self):
        """创建无效类型的轨道应抛出 ValueError"""
        try:
            Track(id="t1", name="无效轨道", type="invalid_type")
            assert False, "应抛出 ValueError"
        except ValueError as e:
            assert "Invalid track type" in str(e)

    def test_track_to_dict(self):
        """Track.to_dict() 返回正确字典"""
        track = Track(id="t1", name="视频轨道", type="video")
        d = track.to_dict()
        assert d["id"] == "t1"
        assert d["name"] == "视频轨道"
        assert d["type"] == "video"
        assert d["clips"] == []
        assert d["locked"] is False
        assert d["hidden"] is False

    def test_track_from_dict(self):
        """Track.from_dict() 从字典恢复对象"""
        data = {
            "id": "t1",
            "name": "视频轨道",
            "type": "video",
            "clips": [],
            "locked": True,
            "hidden": False,
        }
        track = Track.from_dict(data)
        assert track.id == "t1"
        assert track.name == "视频轨道"
        assert track.type == "video"
        assert track.locked is True

    def test_track_with_clips_to_dict(self):
        """包含 Clip 的 Track 的 to_dict"""
        clip = Clip(id="c1", source_path="/path/video.mp4", start_time=0.0, end_time=10.0, duration=10.0, track_id="t1")
        track = Track(id="t1", name="视频轨道", type="video", clips=[clip])
        d = track.to_dict()
        assert len(d["clips"]) == 1
        assert d["clips"][0]["id"] == "c1"
        assert d["clips"][0]["source_path"] == "/path/video.mp4"

    def test_track_all_valid_types(self):
        """所有有效轨道类型均可创建"""
        for t in Track.VALID_TYPES:
            track = Track(id=f"t_{t}", name=t, type=t)
            assert track.type == t

    def test_track_repr(self):
        """Track.__repr__ 格式正确"""
        track = Track(id="t1", name="视频轨道", type="video")
        r = repr(track)
        assert "Track(" in r
        assert "t1" in r
        assert "视频轨道" in r


if __name__ == "__main__":
    t = TestTrack()
    for method in [
        t.test_create_valid_track,
        t.test_create_invalid_track_type,
        t.test_track_to_dict,
        t.test_track_from_dict,
        t.test_track_with_clips_to_dict,
        t.test_track_all_valid_types,
        t.test_track_repr,
    ]:
        try:
            method()
            print(f"  ✅ {method.__name__}")
        except Exception as e:
            print(f"  ❌ {method.__name__}: {e}")
