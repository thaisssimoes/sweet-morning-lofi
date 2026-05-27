#!/usr/bin/env python3
"""
Mock short story video — "O Pintinho e a Minhoca"

A 7-scene cute/comedy story:
  - Generates 7 consistent illustrations via Pollinations.ai (flux model)
  - Generates Portuguese narration via edge-tts (Thalita voice)
  - Renders each scene with alternating Ken Burns zoom
  - Concatenates into a vertical short video (1080x1920)

Style consistency strategy:
  - Every prompt uses the SAME style + character description prefix
  - Seeds are BASE_SEED + scene_idx (small offset for variation, not chaos)
  - Single character (yellow chick), single setting (green garden)

Usage:  python make_short_story.py
Output: ../output/story_pintinho.mp4
"""
import random
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT       = Path(__file__).parent.parent
WORK_DIR   = ROOT / "output" / "short_story"
WORK_DIR.mkdir(parents=True, exist_ok=True)
FINAL      = ROOT / "output" / "story_pintinho.mp4"

W, H, FPS  = 1080, 1920, 30      # vertical (YouTube Shorts ratio)
VOICE      = "pt-BR-ThalitaNeural"
TTS_RATE   = "-5%"               # slightly slower → warm storytelling pace
BASE_SEED  = 4242

# ── Style + character shared in every prompt for consistency ──────────────────
# Kept short — Pollinations 500s on very long URLs sometimes.
STYLE_PREFIX = "cute watercolor children book illustration, kawaii, pastel colors"
CHARACTER    = "tiny round yellow baby chick with big black eyes"
SETTING      = "green grass garden, soft daylight"

