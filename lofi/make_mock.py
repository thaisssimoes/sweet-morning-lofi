#!/usr/bin/env python3
"""
Mock video — Sweet Morning Lofi visual effects demo.

All dynamic effects via drawbox + drawtext (no geq):
  - Warm colorbalance (static tint on base image)
  - Animated rain strips   → 6 thin drawbox moving downward via (t*speed)%wrap
  - Floating light orbs    → 4 drawbox on sin/cos paths
  - Blinking sparkles      → drawtext '*' with oscillating alpha
  - News chyron ticker     → scrolling drawtext at bottom
  - Breaking-news bands    → two crossfading drawtext lines above ticker
  - Grain + vignette

Usage:  python make_mock.py
Output: ../output/mock_effects.mp4
"""
import subprocess
import sys
from pathlib import Path

ROOT   = Path(__file__).parent.parent
IMAGE  = ROOT / "assets" / "images" / "rainy_20260518_275.jpg"
OUTPUT = ROOT / "output" / "mock_effects.mp4"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

W, H, FPS, DUR = 1920, 1080, 24, 30
FONT = "font=Arial"   # name-based font lookup — no path, no colon issues

# ── Rain strips ────────────────────────────────────────────────────────────────
# (x_center, speed_px_per_sec, wrap_px, strip_width, strip_height)
RAIN = [
    (285,  175, 570, 3, 22),
    (620,  220, 570, 2, 18),
    (895,  158, 570, 3, 22),
    (1105, 238, 570, 2, 18),
    (1375, 193, 570, 3, 22),
    (1640, 207, 570, 2, 18),
]

# drawbox doesn't support % operator → use mod(a\,b). Python \\, → string \, →
# FFmpeg level-2 unescapes to , for the expression evaluator (mod takes 2 args).
rain_filters = [
    f"drawbox=x={xc}:y=mod(t*{spd}\\,{wrap}):w={bw}:h={bh}:color=0xCCEEFF@0.35:t=99"
    for xc, spd, wrap, bw, bh in RAIN
]

# ── Floating light orbs (drawbox squares on sin/cos paths) ─────────────────────
# (x_expr, y_expr, size, color@alpha)
ORBS = [
    ("960+80*sin(t*0.7)-12",  "190+25*sin(t*1.1)-12", 24, "0xFFE066@0.70"),
    ("1360+45*cos(t*0.9)-9",  "310+20*cos(t*0.6)-9",  18, "0xFFCC44@0.60"),
    ("420+55*sin(t*0.5)-10",  "240+30*sin(t*0.8)-10", 20, "0xFFD966@0.65"),
    ("1160+35*sin(t*1.2)-7",  "155+20*cos(t*1.0)-7",  14, "0xFFEE99@0.55"),
]

orb_filters = [
    f"drawbox=x='{x}':y='{y}':w={sz}:h={sz}:color={col}:t=99"
    for x, y, sz, col in ORBS
]

# ── Blinking sparkles (drawtext with alpha expression) ─────────────────────────
SPARKLES = [
    ("300+30*sin(t*1.3)",  "120+20*cos(t*0.9)", "0.5+0.5*sin(t*2.1)"),
    ("1540+40*cos(t*0.8)", "200+25*sin(t*1.7)", "0.5+0.5*cos(t*2.5)"),
    ("750+25*sin(t*1.9)",  "80+15*cos(t*1.4)",  "0.5+0.5*sin(t*3.0+1)"),
    ("1180+20*cos(t*2.2)", "450+18*sin(t*0.7)", "0.5+0.5*cos(t*1.8+2)"),
]

sparkle_filters = [
    f"drawtext=text='*':{FONT}:x='{x}':y='{y}':fontsize=22:fontcolor=0xFFFF88:alpha='{a}'"
    for x, y, a in SPARKLES
]

# ── News chyron: bottom ticker scrolling right→left ────────────────────────────
# No ':' in text — FFmpeg drawtext parser splits on ':' even inside single quotes
# in some chains; we use ' -- ' as separator instead.
TICKER = (
    "NOW PLAYING  --  Sweet Morning Lofi  --  Rainy Day Kawaii Mix  "
    "--  Cozy Cafe Session Vol.7  --  Your daily dose of kawaii beats  "
    "--  Sweet Morning Lofi  Est. 2024  --  Subscribe for weekly cozy mixes  "
)

ticker_filters = [
    # Dark background bar
    f"drawbox=x=0:y=940:w={W}:h=100:color=0x060618@0.88:t=99",
    # Scrolling text (starts at right edge, moves left at 65 px/s)
    f"drawtext=text='{TICKER}':{FONT}:x={W}-t*65:y=962:fontsize=26:fontcolor=white",
]

# ── Breaking-news bands: two lines above ticker that crossfade every ~12s ─────
BAND_Y = 855
BAND_H = 80

# alpha oscillates between 0 and 1 on opposite phases (no ':' or '&' in text)
LINE_A = "Sweet Morning Lofi  --  Now Playing  --  Rainy Day Kawaii Mix Vol.7"
LINE_B = "Sweet Morning Lofi  --  Cozy Cafe Lofi Beats  --  Study and Chill Session"

news_band_filters = [
    # Background band
    f"drawbox=x=0:y={BAND_Y}:w={W}:h={BAND_H}:color=0x0A0A30@0.80:t=99",
    # Accent bar (thin blue line on left)
    f"drawbox=x=0:y={BAND_Y}:w=6:h={BAND_H}:color=0x4488FF@0.95:t=99",
    # Line A: fades in/out with sin^2 over ~12s cycle, starts visible
    f"drawtext=text='{LINE_A}':{FONT}:x=24:y={BAND_Y+22}:fontsize=30:fontcolor=white:alpha='sin(t*3.14159/12)*sin(t*3.14159/12)'",
    # Line B: fades on opposite phase (cos^2)
    f"drawtext=text='{LINE_B}':{FONT}:x=24:y={BAND_Y+22}:fontsize=30:fontcolor=0xCCDDFF:alpha='cos(t*3.14159/12)*cos(t*3.14159/12)'",
]

# ── Channel watermark ──────────────────────────────────────────────────────────
watermark = f"drawtext=text='Sweet Morning Lofi':{FONT}:x=40:y=40:fontsize=22:fontcolor=white@0.5"

# ── Full filter chain ──────────────────────────────────────────────────────────
vf = ",".join([
    f"scale={W}:{H}:force_original_aspect_ratio=decrease",
    f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black",
    f"fps={FPS}",
    "colorbalance=rs=0.05:gs=0.02:bs=-0.04",   # static warm amber tint
    *rain_filters,
    *orb_filters,
    *sparkle_filters,
    *news_band_filters,
    *ticker_filters,
    watermark,
    "noise=alls=8:allf=t",
    "vignette=PI/4.5",
])

cmd = [
    "ffmpeg", "-y",
    "-loop", "1", "-framerate", str(FPS), "-i", str(IMAGE),
    "-vf", vf,
    "-t", str(DUR),
    "-c:v", "libx264", "-preset", "fast", "-crf", "20",
    "-pix_fmt", "yuv420p",
    str(OUTPUT),
]

print(f"Gerando mock {DUR}s @ {FPS}fps...")
print(f"  Imagem : {IMAGE.name}")
print(f"  Output : {OUTPUT}")

result = subprocess.run(cmd, text=True, capture_output=True)
if result.returncode != 0:
    print("[ERRO ffmpeg]\n" + result.stderr[-3000:], file=sys.stderr)
    sys.exit(1)

print(f"\n[OK] Pronto! {OUTPUT}")
