#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""伪人降临 抖音视频确定性流水线(项目级脚本, 跨 session 复用)
用法: python3 douyin_video_weiren.py
流程: 5段配音(edge-tts) -> 5张文字卡(PIL含字幕) -> ffmpeg合成 -> 封面
输出: data/videos/douyin_weiren.mp4 + douyin_weiren_cover.png
确定性: 一次跑通, 失败打印明确错误码退出(exit=returncode)。
"""
import os, subprocess, json, sys, shutil

FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
V = "zh-CN-YunjianNeural"
RATE = "+8%"
OUT_DIR = "data/videos"
OUT_MP4 = os.path.join(OUT_DIR, "douyin_weiren.mp4")
OUT_COVER = os.path.join(OUT_DIR, "douyin_weiren_cover.png")

# (口播文本, 大字幕多行用 | 分隔)
SEGS = [
    ("如果人群里混着伪人——长得和人一模一样，每天夜里都会杀一个人，你能分辨出来吗？",
     "你身边，有伪人吗？"),
    ("这座城市里，没人分得清，只能静待屠戮。直到林羊觉醒【预言家】：每天可以查验一个人，系统会告诉他——对方，是人，还是伪人？",
     "伪人·每晚杀一个|预言家·每日查验一人"),
    ("尊贵的预言家，您今日要查验的目标是——每天只能查一个：查自己最亲的人？查朝夕相处的同事？还是那个总盯着你的邻居？",
     "尊贵的预言家|您今日要查验的目标是——"),
    ("可城里的人，还在一个接一个消失。伪人，真的只有你看到的这一个吗？林羊下一个要查验的，又会是谁？",
     "真的只有这一个吗？"),
    ("悬疑脑洞已更到第 234 章，越往后越不敢睡。番茄小说APP，搜索「合拍人疏」，直接开看全文。",
     "番茄小说APP 搜索「合拍人疏」|直接开看全文"),
]

def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print("[FATAL] %s rc=%d" % (cmd[0], r.returncode), flush=True)
        print((r.stdout or "")[-300:], flush=True)
        print((r.stderr or "")[-300:], flush=True)
        sys.exit(r.returncode)
    return r

def tts(i, text):
    out = os.path.join(OUT_DIR, "wr_v_%d.mp3" % i)
    sh(["edge-tts", "--voice", V, "--rate", RATE, "--text", text, "--write-media", out], timeout=90)
    d = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", out])
    dur = float(d.stdout.strip()) if d.stdout.strip() else 4.0
    print("seg%d 配音 %.1fs" % (i, dur), flush=True)
    return out, dur

def card(i, big_text):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), "#0d0d14")
    d = ImageDraw.Draw(img)
    f1 = ImageFont.truetype(FONT, 88)
    f2 = ImageFont.truetype(FONT, 44)
    f3 = ImageFont.truetype(FONT, 32)
    if i in (1, 5):
        d.rectangle([0, 0, W, 240], fill="#6a040f")
        d.text((W/2, 120), "钩子" if i == 1 else "引导", font=f3, fill="#ffd166", anchor="mm")
    else:
        d.rectangle([0, 0, W, 200], fill="#1a1a2e")
        d.text((W/2, 100), "伪人降临 %d/5" % i, font=f3, fill="#8a8a9a", anchor="mm")
    lines = big_text.split("|")
    y = 820
    for ln in lines:
        d.text((W/2, y), ln, font=f1, fill="#e8e8f0", anchor="mm", stroke_width=2, stroke_fill="#6a040f")
        y += 130
    d.rectangle([0, H-140, W, H], fill="#6a040f")
    d.text((W/2, H-70), "合拍人疏", font=f2, fill="#ffffff", anchor="mm")
    p = os.path.join(OUT_DIR, "wr_c_%d.png" % i)
    img.save(p)
    return p

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    segs = []
    for i, (text, big) in enumerate(SEGS, 1):
        vo, dur = tts(i, text)
        c = card(i, big)
        segs.append((vo, c, dur))
    shutil.copy(segs[0][1], OUT_COVER)
    seg_mp4s = []
    for i, (vo, c, dur) in enumerate(segs, 1):
        seg_mp4 = os.path.join(OUT_DIR, "wr_seg_%d.mp4" % i)
        sh(["ffmpeg", "-y", "-loop", "1", "-i", c, "-i", vo,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", seg_mp4], timeout=120)
        seg_mp4s.append(seg_mp4)
    lst = os.path.abspath(os.path.join(OUT_DIR, "wr_list.txt"))
    with open(lst, "w") as f:
        for m in seg_mp4s:
            f.write("file '%s'" % os.path.abspath(m) + chr(10))
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", OUT_MP4], timeout=120)
    total = round(sum(s[2] for s in segs), 1)
    print("DONE mp4=%s cover=%s total=%.1fs" % (OUT_MP4, OUT_COVER, total), flush=True)
    print(json.dumps({"mp4": OUT_MP4, "cover": OUT_COVER, "total_s": total, "segs": len(segs)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
