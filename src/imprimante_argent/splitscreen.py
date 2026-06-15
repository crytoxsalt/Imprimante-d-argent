import json
import os
import random
import re
import shutil
import subprocess
from pathlib import Path

from . import config
from .transcribe import get_word_timestamps

HALF_H = 960

_ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: {half_h}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat,80,&H0000FFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,5,3,2,60,60,25,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(r.stdout)["format"]["duration"])


def _fmt(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = int(round((s % 1) * 100))
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


def _esc(path):
    path = os.fspath(path)
    try:
        rel = os.path.relpath(path)
        if not rel.startswith(".."):
            return rel.replace("\\", "/")
    except Exception:
        pass
    p = os.path.abspath(path).replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        p = p[0] + "\\:" + p[2:]
    return p


def _write_ass(words, path):
    lines = [_ASS_HEADER.format(half_h=HALF_H).rstrip()]
    for w in words:
        text = w["word"].upper().replace("\\", "\\\\").replace("{", "\\{")
        lines.append(
            f"Dialogue: 0,{_fmt(w['start'])},{_fmt(w['end'])},Default,,0,0,0,,{text}"
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _parse_srt(path: Path) -> list:
    """Parse an SRT file into [{word, start, end}] entries (one per subtitle line)."""
    text    = Path(path).read_text(encoding="utf-8", errors="replace")
    entries = []
    for block in re.split(r"\n\n+", text.strip()):
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        m = re.match(
            r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)",
            lines[1],
        )
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = m.groups()
        start  = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000
        end    = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000
        line   = " ".join(lines[2:]).strip()
        line   = re.sub(r"<[^>]+>", "", line).strip()   # strip HTML tags
        if line:
            entries.append({"word": line, "start": start, "end": end})
    return entries


def compose(tv_clip, gameplay_clip, output_path, min_dur=30.0, max_dur=90.0,
            part_label=None, srt_path=None, clip_offset=0.0):
    config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tv_total = _duration(tv_clip)
    gta_total = _duration(gameplay_clip)
    duration = random.uniform(min_dur, max_dur)

    tv_start = random.uniform(0, max(0.0, tv_total - duration - 1))
    gta_start = random.uniform(0, max(0.0, gta_total - duration - 1))

    print(f"  TV segment:       {tv_start:.1f}s — {tv_start + duration:.1f}s ({duration:.0f}s)")
    print(f"  Gameplay segment: {gta_start:.1f}s — {gta_start + duration:.1f}s")

    if srt_path and Path(srt_path).exists():
        # Use VidVault SRT — no Whisper needed
        # SRT timestamps are episode-absolute; shift by clip_offset (download start) + tv_start
        print("Loading captions from SRT...")
        raw_words  = _parse_srt(srt_path)
        abs_start  = clip_offset + tv_start
        words = [
            {"word": e["word"], "start": e["start"] - abs_start, "end": e["end"] - abs_start}
            for e in raw_words
            if e["end"] > abs_start and e["start"] < abs_start + duration
        ]
        print(f"  {len(words)} subtitle lines")
    else:
        # Fall back to Whisper transcription
        audio_path = config.TEMP_DIR / "fg_audio.mp3"
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(tv_start), "-t", str(duration),
            "-i", str(tv_clip),
            "-vn", "-acodec", "mp3", "-ab", "192k",
            str(audio_path),
        ], check=True, capture_output=True)

        print("Transcribing TV audio with Whisper...")
        words = get_word_timestamps(audio_path)
        print(f"  {len(words)} words timestamped")

    ass_path = config.TEMP_DIR / "fg_captions.ass"
    _write_ass(words, ass_path)

    # Build filter: each input is pre-seeked via -ss, so no trim needed
    af = f"ass={_esc(ass_path)}:fontsdir={_esc(config.FONTS_DIR)}"
    font_path = _esc(config.FONT_BOLD)
    part_filter = (
        f"[stacked]drawtext=fontfile='{font_path}':text='{part_label}':"
        f"fontsize=72:fontcolor=white:borderw=4:bordercolor=black:"
        f"x=(w-text_w)/2:y=40[outv]"
        if part_label else "[stacked]copy[outv]"
    )
    filt = (
        # Top half: scale FG to fill 1080×960, burn yellow captions
        f"[0:v]scale=1080:{HALF_H}:force_original_aspect_ratio=increase,"
        f"crop=1080:{HALF_H}[fg];"
        f"[fg]{af}[fg_cap];"
        # Bottom half: scale gameplay to fill 1080×960
        f"[1:v]scale=1080:{HALF_H}:force_original_aspect_ratio=increase,"
        f"crop=1080:{HALF_H}[gta];"
        # Stack vertically → 1080×1920, then optionally burn part label
        f"[fg_cap][gta]vstack[stacked];"
        + part_filter
    )

    print("Composing split-screen video...")
    use_srt = srt_path and Path(srt_path).exists()
    try:
        if use_srt:
            # Audio comes from TV clip input (0:a) — no separate audio file needed
            subprocess.run([
                "ffmpeg", "-y",
                "-ss", str(tv_start),  "-t", str(duration), "-i", str(tv_clip),
                "-ss", str(gta_start), "-t", str(duration), "-i", str(gameplay_clip),
                "-filter_complex", filt,
                "-map", "[outv]",
                "-map", "0:a",
                "-c:v", "libx264", "-crf", "23", "-preset", "fast",
                "-c:a", "aac", "-b:a", "192k",
                str(output_path),
            ], check=True)
        else:
            subprocess.run([
                "ffmpeg", "-y",
                "-ss", str(tv_start),  "-t", str(duration), "-i", str(tv_clip),
                "-ss", str(gta_start), "-t", str(duration), "-i", str(gameplay_clip),
                "-i", str(audio_path),
                "-filter_complex", filt,
                "-map", "[outv]",
                "-map", "2:a",
                "-c:v", "libx264", "-crf", "23", "-preset", "fast",
                "-c:a", "aac", "-b:a", "192k",
                str(output_path),
            ], check=True)
    finally:
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)

    print(f"\nDone -> {output_path}")
    return output_path
