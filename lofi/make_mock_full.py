#!/usr/bin/env python3
"""
Sweet Morning Lofi — full mock video.

  - 4 random songs from D:\\Youtube\\Kawaii Lofi\\Rainy Day  (concatenated audio)
  - 30 s base video with effects, LOOPED to cover the full audio duration
  - News ticker is a PERFECT LOOP: empty band at t=0 and t=L (so each repeat
    seamlessly starts with no text on screen).

Effects:
  - Static warm colorbalance
  - Bigger, brighter rain streaks (4-5 px wide, 50 px tall, alpha 0.75)
  - Bigger sparkles via drawtext '*' at fontsize 40 with pulsing alpha
  - Moving light orbs (4 drawbox on sin/cos paths)
  - News chyron — single perfect-loop scroll across the bar
  - Vignette  (noise removed — user didn't like it)

Usage:  python make_mock_full.py
Output: ../output/mock_full.mp4
"""
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT      = Path(__file__).parent.parent
IMAGE     = ROOT / "assets" / "images" / "rainy_20260518_275.jpg"
SONGS_DIR = Path(r"D:\Youtube\Kawaii Lofi\Rainy Day")
OUT_DIR   = ROOT / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_VIDEO  = OUT_DIR / "_base_loop.mp4"
AUDIO_MIX   = OUT_DIR / "_audio_mix.m4a"
CONCAT_TXT  = OUT_DIR / "_audio_concat.txt"
FINAL       = OUT_DIR / "mock_full.mp4"

W, H, FPS = 1920, 1080, 24
L = 30      # loop duration (seconds)


# ── 1. pick 4 random songs ────────────────────────────────────────────────────
def ffprobe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0

all_songs = list(SONGS_DIR.glob("*.mp3"))
if len(all_songs) < 4:
    sys.exit(f"[ERROR] Apenas {len(all_songs)} MP3s em {SONGS_DIR}")

random.seed()                      # reseed each run for variety
picked = random.sample(all_songs, 4)
durations = [ffprobe_duration(s) for s in picked]
total_audio = sum(durations)

print("Músicas selecionadas:")
for s, d in zip(picked, durations):
    print(f"  - {s.name}  ({d/60:.1f} min)")
print(f"Total áudio: {total_audio/60:.1f} min ({total_audio:.0f} s)")

# Round the video duration UP to the next multiple of L so it always
# finishes on a clean loop boundary (last frame = empty band).
loops_needed = int(total_audio // L) + (1 if total_audio % L else 0)
final_duration = loops_needed * L
print(f"Loops de {L}s: {loops_needed}  ->  video final {final_duration}s ({final_duration/60:.1f} min)")


# ── 2. concat the picked songs into a single audio file ──────────────────────
with open(CONCAT_TXT, "w", encoding="utf-8") as f:
    for s in picked:
        safe = str(s).replace("\\", "/").replace("'", "\\'")
        f.write(f"file '{safe}'\n")

print("\n[1/3] Concatenando áudio...")
r = subprocess.run(
    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(CONCAT_TXT),
     "-c:a", "aac", "-b:a", "192k", "-t", str(final_duration),
     str(AUDIO_MIX)],
    capture_output=True, text=True,
)
if r.returncode != 0:
    print("[ERRO áudio]\n" + r.stderr[-1500:], file=sys.stderr)
    sys.exit(1)


# ── 3. base loop video (L seconds, effects, no audio) ────────────────────────
# Rain strips: thicker, taller, more opaque so they read clearly on the window.
# 18 streams spread across the window area (x ~ 220 .. 1720)
RAIN = [
    (220,  175, 590, 5, 60),
    (320,  205, 590, 4, 50),
    (420,  180, 590, 5, 60),
    (510,  220, 590, 4, 50),
    (605,  155, 590, 6, 70),
    (700,  240, 590, 4, 50),
    (790,  195, 590, 5, 60),
    (880,  165, 590, 4, 50),
    (975,  215, 590, 6, 70),
    (1060, 185, 590, 5, 60),
    (1155, 200, 590, 4, 50),
    (1245, 170, 590, 5, 60),
    (1340, 235, 590, 4, 50),
    (1430, 190, 590, 6, 70),
    (1520, 210, 590, 4, 50),
    (1610, 175, 590, 5, 60),
    (1700, 225, 590, 4, 50),
    (1790, 195, 590, 5, 60),
]
rain_filters = [
    f"drawbox=x={xc}:y=mod(t*{spd}\\,{wrap}):w={bw}:h={bh}:color=0xE6F0FF@0.85:t=99"
    for xc, spd, wrap, bw, bh in RAIN
]

# Floating light orbs (still drawbox, semi-transparent yellows)
ORBS = [
    ("960+80*sin(t*0.7)-14",  "190+25*sin(t*1.1)-14", 28, "0xFFE066@0.75"),
    ("1360+45*cos(t*0.9)-11", "310+20*cos(t*0.6)-11", 22, "0xFFCC44@0.70"),
    ("420+55*sin(t*0.5)-12",  "240+30*sin(t*0.8)-12", 24, "0xFFD966@0.72"),
    ("1160+35*sin(t*1.2)-9",  "155+20*cos(t*1.0)-9",  18, "0xFFEE99@0.68"),
]
orb_filters = [
    f"drawbox=x={x}:y={y}:w={sz}:h={sz}:color={col}:t=99"
    for x, y, sz, col in ORBS
]

