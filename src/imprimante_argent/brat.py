"""
BRAT lyric video - Python port of bratAnimator's classic rendering mode.
  1. Search LRCLIB for synced lyrics (free, no key)
  2. Fall back to Whisper transcription
  3. Render frames with PIL matching the JS drawScene classic mode
  4. Pipe raw frames to FFmpeg with the music track
"""
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from . import config

W, H          = 1080, 1920
BG            = (0x8A, 0xCE, 0x00)   # #8ACE00
FG            = (0, 0, 0)            # #000000
FPS           = 30
LINE_SPACING  = 0.92                 # matches JS default
STRETCH       = 0.94                 # horizontal text compress (JS default)
MAX_W_RATIO   = 0.76
MAX_H_RATIO   = 0.48


# ── font helpers ──────────────────────────────────────────────────────────────

def _font_path() -> str:
    """Arial Narrow (weight 400) is the JS default; fall back to Arial."""
    candidates = [
        "C:/Windows/Fonts/arialn.ttf",    # Arial Narrow regular
        "C:/Windows/Fonts/arial.ttf",      # Arial regular
        str(config.FONT_BOLD),             # Montserrat-Bold last resort
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    raise FileNotFoundError("No suitable font found")


_FONT_CACHE: dict = {}
_FP = None

def _font(size: int) -> ImageFont.FreeTypeFont:
    global _FP
    if _FP is None:
        _FP = _font_path()
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = ImageFont.truetype(_FP, size)
    return _FONT_CACHE[size]


# ── text layout (port of fitTextLayout + measureWrappedLines) ─────────────────

def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: float) -> list:
    """Word-wrap text to fit max_w pixels."""
    words = text.split()
    if not words:
        return ["brat"]
    lines, cur = [], words[0]
    dummy = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy)
    for w in words[1:]:
        candidate = cur + " " + w
        if draw.textlength(candidate, font=font) <= max_w:
            cur = candidate
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _fit_layout(text: str, max_w: float, max_h: float, start_size: int):
    """Return (font, wrapped_lines, line_height) that fits within max_w x max_h."""
    dummy = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy)
    for size in range(start_size, 22, -2):
        font = _font(size)
        lines = _wrap(text, font, max_w)
        line_h = size * LINE_SPACING
        total_h = len(lines) * line_h
        widest = max(draw.textlength(l, font=font) for l in lines)
        if widest <= max_w and total_h <= max_h:
            return font, lines, line_h
    font = _font(22)
    return font, _wrap(text, font, max_w), 22 * LINE_SPACING


# ── LRC / lyrics ──────────────────────────────────────────────────────────────

def _search_lrclib(query: str) -> Optional[str]:
    url = "https://lrclib.net/api/search?q=" + urllib.parse.quote(query)
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            results = json.loads(r.read())
        for item in results:
            if item.get("syncedLyrics"):
                print(f"  LRCLIB: {item.get('artistName')} – {item.get('trackName')}")
                return item["syncedLyrics"]
    except Exception as e:
        print(f"  LRCLIB failed: {e}")
    return None


def _transcribe(audio_path: Path, model_size: str) -> str:
    from faster_whisper import WhisperModel
    print("  Transcribing with Whisper...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(str(audio_path), beam_size=1)
    lines = []
    for s in segs:
        m, sec = divmod(s.start, 60)
        lines.append(f"[{int(m):02d}:{sec:05.2f}] {s.text.strip()}")
    return "\n".join(lines)


def _parse_lrc(lrc: str) -> list:
    """Return [(start_sec, end_sec, text), ...] with durations filled in."""
    raw = []
    for line in lrc.splitlines():
        text = re.sub(r"\[[\d:.,<>]+\]", "", line).strip().lower()
        if not text:
            continue
        for m, s in re.findall(r"\[(\d+):(\d+(?:[.,]\d+)?)\]", line):
            raw.append((int(m) * 60 + float(s.replace(",", ".")), text))
    raw = sorted(raw, key=lambda x: x[0])
    out = []
    for i, (start, text) in enumerate(raw):
        end = raw[i + 1][0] if i + 1 < len(raw) else start + 4.0
        out.append((start, end, text))
    return out


# ── frame renderer ────────────────────────────────────────────────────────────

def _render_frame(lyrics: list, t: float, max_w: float, max_h: float,
                  start_size: int, watermark: str = "@geldmaker") -> bytes:
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # find active line
    active_text = None
    line_progress = 0.0
    for (start, end, text) in lyrics:
        if start <= t:
            active_text = text
            dur = max(0.001, end - start)
            line_progress = min(1.0, (t - start) / dur)
        else:
            break

    if active_text is None:
        # before first lyric: show watermark fully, no typewriter
        display = watermark
    else:
        # typewriter: reveal all chars by 75% of line duration, hold the rest
        reveal_progress = min(1.0, line_progress / 0.75)
        visible_chars = max(1, int(reveal_progress * len(active_text)))
        display = active_text[:visible_chars]

    font, lines, line_h = _fit_layout(display, max_w, max_h, start_size)

    total_h = len(lines) * line_h
    center_y = H / 2
    # JS: startY = centerY - totalHeight/2 + lineHeight * 0.82
    start_y = center_y - total_h / 2 + line_h * 0.82

    for i, line in enumerate(lines):
        tw = draw.textlength(line, font=font)
        # JS applies ctx.scale(STRETCH, 1) — simulate by centering as normal
        # (PIL can't scale just text; the difference is subtle at 0.94)
        x = (W - tw * STRETCH) / 2
        y = start_y + i * line_h
        draw.text((x, y), line, font=font, fill=FG)

    return img.tobytes()


# ── pipeline ──────────────────────────────────────────────────────────────────

def render_video(lyrics: list, audio_path: Path, output_path: Path,
                 watermark: str = "@geldmaker") -> None:
    total   = lyrics[-1][1] + 1.0      # end of last line + 1s
    frames  = int(total * FPS)
    max_w   = W * MAX_W_RATIO
    max_h   = H * MAX_H_RATIO
    start_s = int(W * 0.118)           # JS: Math.floor(width * 0.118)

    proc = subprocess.Popen([
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "pipe:0",
        "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_path),
    ], stdin=subprocess.PIPE)

    print(f"Rendering {frames} frames ({total:.0f}s)...")
    for i in range(frames):
        proc.stdin.write(_render_frame(lyrics, i / FPS, max_w, max_h, start_s, watermark))
        if i % (FPS * 15) == 0:
            print(f"  {i / FPS:.0f}s / {total:.0f}s")

    proc.stdin.close()
    proc.wait()


def run(music_path: Path, output_path: Path, model_size: str = "base",
        artist: str = "", watermark: str = "@geldmaker") -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    music_path = Path(music_path)

    query = f"{artist} {music_path.stem}".strip()
    print(f"Searching LRCLIB for '{query}'...")
    lrc = _search_lrclib(query)
    if not lrc:
        lrc = _transcribe(music_path, model_size)

    lyrics = _parse_lrc(lrc)
    if not lyrics:
        raise ValueError("No lyrics parsed")
    print(f"  {len(lyrics)} lines loaded")

    render_video(lyrics, music_path, output_path, watermark=watermark)
    print(f"\nSaved: {output_path}")
