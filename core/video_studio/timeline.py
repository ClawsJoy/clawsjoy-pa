from typing import List, Optional, Dict, Any


class Track:
    """轨道模型"""

    VALID_TYPES = {"video", "audio", "text", "effect"}

    def __init__(
        self,
        id: str,
        name: str,
        type: str,
        clips: Optional[List["Clip"]] = None,
        locked: bool = False,
        hidden: bool = False,
    ):
        if type not in self.VALID_TYPES:
            raise ValueError(f"Invalid track type: {type}. Must be one of {self.VALID_TYPES}")
        self.id = id
        self.name = name
        self.type = type
        self.clips = clips if clips is not None else []
        self.locked = locked
        self.hidden = hidden

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "clips": [clip.to_dict() for clip in self.clips],
            "locked": self.locked,
            "hidden": self.hidden,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Track":
        clips = [Clip.from_dict(c) for c in data.get("clips", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            type=data["type"],
            clips=clips,
            locked=data.get("locked", False),
            hidden=data.get("hidden", False),
        )

    def __repr__(self) -> str:
        return f"Track(id={self.id!r}, name={self.name!r}, type={self.type!r}, clips={len(self.clips)})"


class Clip:
    """片段模型"""

    def __init__(
        self,
        id: str,
        source_path: str,
        start_time: float,
        end_time: float,
        duration: float,
        track_id: str,
        speed: float = 1.0,
        volume: float = 1.0,
    ):
        self.id = id
        self.source_path = source_path
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.track_id = track_id
        self.speed = speed
        self.volume = volume

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_path": self.source_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "track_id": self.track_id,
            "speed": self.speed,
            "volume": self.volume,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Clip":
        return cls(
            id=data["id"],
            source_path=data["source_path"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            duration=data["duration"],
            track_id=data["track_id"],
            speed=data.get("speed", 1.0),
            volume=data.get("volume", 1.0),
        )

    def __repr__(self) -> str:
        return f"Clip(id={self.id!r}, source_path={self.source_path!r}, duration={self.duration})"


class Timeline:
    """时间线模型"""

    def __init__(
        self,
        id: str,
        name: str,
        tracks: Optional[List[Track]] = None,
        duration: float = 0.0,
        fps: float = 30.0,
        resolution: Optional[Dict[str, int]] = None,
    ):
        self.id = id
        self.name = name
        self.tracks = tracks if tracks is not None else []
        self.duration = duration
        self.fps = fps
        self.resolution = resolution if resolution is not None else {"width": 1920, "height": 1080}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tracks": [track.to_dict() for track in self.tracks],
            "duration": self.duration,
            "fps": self.fps,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Timeline":
        tracks = [Track.from_dict(t) for t in data.get("tracks", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            tracks=tracks,
            duration=data.get("duration", 0.0),
            fps=data.get("fps", 30.0),
            resolution=data.get("resolution", {"width": 1920, "height": 1080}),
        )

    def __repr__(self) -> str:
        return f"Timeline(id={self.id!r}, name={self.name!r}, tracks={len(self.tracks)}, duration={self.duration})"
