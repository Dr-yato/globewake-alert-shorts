#!/usr/bin/env python3
"""ALERT Short mix (no voice): music bed + quieter hit/whoosh/typing cues -> assets/audio/mix.wav, about -14 LUFS / -3 dBTP (leaves AAC headroom).
The standing bed is Trevor Morris, "Hvitserk's Choice" (fetch_music.py). Do not commit the wav.

alert.json "audio": {
  "bed": file, "bed_gain": 0.4, "bed_start": 0,   # bed_start in seconds if the file is the full official track
  "bed_fade_in": 0.3,
  "cues": [{"file":..., "t":sec, "gain":.., "dur":optional trim}]
}
Recommended quieter SFX gains: alert hit 0.55, whoosh 0.35, impact 0.30, typing 0.35.
Delivery QC: about -14 LUFS, true peak <= -1.5 dBFS (loudnorm targets TP -3 so AAC overshoot still lands under -1.5).
"""
import json, os, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = json.load(open(os.path.join(ROOT, "alert.json"))); AU = A["audio"]; total = float(A.get("duration", 15))

def ad(f):
    """Resolve a file under assets/audio, trying .wav/.mp3 if the exact name is missing."""
    p = os.path.join(ROOT, "assets/audio", f)
    if os.path.isfile(p):
        return p
    stem, ext = os.path.splitext(p)
    for alt in (".wav", ".mp3", ".m4a", ".flac", ".ogg"):
        q = stem + alt
        if q != p and os.path.isfile(q):
            return q
    return p  # let ffmpeg raise a clear error
inputs = ["-i", ad(AU["bed"])]
# optional "bed_loop": [cut, restart, xfade] -> bed[0:cut] crossfaded into bed[restart:cut] (repeat) so a bed whose own tail
# fades out still holds to the end (keeps the drone up for a clean loop back to the hit)
bl = AU.get("bed_loop")
if bl:   # pre-render the looped bed with separate inputs (asplit+atrim starves branches)
    cut, rs, xf = bl; seg = cut - rs; n = int((total - cut) // (seg - xf)) + 2
    parts = [f"[0:a]atrim=0:{cut},asetpts=PTS-STARTPTS[x0]"]
    for k in range(1, n):
        parts.append(f"[{k}:a]atrim={rs}:{cut},asetpts=PTS-STARTPTS[y{k}];[x{k-1}][y{k}]acrossfade=d={xf}[x{k}]")
    looped = ad("bed_looped.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", *sum([["-i", ad(AU["bed"])] for _ in range(n)], []), "-filter_complex", ";".join(parts),
                    "-map", f"[x{n-1}]", "-ar", "48000", looped], check=True)
    inputs = ["-i", looped]
src = "[0:a]"
bs = float(AU.get("bed_start", 0) or 0)
fl = [f"{src}aresample=48000,aformat=channel_layouts=stereo,atrim={bs}:{bs + total},asetpts=PTS-STARTPTS,volume={AU.get('bed_gain', .4)},"
      f"afade=t=in:st=0:d={AU.get('bed_fade_in', .3)},afade=t=out:st={total - .35}:d=0.35,apad=whole_dur={total}[bed]"]
mix = ["[bed]"]
for i, c in enumerate(AU.get("cues", [])):
    inputs += ["-i", ad(c["file"])]
    trim = f"atrim=0:{c['dur']},afade=t=out:st={max(0, c["dur"] - 0.12)}:d=0.12," if c.get("dur") else ""
    fl.append(f"[{i + 1}:a]aresample=48000,aformat=channel_layouts=stereo,{trim}volume={c.get('gain', .6)},adelay={int(c['t'] * 1000)}:all=1[c{i}]")
    mix.append(f"[c{i}]")
fl.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,atrim=0:{total},alimiter=limit=0.5:attack=3:release=80:level=disabled[pre]")
tmp = ad("mix_pre.wav")
subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fl), "-map", "[pre]", "-ar", "48000", tmp], check=True)
r = subprocess.run(["ffmpeg", "-v", "info", "-i", tmp, "-af", "loudnorm=I=-14:TP=-3:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
j = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
ln = (f"loudnorm=I=-14:TP=-3:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
      f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", ln, "-ar", "48000", "-c:a", "pcm_s16le", ad("mix.wav")], check=True)
os.remove(tmp)
if bl: os.remove(ad("bed_looped.wav"))
print("mix.wav written; pre-norm", j["input_i"], "LUFS")
