import json
import random
import subprocess
import time
from pathlib import Path

from . import config

W, H = 1080, 1920


def _dur(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(r.stdout)["format"]["duration"])


def _ffmpeg_font(path: Path) -> str:
    """Return an FFmpeg-safe font path; falls back to Arial when path has apostrophe."""
    s = str(path).replace("\\", "/")
    if "'" in s:
        for fb in ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"]:
            if Path(fb).exists():
                s = fb
                break
    if len(s) > 1 and s[1] == ":":
        s = s[0] + "\\:" + s[2:]
    return s


def _title_filter(title_text):
    font = _ffmpeg_font(config.FONT_BOLD)
    esc  = title_text.replace("'", "\\'")
    return (
        f"drawtext=text='{esc}':fontfile='{font}':"
        f"fontsize=58:fontcolor=black:box=1:boxcolor=white@1.0:boxborderw=22:"
        f"x=(w-text_w)/2:y=30"
    )


def _export(input_path, output_path, ss, duration, title_text, loop=False):
    """Export one full 9:16 clip with title burned in, muted."""
    filt = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1[scaled];"
        f"[scaled]{_title_filter(title_text)}[vid]"
    )
    loop_flag = ["-stream_loop", "-1"] if loop else []
    subprocess.run([
        "ffmpeg", "-y",
        *loop_flag, "-ss", str(ss), "-t", str(duration), "-i", str(input_path),
        "-filter_complex", filt,
        "-map", "[vid]",
        "-an",
        "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast", "-r", "30",
        str(output_path),
    ], check=True)


def compose_part(rwj_clip, gta_clip, output_path, tv_start, duration, title_text):
    """
    Two full 9:16 clips (1080x1920 each) placed side by side → 2160x1920 output.
    No cropping, no squishing. Title burned on both halves at the top.
    """
    font     = _ffmpeg_font(config.FONT_BOLD)
    esc      = title_text.replace("'", "\\'")
    title_f  = (
        f"drawtext=text='{esc}':fontfile='{font}':"
        f"fontsize=58:fontcolor=black:box=1:boxcolor=white@1.0:boxborderw=22:"
        f"x=(w-text_w)/2:y=30"
    )
    gta_loop = ["-stream_loop", "-1"] if _dur(gta_clip) < duration else []

    filt = (
        # Left: RWJ at full 9:16
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1[left];"
        # Right: GTA at full 9:16
        f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1[right];"
        # Place side by side → 2160x1920
        f"[left][right]hstack=inputs=2[combined];"
        # Title overlay centered across full width
        f"[combined]{title_f}[vid]"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(tv_start), "-t", str(duration), "-i", str(rwj_clip),
        *gta_loop, "-t", str(duration), "-i", str(gta_clip),
        "-filter_complex", filt,
        "-map", "[vid]",
        "-an",
        "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast", "-r", "30",
        str(output_path),
    ], check=True)


def run(video_path, parts, duration, title=None, use_base=False):
    video_path = Path(video_path)
    total_dur  = _dur(video_path)

    if use_base and config.BASE_VIDEO.exists():
        gta_clip = config.BASE_VIDEO
    else:
        gameplay = list(config.GAMEPLAY_DIR.glob("*.mp4"))
        if not gameplay:
            raise FileNotFoundError(f"No gameplay clips in {config.GAMEPLAY_DIR}")
        gta_clip = random.choice(gameplay)

    if not title:
        from .ai_title import title_from_video
        title = title_from_video(video_path)

    print(f"Video:     {video_path.name}")
    print(f"Bottom:    {gta_clip.name}")
    print(f"Title:     {title}")
    print(f"Total dur: {total_dur:.1f}s  ->  {parts} parts x {duration}s\n")

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())

    for part in range(1, parts + 1):
        start = (part - 1) * duration
        if start >= total_dur:
            print(f"Video ended — stopping at {part - 1} part(s).")
            break

        part_dur   = min(duration, total_dur - start)
        title_text = f"{title} Part {part}" if title != "Part" else f"Part {part}"
        out        = config.OUTPUT_DIR / f"rwj_part{part}_{ts}.mp4"

        out = config.OUTPUT_DIR / f"rwj_part{part}_{ts}.mp4"

        print(f"--- {title_text}  (offset {start:.0f}s, {part_dur:.0f}s) ---")
        compose_part(video_path, gta_clip, out, start, part_dur, title_text)
        print(f"Saved: {out.name}\n")

    print(f"All parts saved to {config.OUTPUT_DIR}/")