# ── The 7 scenes: (image prompt fragment, narration text) ─────────────────────
# Prompts kept short — Pollinations works better with focused descriptions
SCENES = [
    (
        "chick walking happy in garden",
        "Era uma vez um pequeno pintinho... que passeava feliz pelo jardim.",
    ),
    (
        "chick with surprised sparkly eyes spotting a small pink worm in the dirt",
        "Foi quando, de repente, ele viu... uma minhoca!",
    ),
    (
        "chick jumping high in the air trying to catch a pink worm, action scene",
        "Animado, deu um pulo cheio de coragem, pronto pra pegar o lanchinho.",
    ),
    (
        "confused chick looking at an empty hole in the ground, head tilted",
        "Mas num piscar de olhos... a minhoca escapou pelo buraco.",
    ),
    (
        "determined chick digging with tiny feet, dirt flying around",
        "O pintinho nao desistiu. Comecou a cavar... e cavar...",
    ),
    (
        "chick covered in brown mud and dirt inside a small hole, exhausted",
        "E cavou tanto, tanto, que ficou todinho sujo de terra.",
    ),
    (
        "surprised chick looking up with mouth open, a small pink worm sits smiling on top of the chick's head",
        "Foi entao que percebeu... a minhoquinha tava ali, na cabeca dele, o tempo todo!",
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. Image generation via Pollinations.ai (curl — Go net/http gets 402)
# ─────────────────────────────────────────────────────────────────────────────
def generate_image(idx: int, scene_prompt: str, out_path: Path) -> None:
    """
    Pollinations free tier is extremely flaky — bursts trigger 402/500 for
    minutes. Patient strategy:
      - Each attempt uses a fresh random seed
      - On 402 (quota): sleep 60-90s (rate limit clears after ~2 min)
      - On 500/other: sleep 30-45s (server-side hiccup)
      - flux fallback to turbo (separate quota pool)
      - 6 patient attempts per model = up to ~8 min per image worst case
    """
    full = f"{STYLE_PREFIX}. {CHARACTER}, {SETTING}. {scene_prompt}"
    encoded = urllib.parse.quote(full)
    print(f"  [{idx+1}/7] {out_path.name}")

    for model in ("flux", "turbo"):
        for attempt in range(6):
            seed = random.randint(1, 1_000_000)
            url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width={W}&height={H}&model={model}&seed={seed}&nologo=true"
            )
            # NOTE: Pollinations returns 500 for "Mozilla/*" UAs (anti-bot rule).
            # Default curl UA passes. Don't pass -A.
            r = subprocess.run(
                ["curl", "-sS", "--max-time", "180",
                 "-o", str(out_path),
                 "-w", "%{http_code}",
                 url],
                capture_output=True, text=True,
            )
            status = (r.stdout or "").strip()
            if status == "200" and out_path.exists() and out_path.stat().st_size >= 2048:
                print(f"      ok ({model}, try {attempt+1}, seed={seed})")
                return
            out_path.unlink(missing_ok=True)
            wait = 75 if status == "402" else 35
            print(f"      try {attempt+1}/6 ({model}, seed={seed}): HTTP {status}  sleep {wait}s")
            time.sleep(wait)
        print(f"      -> fallback to next model")

    sys.exit(f"[ERRO image {idx+1}] Pollinations falhou em todos os modelos")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Narration via edge-tts (Portuguese, Thalita voice)
# ─────────────────────────────────────────────────────────────────────────────
def generate_narration(idx: int, text: str, out_path: Path) -> None:
    print(f"  [{idx+1}/7] {out_path.name}")
    r = subprocess.run(
        ["edge-tts", "--voice", VOICE, f"--rate={TTS_RATE}",
         "--text", text, "--write-media", str(out_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not out_path.exists():
        sys.exit(f"[ERRO tts {idx+1}]\n{r.stderr[-500:]}")


def audio_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or 0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Render one scene clip — Ken Burns zoom (in / out alternating)
# ─────────────────────────────────────────────────────────────────────────────
def render_scene(idx: int, image: Path, audio: Path, out_path: Path) -> None:
    dur = audio_duration(audio) + 0.6      # small tail after narration ends
    frames = int(dur * FPS)
    # scale+crop Ken Burns — smoother than zoompan (no integer pixel rounding jitter)
    # scale image to W*zoom x H*zoom per frame, then center-crop to W x H
    if idx % 2 == 0:
        zoom_expr = f"1+0.18*n/{frames}"        # zoom in  1.0 → 1.18
    else:
        zoom_expr = f"1.18-0.18*n/{frames}"     # zoom out 1.18 → 1.0

    # trunc(..../2)*2 ensures even dimensions required by yuv420p
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"scale=w='trunc({W}*({zoom_expr})/2)*2':h='trunc({H}*({zoom_expr})/2)*2':eval=frame,"
        f"crop={W}:{H},"
        f"setpts=PTS-STARTPTS"
    )

    print(f"  [{idx+1}/7] {out_path.name}  ({dur:.1f}s)")
    r = subprocess.run(
        ["ffmpeg", "-y",
         "-loop", "1", "-framerate", str(FPS), "-i", str(image),
         "-i", str(audio),
         "-vf", vf,
         "-c:v", "libx264", "-preset", "fast", "-crf", "20",
         "-c:a", "aac", "-b:a", "192k",
         "-pix_fmt", "yuv420p",
         "-t", str(dur), "-shortest",
         str(out_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.exit(f"[ERRO render {idx+1}]\n{r.stderr[-800:]}")


def concat_clips(clips: list[Path], out_path: Path) -> None:
    txt = WORK_DIR / "_concat.txt"
    with open(txt, "w", encoding="utf-8") as f:
        for p in clips:
            safe = str(p).replace("\\", "/").replace("'", "\\'")
            f.write(f"file '{safe}'\n")
    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(txt),
         "-c", "copy", str(out_path)],
        capture_output=True, text=True,
    )
    txt.unlink(missing_ok=True)
    if r.returncode != 0:
        sys.exit(f"[ERRO concat]\n{r.stderr[-800:]}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    print("== O PINTINHO E A MINHOCA ==\n")
    print("ROTEIRO:")
    for i, (_, line) in enumerate(SCENES, 1):
        print(f"  {i}. {line}")
    print()

    print("[1/4] Gerando imagens (Pollinations.ai flux)...")
    images = []
    for i, (prompt, _) in enumerate(SCENES):
        p = WORK_DIR / f"scene_{i+1:02d}.jpg"
        if p.exists() and p.stat().st_size > 2048:
            print(f"  [{i+1}/7] {p.name}  (cached)")
        else:
            generate_image(i, prompt, p)
            # space requests out to stay under the anonymous-tier rate limit
            if i < len(SCENES) - 1:
                time.sleep(8)
        images.append(p)

    print("\n[2/4] Gerando narracao (edge-tts)...")
    audios = []
    for i, (_, text) in enumerate(SCENES):
        a = WORK_DIR / f"scene_{i+1:02d}.mp3"
        if a.exists():
            print(f"  [{i+1}/7] {a.name}  (cached)")
        else:
            generate_narration(i, text, a)
        audios.append(a)

    print("\n[3/4] Renderizando cenas (Ken Burns)...")
    clips = []
    for i, (img, aud) in enumerate(zip(images, audios)):
        c = WORK_DIR / f"clip_{i+1:02d}.mp4"
        render_scene(i, img, aud, c)
        clips.append(c)

    print("\n[4/4] Juntando cenas...")
    concat_clips(clips, FINAL)

    total = sum(audio_duration(a) + 0.6 for a in audios)
    print(f"\n[OK] {FINAL}  (~{total:.1f}s)")


if __name__ == "__main__":
    main()
