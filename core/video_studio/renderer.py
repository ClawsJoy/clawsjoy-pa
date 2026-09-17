"""视频渲染器 - 封装 ffmpeg-python 实现视频编辑操作"""

import json
import os
from typing import List, Optional, Dict, Any

import ffmpeg


def trim(input_path: str, output_path: str, start_time: float, end_time: float) -> str:
    """裁剪视频片段

    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
        start_time: 起始时间（秒）
        end_time: 结束时间（秒）

    Returns:
        输出文件路径
    """
    duration = end_time - start_time
    (
        ffmpeg
        .input(input_path, ss=start_time, t=duration)
        .output(output_path, c="copy")
        .overwrite_output()
        .run(quiet=True)
    )
    return output_path


def concat(clip_paths: List[str], output_path: str) -> str:
    """合并多个视频片段

    使用 concat demuxer，需要所有视频编码格式一致。

    Args:
        clip_paths: 视频片段路径列表
        output_path: 输出视频路径

    Returns:
        输出文件路径
    """
    if len(clip_paths) == 1:
        # 只有一个文件，直接复制
        (
            ffmpeg
            .input(clip_paths[0])
            .output(output_path, c="copy")
            .overwrite_output()
            .run(quiet=True)
        )
        return output_path

    # 创建临时文件列表
    list_path = output_path + ".concat_list.txt"
    try:
        with open(list_path, "w", encoding="utf-8") as f:
            for path in clip_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")

        (
            ffmpeg
            .input(list_path, format="concat", safe=0)
            .output(output_path, c="copy")
            .overwrite_output()
            .run(quiet=True)
        )
    finally:
        if os.path.exists(list_path):
            os.remove(list_path)

    return output_path


def speed_change(input_path: str, output_path: str, speed: float) -> str:
    """变速处理

    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
        speed: 速度倍数（>1 加速，<1 减速）

    Returns:
        输出文件路径
    """
    # 视频变速用 setpts，音频变速用 atempo
    video_filter = f"setpts={1/speed}*PTS"
    audio_filter = f"atempo={speed}"

    (
        ffmpeg
        .input(input_path)
        .output(output_path, vf=video_filter, af=audio_filter)
        .overwrite_output()
        .run(quiet=True)
    )
    return output_path


def add_audio(
    input_path: str,
    audio_path: str,
    output_path: str,
    volume: float = 1.0,
) -> str:
    """替换或叠加音轨

    将音频叠加到视频中，原视频音频被替换。

    Args:
        input_path: 输入视频路径
        audio_path: 输入音频路径
        output_path: 输出视频路径
        volume: 音量倍数（默认 1.0）

    Returns:
        输出文件路径
    """
    video = ffmpeg.input(input_path)
    audio = ffmpeg.input(audio_path)

    # 调整音量后混音
    audio_adjusted = audio.audio.filter("volume", volume=volume)

    (
        ffmpeg
        .output(video.video, audio_adjusted, output_path, shortest=None)
        .overwrite_output()
        .run(quiet=True)
    )
    return output_path


def get_video_info(input_path: str) -> Dict[str, Any]:
    """获取视频信息

    Args:
        input_path: 输入视频路径

    Returns:
        包含视频信息的字典：duration（时长秒）、width、height、
        codec（视频编码）、audio_codec（音频编码）、bitrate（比特率）
    """
    probe = ffmpeg.probe(input_path)

    video_stream = None
    audio_stream = None

    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video" and video_stream is None:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = stream

    info: Dict[str, Any] = {}

    # 时长优先从 format 取
    format_info = probe.get("format", {})
    duration_str = format_info.get("duration")
    if duration_str:
        info["duration"] = float(duration_str)

    if video_stream:
        info["width"] = video_stream.get("width")
        info["height"] = video_stream.get("height")
        info["codec"] = video_stream.get("codec_name")
        info["codec_long_name"] = video_stream.get("codec_long_name")

        # 如果 format 没有 duration，从视频流取
        if "duration" not in info:
            v_duration = video_stream.get("duration")
            if v_duration:
                info["duration"] = float(v_duration)

    if audio_stream:
        info["audio_codec"] = audio_stream.get("codec_name")
        info["audio_sample_rate"] = audio_stream.get("sample_rate")
        info["audio_channels"] = audio_stream.get("channels")

    if format_info:
        bitrate_str = format_info.get("bit_rate")
        if bitrate_str:
            info["bitrate"] = int(bitrate_str)

    return info
