#!/usr/bin/env python3
"""
Sweet Morning Lofi — Video Generator + YouTube Uploader

Usage:
    python generate_videos.py                              # 7 vídeos a partir de hoje
    python generate_videos.py -n 3                         # 3 vídeos
    python generate_videos.py -b 25-05-2026                # 7 vídeos a partir dessa data
    python generate_videos.py -n 3 -b 25-05-2026           # 3 vídeos a partir dessa data
    python generate_videos.py -c                           # continua do dia seguinte ao último vídeo gerado
    python generate_videos.py -c -n 3                      # idem, gerando 3 vídeos
    python generate_videos.py --upload-from 20-05-2026     # sobe vídeos já gerados
    python generate_videos.py --upload-from 20-05-2026 --upload-to 27-05-2026
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error

# ── Configuração ───────────────────────────────────────────────────────────────
BASE_DIR      = Path(r"D:\Youtube\Kawaii Lofi")
SUNNY_DIR     = BASE_DIR / "Kawaii Lofi"
RAINY_DIR     = BASE_DIR / "Rainy Day"
IMAGES_DIR    = BASE_DIR / "images"
OUTPUT_DIR    = BASE_DIR / "output"

LATITUDE      = 35.6762
LONGITUDE     = 139.6503
TIMEZONE      = "Asia/Tokyo"

TARGET_MIN    = 50 * 60
TARGET_MAX    = 120 * 60
VIDEO_W       = 1920
VIDEO_H       = 1080

PUBLISH_HOUR_UTC     = 8      # hora de publicação em UTC
YOUTUBE_CATEGORY     = "10"  # Music
YOUTUBE_PLAYLIST_ID  = "PLNw88sQP95NPB5RIsrahTN70V-Sr7SaKZ"
# ───────────────────────────────────────────────────────────────────────────────

RAINY_CODES = {
    3, 45, 48,
    51, 53, 55, 56, 57,
    61, 63, 65, 66, 67,
    71, 73, 75, 77,
    80, 81, 82, 85, 86,
    95, 96, 99,
}

# ── Metadata templates ─────────────────────────────────────────────────────────

_SEASON_DATA = {
    "summer": ("Summer", "🌴"),
    "autumn": ("Autumn", "🍂"),
    "winter": ("Winter", "❄️"),
    "spring": ("Spring", "🌸"),
}

_RAINY_TITLES = [
    "🌧️ Rainy {season} Kawaii Lofi | Cozy Beats to Relax, Study & Unwind",
    "☔ Soft Rain Kawaii Lofi | Gentle Beats for a Slow Rainy {weekday}",
    "☕🌧️ Kawaii Rainy Day Lofi | Calm Beats for Cloudy {season} Days",
    "🌧️{semoji} Cozy Rain Kawaii Lofi | Soft Beats to Rest, Read & Unwind",
    "🌂 Rainy {season} Kawaii Beats | Lo-Fi Music to Slow Down & Breathe",
    "🌧️{semoji} Kawaii Lofi for Rainy Days | Beats to Study, Rest & Dream",
]

_SUNNY_TITLES = [
    "☀️ Sunny {season} Kawaii Lofi | Warm Beats for a Bright & Easy Day",
    "☀️{semoji} Kawaii Morning Lofi | Cheerful Beats for a Good {weekday}",
    "🌸 Kawaii Sunny Day Lofi | Soft Uplifting Beats for {season} Mornings",
    "✨ Feel-Good Kawaii Lofi | Warm Beats to Brighten Your {season} Day",
    "☀️ Kawaii Sunny Day Beats | Cozy Lo-Fi Music for Any Good Day",
    "☀️{semoji} Sunny Kawaii Lofi | Beats to Focus, Create & Smile",
]

_RAINY_HOOKS = [
    "1 hour of soft rainy-day kawaii lofi to help you slow down, breathe, and just exist.",
    "Rain on the window, tea in hand, lofi in your ears — this mix was made for days like this.",
    "Wrap yourself in these gentle kawaii beats and let a rainy {season} afternoon carry you away.",
    "Sometimes the best thing to do on a rainy day is nothing at all — let this lofi mix keep you company.",
    "Soft beats, grey skies, and all the coziness you need to get through a rainy {weekday}.",
    "There's a kind of magic that only happens on rainy days — this kawaii lofi mix was made to live inside it.",
]

_SUNNY_HOOKS = [
    "1 hour of warm, sunny kawaii lofi to brighten your day and keep you gently focused.",
    "Some days just call for good vibes and soft beats — this sunny lofi mix has you covered.",
    "Start your {weekday} with the warmest kawaii lofi vibes — gentle, uplifting, and built to last.",
    "Let these bright kawaii beats turn any ordinary {season} day into something a little more magical.",
    "Sunny days are even better with lofi — warm beats, good energy, and all the coziness you need.",
    "Open the window, feel the {season} sun, and let this kawaii lofi mix set the mood for the whole day.",
]

_RAINY_MOODS = [
    "This mix blends soft kawaii lofi beats with the calming mood of a rainy {season} day. No rush, no noise — just gentle rhythms to help you reset and breathe.",
    "There's something magical about rain and lofi together. These tracks were crafted to match that slow, introspective mood — perfect for quiet {season} afternoons.",
    "Heavy rain, light beats. This kawaii lofi journey was designed to turn any stormy {weekday} into a calm, cozy retreat from the world.",
    "Grey skies outside, warm beats inside. This mix was built for those beautiful rainy {season} days when all you want to do is slow down and feel something soft.",
]

_SUNNY_MOODS = [
    "This mix brings together the warmest kawaii lofi sounds and the easy, uplifting energy of a sunny {season} day — perfect for staying in a good mood from morning to night.",
    "Bright skies, soft beats. These kawaii lofi tracks were crafted to match the gentle optimism of a beautiful {season} day — no rush, just pure good vibes.",
    "Sun is out, beats are soft. This kawaii lofi journey keeps the energy light, warm, and consistently feel-good from the very first note to the last.",
    "There's a special kind of peace in a sunny {season} {weekday}. This mix was made to stretch that feeling out for a full hour of warm, effortless lofi.",
]

_RAINY_USE_CASES = [
    "Studying or reading on a rainy afternoon",
    "Falling asleep to soft beats and the sound of rain",
    "Working from home on a grey, cloudy day",
    "Journaling, sketching, or quietly zoning out",
    "Unwinding after a long, exhausting week",
    "Cozy self-care moments — tea, blankets, slow evenings",
    "Background music for a rainy home-office vibe",
    "Doing nothing at all and being totally okay with it",
    "A slow morning when you don't want to rush into the day",
    "Late-night creative sessions with the rain as company",
]

_SUNNY_USE_CASES = [
    "A productive morning before the world wakes up",
    "Studying or working with a positive, focused mindset",
    "Weekend morning rituals — coffee, journaling, slow walks",
    "Lifting your mood on any ordinary weekday",
    "Background music for a cheerful, creative afternoon",
    "Light exercise, yoga, or a quiet stretch session",
    "A long, relaxed lunch break in the sun",
    "Winding down a beautiful day with gentle, warm beats",
    "Getting things done without losing your chill",
    "Afternoon art, reading, or just watching the light change",
]

_RAINY_HASHTAGS = [
    "#lofi", "#rainylofi", "#kawailofi", "#relaxingmusic", "#cozyvibes",
    "#rainmusic", "#studymusic", "#sleepmusic", "#chillbeats", "#lofihiphop",
    "#rainyambience", "#kawaiiaesthetic", "#softbeats", "#rainyplaylist", "#lofimix",
    "#cozymusic", "#rainyday", "#lofibeats", "#calmmusic", "#rainyvibes",
]

_SUNNY_HASHTAGS = [
    "#lofi", "#kawailofi", "#sunnylofi", "#morninglofi", "#happylofi",
    "#relaxingmusic", "#feelgoodmusic", "#cozymorning", "#chillbeats", "#lofihiphop",
    "#positivevibes", "#studymusic", "#kawaiiaesthetic", "#sunnyplaylist", "#lofimix",
    "#brightday", "#morningvibes", "#lofibeats", "#upliftingmusic", "#cozylofi",
]

_FIXED_TAGS = (
    "creative lofi,cute relaxing music,cozy morning playlist,gentle motivation,"
    "happy morning routine,kawaii chill playlist,positive mood music,comfy background music"
)

_RAINY_TAGS = (
    f"{_FIXED_TAGS},"
    "lofi,kawaii lofi,rainy day lofi,rain lofi,cozy rain music,relaxing music,"
    "lofi hip hop,chill beats,sleep music,study music,lofi music for rainy days,"
    "soft beats,lofi playlist,calm music,kawaii aesthetic music,rain ambience lofi,"
    "unwind music,lo-fi,cozy lofi,background music"
)

_SUNNY_TAGS = (
    f"{_FIXED_TAGS},"
    "lofi,kawaii lofi,sunny lofi,morning lofi,feel good lofi,relaxing music,"
    "lofi hip hop,chill beats,study music,focus music,lofi music for sunny days,"
    "cheerful lofi,warm beats,lofi playlist,kawaii aesthetic music,uplifting lofi,"
    "positive vibes music,lo-fi,cozy lofi,background music"
)

OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_URL   = "http://localhost:11434/api/chat"

# ── .env ───────────────────────────────────────────────────────────────────────

def load_env() -> dict:
    env = {}
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip()
    return env

# ── Weather ────────────────────────────────────────────────────────────────────

def fetch_forecast(days: int) -> tuple[list[int], list[str]]:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LATITUDE}&longitude={LONGITUDE}"
        f"&daily=weathercode&timezone={TIMEZONE}"
        f"&forecast_days={days}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        return data["daily"]["weathercode"], data["daily"]["time"]
    except urllib.error.URLError as exc:
        print(f"[WARN] Weather API unreachable: {exc}. Defaulting to sunny.", file=sys.stderr)
        today = date.today()
        return [0] * days, [(today + timedelta(days=i)).isoformat() for i in range(days)]

# ── Audio / Video ──────────────────────────────────────────────────────────────

def mp3_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def pick_songs(songs_dir: Path, target: int) -> tuple[list[Path], float]:
    pool = list(songs_dir.glob("*.mp3"))
    if not pool:
        sys.exit(f"[ERROR] No MP3 files found in {songs_dir}")

    random.shuffle(pool)
    selected: list[Path] = []
    total = 0.0

    for song in pool:
        if total >= target:
            break
        dur = mp3_duration(song)
        if dur > 0:
            selected.append(song)
            total += dur

    if total < target:
        random.shuffle(pool)
        for song in pool:
            if total >= target:
                break
            dur = mp3_duration(song)
            if dur > 0:
                selected.append(song)
                total += dur

    return selected, total


def pick_image(rainy: bool) -> Path:
    prefix = "rainy day" if rainy else "sunny day"
    candidates = [f for f in IMAGES_DIR.iterdir() if f.name.lower().startswith(prefix)]
    if not candidates:
        sys.exit(f"[ERROR] No images with prefix '{prefix}' in {IMAGES_DIR}")
    return random.choice(candidates)


def make_video(songs: list[Path], image: Path, out_file: Path, duration: float) -> None:
    concat_txt = out_file.parent / "_concat.txt"
    audio_tmp  = out_file.parent / "_audio.aac"

    with open(concat_txt, "w", encoding="utf-8") as fh:
        for s in songs:
            safe = str(s).replace("\\", "/").replace("'", "\\'")
            fh.write(f"file '{safe}'\n")

    cmd1 = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-vn",
        "-af", "asetpts=PTS-STARTPTS",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(int(duration)),
        str(audio_tmp),
    ]

    vf = (
        f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2:color=black"
    )
    cmd2 = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "25", "-i", str(image),
        "-i", str(audio_tmp),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-tune", "stillimage",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        "-r", "1",
        "-vf", vf,
        "-shortest",
        str(out_file),
    ]

    print("  [1/2] Encoding audio...")
    r1 = subprocess.run(cmd1, capture_output=True, text=True)
    concat_txt.unlink(missing_ok=True)
    if r1.returncode != 0:
        audio_tmp.unlink(missing_ok=True)
        print(f"[ERROR] Pass 1 failed:\n{r1.stderr[-3000:]}", file=sys.stderr)
        sys.exit(1)

    print("  [2/2] Encoding video...")
    r2 = subprocess.run(cmd2, capture_output=True, text=True)
    audio_tmp.unlink(missing_ok=True)
    if r2.returncode != 0:
        print(f"[ERROR] Pass 2 failed:\n{r2.stderr[-3000:]}", file=sys.stderr)
        sys.exit(1)

# ── Metadata / Ollama ──────────────────────────────────────────────────────────

def _fmt_hours(secs: float) -> str:
    h = round(secs / 1800) / 2
    return f"~{int(h)}h" if h == int(h) else f"~{h}h"


def _get_season(d: date) -> str:
    m = d.month
    if m in (12, 1, 2): return "summer"
    if m in (3, 4, 5):  return "autumn"
    if m in (6, 7, 8):  return "winter"
    return "spring"


def _ollama_metadata(weekday, day_str, season, mood_word, dur_label, dur_hours) -> dict | None:
    system = (
        "You are a YouTube SEO specialist for kawaii lofi music. "
        "You write creative, natural, keyword-rich metadata that feels human — not robotic. "
        "For titles, ALWAYS use | as separator (never ~). "
        "Title pattern: [emoji] [Keyword with Kawaii + weather] | [Activity in English]. "
        "Respond ONLY with a valid JSON object, no markdown, no extra text."
    )
    description_format = (
        "The description must follow this EXACT structure (use real newlines, not \\\\n):\\n"
        "1. One hook sentence — keyword-rich, under 150 chars (shown in search preview)\\n"
        "2. Blank line\\n"
        "3. Two or three sentences describing the mood and vibe\\n"
        "4. Blank line\\n"
        "5. '✨ Perfect for:' followed by 4 bullet lines starting with •\\n"
        "6. Blank line\\n"
        "7. '🎵 This is a continuous ~1 hour mix crafted to keep the vibe consistent from the first beat to the last.'\\n"
        "8. Blank line\\n"
        "9. '🔔 Subscribe & hit the bell — new mixes drop every week!'\\n"
        "10. Blank line\\n"
        "11. '──────────────────────────────────────'\\n"
        "12. 'Sweet Morning Lofi 🌸 — your daily dose of cozy kawaii beats'\\n"
        "13. '──────────────────────────────────────'\\n"
        "14. Blank line\\n"
        "15. Exactly 5 hashtags on one line (e.g. #lofi #kawailofi #rainylofi #cozyvibes #studymusic)"
    )
    user = (
        f"Generate YouTube metadata for this video:\\n"
        f"- Channel: Sweet Morning Lofi\\n"
        f"- Date: {weekday}, {day_str}\\n"
        f"- Weather: {mood_word.title()}\\n"
        f"- Season: {season} (Tokyo, Japan)\\n"
        f"- Content: {dur_label} continuous kawaii lofi music mix\\n\\n"
        f"Return a JSON object with these keys:\\n"
        f'  "title"  : YouTube title following this EXACT pattern: [emoji] [Keyword] | [Activity in English]. '
        f'Rules: start with emoji; include "Kawaii" + weather context (Sunny/Rainy/Rain); '
        f'use | as separator (NOT ~); after | write the use case in English (study, relax, work, read, focus, unwind). '
        f'Max 70 chars. Good examples: '
        f'"🌧️ Rainy Day Kawaii Beats | Cozy Lo-Fi Music to Study & Relax" '
        f'"☀️ Sunny Kawaii Lofi | Warm Beats to Focus, Create & Feel Good". '
        f'You may include the duration "{dur_hours}" naturally if it fits.\\n'
        f'  "description" : full description — {description_format}\\n'
        f'  "tags"   : list of 15-20 long-tail tags for the YouTube tags field'
    )
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "stream": False,
        "format": "json",
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        return json.loads(data["message"]["content"])
    except Exception as exc:
        print(f"[WARN] Ollama unavailable ({exc}). Falling back to templates.", file=sys.stderr)
        return None


def _metadata_from_templates(day_str, rainy, season_name, season_emoji, weekday):
    def fmt(s): return s.format(season=season_name, semoji=season_emoji, weekday=weekday)
    title    = fmt(random.choice(_RAINY_TITLES    if rainy else _SUNNY_TITLES))
    hook     = fmt(random.choice(_RAINY_HOOKS     if rainy else _SUNNY_HOOKS))
    mood     = fmt(random.choice(_RAINY_MOODS     if rainy else _SUNNY_MOODS))
    cases    = random.sample(_RAINY_USE_CASES if rainy else _SUNNY_USE_CASES, 4)
    hashtags = " ".join(random.sample(_RAINY_HASHTAGS if rainy else _SUNNY_HASHTAGS, 5))
    tags_str = _RAINY_TAGS if rainy else _SUNNY_TAGS
    bullets  = "\n".join(f"• {c}" for c in cases)
    description = (
        f"{hook}\n\n{mood}\n\n"
        f"✨ Perfect for:\n{bullets}\n\n"
        f"🎵 This is a continuous mix crafted to keep the vibe consistent from the first beat to the last.\n\n"
        f"🔔 Subscribe & hit the bell — new mixes drop every week!\n\n"
        f"{'─' * 38}\nSweet Morning Lofi 🌸 — your daily dose of cozy kawaii beats\n{'─' * 38}\n\n"
        f"{hashtags}"
    )
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    return title, description, tags


def make_metadata(day_str: str, rainy: bool, duration_secs: float = 3600) -> dict:
    d                         = date.fromisoformat(day_str)
    season_key                = _get_season(d)
    season_name, season_emoji = _SEASON_DATA[season_key]
    weekday                   = d.strftime("%A")
    mood_word                 = "rainy" if rainy else "sunny"
    source                    = "llama3.1:8b"
    dur_min                   = round(duration_secs / 60)
    dur_label                 = f"{dur_min} min"
    dur_hours                 = _fmt_hours(duration_secs)

    print(f"  Generating metadata via Ollama ({OLLAMA_MODEL})...")
    llm = _ollama_metadata(weekday, day_str, season_name, mood_word, dur_label, dur_hours)

    if llm and all(k in llm for k in ("title", "description", "tags")):
        title, description, tags_raw = llm["title"], llm["description"], llm["tags"]
    else:
        source = "templates"
        title, description, tags_raw = _metadata_from_templates(
            day_str, rainy, season_name, season_emoji, weekday
        )

    tags = tags_raw if isinstance(tags_raw, list) else [t.strip() for t in str(tags_raw).split(",") if t.strip()]

    print(f"  Metadata source: {source}")
    return {
        "date":             day_str,
        "weekday":          weekday,
        "mood":             mood_word,
        "season":           season_name,
        "duration_seconds": round(duration_secs),
        "duration_label":   dur_label,
        "source":           source,
        "title":            title,
        "description":      description,
        "tags":             tags,
    }

# ── YouTube upload ─────────────────────────────────────────────────────────────

def _build_youtube_client(env: dict):
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        print("[ERROR] Instale as dependências do YouTube:", file=sys.stderr)
        print("  pip install google-api-python-client google-auth google-auth-httplib2", file=sys.stderr)
        sys.exit(1)

    client_id     = env.get("YOUTUBE_CLIENT_ID", "")
    client_secret = env.get("YOUTUBE_CLIENT_SECRET", "")
    refresh_token = env.get("YOUTUBE_REFRESH_TOKEN", "")

    if not all([client_id, client_secret, refresh_token]):
        return None

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds)

    return youtube


def _add_to_playlist(youtube, video_id: str) -> None:
    body = {
        "snippet": {
            "playlistId": YOUTUBE_PLAYLIST_ID,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    try:
        youtube.playlistItems().insert(part="snippet", body=body).execute()
        print(f"  ✅ Adicionado à playlist")
    except Exception as exc:
        print(f"  [WARN] Não foi possível adicionar à playlist: {exc}", file=sys.stderr)


def upload_to_youtube(youtube, video_path: Path, metadata: dict, day_str: str) -> str:
    from googleapiclient.http import MediaFileUpload
    y, m, d    = [int(x) for x in day_str.split("-")]
    publish_dt = datetime(y, m, d, PUBLISH_HOUR_UTC, 0, 0, tzinfo=timezone.utc)
    now_utc    = datetime.now(timezone.utc)

    if publish_dt > now_utc:
        status = {"privacyStatus": "private", "publishAt": publish_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")}
        schedule_msg = f"agendado para {publish_dt.strftime('%d/%m/%Y %H:%M')} UTC"
    else:
        status = {"privacyStatus": "public"}
        schedule_msg = "publicado imediatamente (data já passou)"

    body = {
        "snippet": {
            "title":       metadata["title"],
            "description": metadata["description"],
            "tags":        metadata["tags"],
            "categoryId":  YOUTUBE_CATEGORY,
        },
        "status": status,
    }

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=50 * 1024 * 1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        prog, response = request.next_chunk()
        if prog:
            print(f"  Upload: {int(prog.progress() * 100)}%...", end="\r")

    video_id = response["id"]
    print(f"  ✅ https://youtu.be/{video_id} — {schedule_msg}")
    return video_id

# ── Helpers ────────────────────────────────────────────────────────────────────

def _next_suffix(out_dir: Path, day: str) -> str:
    if not (out_dir / f"lofi_{day}.mp4").exists():
        return ""
    i = 2
    while (out_dir / f"lofi_{day}({i}).mp4").exists():
        i += 1
    return f"({i})"


def _dates_in_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _last_generated_date(out_dir: Path) -> date | None:
    if not out_dir.exists():
        return None
    latest: date | None = None
    for child in out_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            d = date.fromisoformat(child.name)
        except ValueError:
            continue
        if any(child.glob("lofi_*.mp4")) and (latest is None or d > latest):
            latest = d
    return latest

# ── Main modes ─────────────────────────────────────────────────────────────────

def run_generate(days: int, start: date, youtube) -> None:
    n = min(days, 16)
    print(f"Fetching {n}-day forecast for Tokyo, Japan...")
    codes, dates = fetch_forecast(n)

    # Align forecast to requested start date
    today = date.today()
    offset = (start - today).days

    for i in range(n):
        day    = start + timedelta(days=i)
        code   = codes[i] if i < len(codes) else 0
        rainy  = code in RAINY_CODES
        mood   = "Rainy" if rainy else "Sunny"
        target = random.randint(TARGET_MIN, TARGET_MAX)
        day_str = day.isoformat()

        print(f"\n[{day_str}]  {mood}  |  target {target // 60} min")

        songs, total = pick_songs(RAINY_DIR if rainy else SUNNY_DIR, target)
        image        = pick_image(rainy)
        out_dir      = OUTPUT_DIR / day_str
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix       = _next_suffix(out_dir, day_str)
        out_file     = out_dir / f"lofi_{day_str}{suffix}.mp4"
        meta_file    = out_dir / f"meta_{day_str}{suffix}.json"

        print(f"  Image  : {image.name}")
        print(f"  Tracks : {len(songs)} songs  ({total / 60:.1f} min)")
        print(f"  Output : {out_file}")

        t_start = time.perf_counter()
        make_video(songs, image, out_file, total)
        elapsed = time.perf_counter() - t_start
        mins, secs = divmod(int(elapsed), 60)

        metadata = make_metadata(day_str, rainy, total)
        meta_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Done!  [{mins}m {secs:02d}s]  meta -> {meta_file.name}")

        if youtube:
            print(f"  Subindo para o YouTube...")
            try:
                upload_to_youtube(youtube, out_file, metadata, day_str)
            except Exception as exc:
                print(f"  [WARN] Upload falhou: {exc} — vídeo salvo em {out_file}", file=sys.stderr)

    print(f"\n✅ {n} vídeo(s) gerado(s).")


def run_batch_upload(start: date, end: date, youtube) -> None:
    if youtube is None:
        sys.exit("[ERROR] Credenciais YouTube não configuradas no .env")

    print(f"Escaneando vídeos de {start} até {end}...")
    uploaded = 0

    for day in _dates_in_range(start, end):
        day_str  = day.isoformat()
        out_dir  = OUTPUT_DIR / day_str
        if not out_dir.exists():
            continue

        for mp4 in sorted(out_dir.glob("lofi_*.mp4")):
            suffix   = mp4.stem.replace(f"lofi_{day_str}", "")
            meta_path = out_dir / f"meta_{day_str}{suffix}.json"
            if not meta_path.exists():
                print(f"  [SKIP] {mp4.name} — sem metadata JSON")
                continue

            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            print(f"\n[{day_str}] {mp4.name}")
            try:
                upload_to_youtube(youtube, mp4, metadata, day_str)
                uploaded += 1
            except Exception as exc:
                print(f"  [WARN] Upload falhou: {exc}", file=sys.stderr)

    print(f"\n✅ {uploaded} vídeo(s) subido(s).")

# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sweet Morning Lofi — gera vídeos e faz upload agendado para o YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-n", type=int, default=7, metavar="N",
                        help="Número de vídeos a gerar (padrão: 7)")
    parser.add_argument("-b", metavar="DD-MM-AAAA",
                        help="Data inicial (padrão: hoje)")
    parser.add_argument("-c", "--continue", dest="continue_", action="store_true",
                        help="Continua a partir do dia seguinte ao último vídeo em output/")
    parser.add_argument("--upload-from", metavar="DD-MM-AAAA",
                        help="Sobe vídeos já gerados a partir desta data")
    parser.add_argument("--upload-to", metavar="DD-MM-AAAA",
                        help="Limita o upload até esta data (usar com --upload-from)")
    args = parser.parse_args()

    env     = load_env()
    youtube = _build_youtube_client(env)
    if youtube is None:
        print("[WARN] Credenciais YouTube não encontradas — vídeos serão gerados mas não subidos.")

    def parse_date(s):
        try:
            d, m, y = s.split("-")
            return date(int(y), int(m), int(d))
        except Exception:
            parser.error(f"Data inválida '{s}' — use o formato DD-MM-AAAA (ex: 20-05-2026)")

    if args.upload_from:
        start = parse_date(args.upload_from)
        end   = parse_date(args.upload_to) if args.upload_to else date(9999, 1, 1)
        run_batch_upload(start, end, youtube)
    elif args.continue_:
        last = _last_generated_date(OUTPUT_DIR)
        if last is None:
            start = parse_date(args.b) if args.b else date.today()
            print(f"[INFO] Nenhum vídeo encontrado em {OUTPUT_DIR} — começando de {start.isoformat()}.")
        else:
            start = last + timedelta(days=1)
            print(f"[INFO] Último vídeo em {last.isoformat()} — continuando de {start.isoformat()}.")
        run_generate(args.n, start, youtube)
    else:
        start = parse_date(args.b) if args.b else date.today()
        run_generate(args.n, start, youtube)


if __name__ == "__main__":
    main()