# Bigger, brighter sparkles. Alpha uses sin*sin so it never goes negative
# (clamps to 0 visually) → sparkles are continuously visible, just pulsing brightness.
# Pure-white color + larger fontsize so they read as obvious points of light.
SPARKLES = [
    ("300+40*sin(t*1.3)",  "120+30*cos(t*0.9)", "0.5+0.5*sin(t*2.1)*sin(t*2.1)",     48),
    ("1540+50*cos(t*0.8)", "200+35*sin(t*1.7)", "0.5+0.5*cos(t*2.5)*cos(t*2.5)",     54),
    ("750+35*sin(t*1.9)",  "80+25*cos(t*1.4)",  "0.5+0.5*sin(t*3.0+1)*sin(t*3.0+1)", 44),
    ("1180+30*cos(t*2.2)", "450+25*sin(t*0.7)", "0.5+0.5*cos(t*1.8+2)*cos(t*1.8+2)", 50),
    ("600+45*sin(t*1.1)",  "320+20*cos(t*1.6)", "0.5+0.5*sin(t*2.8+0.5)*sin(t*2.8+0.5)", 46),
    ("1420+40*cos(t*1.5)", "420+30*sin(t*0.6)", "0.5+0.5*cos(t*2.0+1.5)*cos(t*2.0+1.5)", 48),
    ("900+30*sin(t*1.8)",  "260+20*cos(t*1.1)", "0.5+0.5*sin(t*2.3+0.8)*sin(t*2.3+0.8)", 42),
    ("1700+25*cos(t*1.6)", "350+18*sin(t*1.9)", "0.5+0.5*cos(t*2.7+0.3)*cos(t*2.7+0.3)", 40),
]
sparkle_filters = [
    f"drawtext=text=*:x={x}:y={y}:fontsize={sz}:fontcolor=0xFFFFFF:alpha={a}"
    for x, y, a, sz in SPARKLES
]

# Watermark (static, top-left)
watermark = (
    f"drawtext=text=Sweet Morning Lofi:x=40:y=40:"
    f"fontsize=24:fontcolor=white@0.55"
)

# ── News ticker — perfect loop with margin ─────────────────────────────────────
# Margin M (px) keeps the text fully off-screen at both ends of the loop.
#   x(t) = W + M - (W + tw + 2M) * t / L
# At t=0:  x = W + M       → text starts M px off-screen to the RIGHT  → invisible
# At t=L:  x = -tw - M     → text M px off-screen to the LEFT          → invisible
# Continuous between → smooth right-to-left scroll, empty band at both ends.
M = 30
TICKER = (
    "NOW PLAYING  --  Sweet Morning Lofi  --  Rainy Day Kawaii Mix  "
    "--  Cozy Cafe Session Vol.7  --  Your daily dose of kawaii beats  "
    "--  Sweet Morning Lofi (Est. 2024)  --  Subscribe for weekly cozy mixes "
)
ticker_filters = [
    f"drawbox=x=0:y=940:w={W}:h=100:color=0x080820@0.85:t=99",
    f"drawtext=text={TICKER}:x={W}+{M}-({W}+tw+{2*M})*t/{L}:y=965:"
    f"fontsize=30:fontcolor=white",
]

# ── Build the filtergraph ──────────────────────────────────────────────────────
vf_parts = [
    f"scale={W}:{H}:force_original_aspect_ratio=decrease",
    f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black",
    f"fps={FPS}",
    "colorbalance=rs=0.05:gs=0.02:bs=-0.04",
    *rain_filters,
    *orb_filters,
    *sparkle_filters,
    *ticker_filters,
    watermark,
    "vignette=PI/4.5",
]
vf = ",".join(vf_parts)

print("\n[2/3] Renderizando vídeo base de {} s...".format(L))
r = subprocess.run(
    ["ffmpeg", "-y",
     "-loop", "1", "-framerate", str(FPS), "-i", str(IMAGE),
     "-vf", vf,
     "-t", str(L),
     "-c:v", "libx264", "-preset", "fast", "-crf", "20",
     "-pix_fmt", "yuv420p",
     "-an",
     str(BASE_VIDEO)],
    capture_output=True, text=True,
)
if r.returncode != 0:
    print("[ERRO base video]\n" + r.stderr[-2500:], file=sys.stderr)
    sys.exit(1)


# ── 4. loop the base video + mux with audio ──────────────────────────────────
print("\n[3/3] Loopando vídeo {}x e juntando com áudio...".format(loops_needed))
r = subprocess.run(
    ["ffmpeg", "-y",
     "-stream_loop", "-1", "-i", str(BASE_VIDEO),
     "-i", str(AUDIO_MIX),
     "-map", "0:v:0", "-map", "1:a:0",
     "-c:v", "copy",
     "-c:a", "copy",
     "-t", str(final_duration),
     "-shortest",
     str(FINAL)],
    capture_output=True, text=True,
)
if r.returncode != 0:
    print("[ERRO mux]\n" + r.stderr[-2500:], file=sys.stderr)
    sys.exit(1)

# Cleanup intermediates
for f in (CONCAT_TXT, BASE_VIDEO, AUDIO_MIX):
    f.unlink(missing_ok=True)

print(f"\n[OK] {FINAL}  ({final_duration/60:.1f} min)")
