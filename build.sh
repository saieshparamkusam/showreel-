#!/usr/bin/env bash
# Rebuild the showreel: pip install pillow numpy scipy fonttools brotli ; ffmpeg required.
set -e
cd "$(dirname "$0")"
python3 src/audio.py                      # -> out/audio_raw.wav (synthesised score + SFX)
python3 src/render.py                     # -> out/chunks/*.mp4 (1800 frames, 4 parallel workers)
ffmpeg -y -f concat -safe 0 -i out/chunks/list.txt -c copy out/video_only.mp4
ffmpeg -y -i out/audio_raw.wav -af "loudnorm=I=-14:TP=-1.5:LRA=9,apad=whole_dur=60,atrim=0:60" -ar 48000 out/audio.wav
ffmpeg -y -i out/video_only.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v libx264 -preset slow -crf 22 -maxrate 10M -bufsize 20M \
  -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 -g 60 -c:a aac -b:a 256k -t 60 -movflags +faststart \
  out/Jeevan_Saiesh_Paramkusam_Showreel_60s.mp4
