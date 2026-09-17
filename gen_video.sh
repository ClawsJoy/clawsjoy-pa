#!/bin/bash
# 合成 6 段视频(卡片动画+配音) -> 拼接 -> 烧字幕 -> 1080p
cd data/videos || exit 1
# 每段时长(总220s≈3:40): 段1=14 段2=30 段3=55 段4=45 段5=40 段6=36
DURS=(14 30 55 45 40 36)
CONCAT=""
for i in 1 2 3 4 5 6; do
  dur=${DURS[$((i-1))]}
  CONCAT="${CONCAT}file 'seg${i}.mp4'
"
done
# 逐段生成
for i in 1 2 3 4 5 6; do
  dur=${DURS[$((i-1))]}
  ffmpeg -y -loop 1 -framerate 25 -i card${i}.png -i voice_${i}.mp3 \
    -filter_complex "[0:v]zoompan=z='min(zoom+0.0007,1.06)':d=25*${dur}:s=1920x1080:fps=25,fade=t=in:st=0:d=0.5,fade=t=out:st=$((dur-1)):d=1,format=yuv420p[v];[1:a]apad[a]" \
    -map "[v]" -map "[a]" -t ${dur} -c:v libx264 -preset fast -crf 22 -c:a aac -b:a 128k \
    seg${i}.mp4 2>seg${i}.err || echo "seg${i} FAIL"
  echo "seg${i} done ${dur}s"
done
# 拼接
printf "$CONCAT" > concat.txt
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy merged_nosub.mp4 2>merge.err || echo "merge FAIL"
# 烧字幕
ffmpeg -y -i merged_nosub.mp4 -vf "subtitles=subtitle.srt:force_style='FontName=WenQuanYi Micro Hei,FontSize=20,PrimaryColour=&H00FFFFFF,Outline=1'" \
  -c:v libx264 -preset fast -crf 20 -c:a copy ../bilibili_kaoyan_ai.mp4 2>sub.err || echo "subtitle FAIL"
echo "ALL DONE"
