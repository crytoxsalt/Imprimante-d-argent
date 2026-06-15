"""
Portrait movie clip composer — 9:16 crop with burned-in subtitles.
Used by the `movies` command.
"""
import os
import re
import subprocess
from pathlib import Path

from . import config
from .transcribe import get_word_timestamps

CANVAS_W = 1080
CANVAS_H = 1920

_ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,5,3,2,60,60,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


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


def _parse_srt(path: Path) -> list:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
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
        start = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000
        end   = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000
        line  = " ".join(lines[2:]).strip()
        line  = re.sub(r"<[^>]+>", "", line).strip()
        if line:
            entries.append({"word": line, "start": start, "end": end})
    return entries


def _write_ass(words, path):
    lines = [_ASS_HEADER.format(w=CANVAS_W, h=CANVAS_H).rstrip()]
    for w in words:
        text = w["word"].replace("\\", "\\\\").replace("{", "\\{")
        lines.append(
            f"Dialogue: 0,{_fmt(w['start'])},{_fmt(w['end'])},Default,,0,0,0,,{text}"
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def compose(movie_clip: Path, output_path: Path,
            clip_start: float = 0.0, duration: float = 60.0,
            srt_path=None):
    """
    Crop movie_clip to 9:16 portrait and burn subtitles.
    clip_start: the offset (seconds from movie start) used when downloading,
                needed to align SRT timestamps to the clip.
    """
    config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"  Clip: {clip_start:.0f}s — {clip_start + duration:.0f}s ({duration:.0f}s)")

    words = []
    if srt_path and Path(srt_path).exists():
        print("Loading captions from SRT...")
        raw = _parse_srt(srt_path)
        # SRT timestamps are absolute from movie start; shift to clip-relative
        words = [
            {"word": e["word"],
             "start": e["start"] - clip_start,
             "end":   e["end"]   - clip_start}
            for e in raw
            if e["end"] > clip_start and e["start"] < clip_start + duration
        ]
        print(f"  {len(words)} subtitle lines")

    if not words:
        if srt_path:
            print("  No subtitles matched this range — falling back to Whisper")
        else:
            print("  No SRT — transcribing with Whisper...")
        audio_path = config.TEMP_DIR / "movie_audio.mp3"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(movie_clip),
            "-vn", "-acodec", "mp3", "-ab", "192k", str(audio_path),
        ], check=True, capture_output=True)
        words = get_word_timestamps(audio_path)
        print(f"  {len(words)} words")

    ass_path = config.TEMP_DIR / "movie_captions.ass"
    _write_ass(words, ass_path)

    af = f"ass={_esc(ass_path)}:fontsdir={_esc(config.FONTS_DIR)}"
    filt = (
        f"[0:v]scale={CANVAS_W}:{CANVAS_H}:force_original_aspect_ratio=increase,"
        f"crop={CANVAS_W}:{CANVAS_H}[scaled];"
        f"[scaled]{af}[outv]"
    )

    print("Composing portrait clip...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(movie_clip),
        "-filter_complex", filt,
        "-map", "[outv]",
        "-map", "0:a",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    ], check=True)

    print(f"Done -> {output_path}")
    return output_path
