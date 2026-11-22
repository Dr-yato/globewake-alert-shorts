#!/bin/bash
# usage: finish_alert.sh <project_dir> <out.mp4>
# two-pass 1080×1920 encode, remux assets/audio/mix.wav, QC (decode, LUFS, peak, letterbox, black frames)
set -e
P=$(realpath "$1"); O=$(realpath -m "$2"); R=$P/renders/raw.mp4; MIX=$P/assets/audio/mix.wav
mkdir -p "$(dirname "$O")"; cd "$P/renders"
if [ ! -f "$MIX" ]; then echo "missing $MIX — run scripts/mix_alert.py first"; exit 1; fi
ffmpeg -y -v error -i "$R" -c:v libx264 -preset slow -b:v 3200k -pass 1 -passlogfile pass -an -f null -
ffmpeg -y -v error -i "$R" -i "$MIX" -map 0:v:0 -map 1:a:0 \
  -vf "scale=1080:1920:flags=lanczos,setsar=1" \
  -c:v libx264 -preset slow -b:v 3200k -maxrate 5000k -bufsize 8000k \
  -pass 2 -passlogfile pass -pix_fmt yuv420p -profile:v high -r 30 -aspect 9:16 \
  -c:a aac -b:a 160k -ar 48000 -movflags +faststart -shortest "$O"
ls -l "$O"
ffprobe -v error -show_entries stream=codec_name,width,height,sample_aspect_ratio,display_aspect_ratio,r_frame_rate,sample_rate:format=duration -of compact "$O"
ffmpeg -v error -i "$O" -f null - && echo DECODE_OK
ffmpeg -nostats -i "$O" -af ebur128=peak=true -f null - 2>&1 | sed -n '/Summary:/,$p' | sed -n '1,20p'
ffmpeg -v info -ss 1 -i "$O" -frames:v 60 -vf cropdetect=24:16:0 -f null - 2>&1 | grep -o 'crop=[0-9:]*' | tail -1
ffmpeg -v info -i "$O" -vf blackdetect=d=0.3:pix_th=0.05 -an -f null - 2>&1 | grep blackdetect || echo NO_BLACK
md5sum "$O"
