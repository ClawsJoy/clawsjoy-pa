#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音推文视频确定性流水线(参数化模板, 2026-09-07)
用法:
  python3 scripts/pipelines/douyin_video.py configs/fengqing.json   # 或任意配置路径
  python3 scripts/pipelines/douyin_video.py                          # 默认 scripts/pipelines/configs/weiren.json
配置 JSON(scripts/pipelines/configs/): {book_name, alias, output_slug, segs:[[口播,大字幕]x5]}
流程: 5段配音(edge-tts) -> 5张文字卡(PIL, 角标=书名 页脚=别名) -> ffmpeg合成 -> 封面
输出: data/videos/douyin_{slug}.mp4 + douyin_{slug}_cover.png(多书并存互不覆盖)
确定性: 一次跑通, 失败打印明确错误码退出(exit=returncode)。
"""
import os, sys, json, subprocess, shutil

FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
V = "zh-CN-YunjianNeural"
RATE = "+8%"
OUT_DIR = "data/videos"
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_config(arg):
    """配置解析: 显式路径 → cwd/configs/<名> → 脚本目录/configs/<名>"""
    cands = []
    if arg:
        cands.append(arg)                                          # 相对 cwd
        cands.append(os.path.join("configs", os.path.basename(arg)))
        cands.append(os.path.join(_SCRIPT_DIR, arg))               # 相对脚本目录
    cands.append(os.path.join(_SCRIPT_DIR, "configs", "weiren.json"))  # 默认模板
    for c in cands:
        if c and os.path.exists(c):
            return c
    sys.exit("配置未找到: %s" % arg)


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print("[FATAL] %s rc=%d" % (cmd[0], r.returncode), flush=True)
        print((r.stdout or "")[-300:], flush=True)
        print((r.stderr or "")[-300:], flush=True)
        sys.exit(r.returncode)
    return r


def tts(i, text):
    out = os.path.join(OUT_DIR, "dv_%s_v_%d.mp3" % (CFG["output_slug"], i))
    sh(["edge-tts", "--voice", V, "--rate", RATE, "--text", text, "--write-media", out], timeout=120)
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
    book = CFG["book_name"]
    alias = CFG["alias"]
    last = len(SEGS)
    tag = "钩子" if i == 1 else ("引导" if i == last else (book if len(book) <= 10 else book[:10] + "…"))
    if i in (1, last):
        d.rectangle([0, 0, W, 240], fill="#6a040f")
    else:
        d.rectangle([0, 0, W, 200], fill="#1a1a2e")
    d.text((W/2, 120 if i in (1, last) else 100), tag, font=f3, fill="#ffd166" if i in (1, last) else "#8a8a9a", anchor="mm")
    lines = big_text.split("|")
    y = 820
    for ln in lines:
        d.text((W/2, y), ln, font=f1, fill="#e8e8f0", anchor="mm", stroke_width=2, stroke_fill="#6a040f")
        y += 130
    d.rectangle([0, H-140, W, H], fill="#6a040f")
    d.text((W/2, H-70), alias, font=f2, fill="#ffffff", anchor="mm")
    p = os.path.join(OUT_DIR, "dv_%s_c_%d.png" % (CFG["output_slug"], i))
    img.save(p)
    return p


def main():
    global CFG, SEGS
    cfg_path = _resolve_config(sys.argv[1] if len(sys.argv) > 1 else "")
    CFG = json.load(open(cfg_path, encoding="utf-8"))
    SEGS = CFG["segs"]
    assert len(SEGS) == 5, "segs 需 5 段"
    slug = CFG["output_slug"]
    OUT_MP4 = os.path.join(OUT_DIR, "douyin_%s.mp4" % slug)
    OUT_COVER = os.path.join(OUT_DIR, "douyin_%s_cover.png" % slug)
    print("CONFIG %s book=%s alias=%s slug=%s segs=%d" % (cfg_path, CFG["book_name"], CFG["alias"], slug, len(SEGS)), flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    segs = []
    for i, (text, big) in enumerate(SEGS, 1):
        vo, dur = tts(i, text)
        c = card(i, big)
        segs.append((vo, c, dur))
    shutil.copy(segs[0][1], OUT_COVER)
    seg_mp4s = []
    for i, (vo, c, dur) in enumerate(segs, 1):
        seg_mp4 = os.path.join(OUT_DIR, "dv_%s_seg_%d.mp4" % (slug, i))
        sh(["ffmpeg", "-y", "-loop", "1", "-i", c, "-i", vo,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", seg_mp4], timeout=150)
        seg_mp4s.append(seg_mp4)
    lst = os.path.abspath(os.path.join(OUT_DIR, "dv_%s_list.txt" % slug))
    with open(lst, "w") as f:
        for m in seg_mp4s:
            f.write("file '%s'" % os.path.abspath(m) + chr(10))
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", OUT_MP4], timeout=150)
    total = round(sum(s[2] for s in segs), 1)
    print("DONE mp4=%s cover=%s total=%.1fs segs=%d" % (OUT_MP4, OUT_COVER, total, len(segs)), flush=True)
    print(json.dumps({"book": CFG["book_name"], "alias": CFG["alias"], "mp4": OUT_MP4, "cover": OUT_COVER,
                      "total_s": total, "segs": len(segs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
