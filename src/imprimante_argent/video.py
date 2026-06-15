import json
import os
import random
import subprocess

from . import config


def _duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(r.stdout)["format"]["duration"])


def _esc(path):
    """Return a filter_complex-safe path: relative if possible (avoids spaces in CWD name)."""
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


def compose(base_video, audio_path, ass_path, output_path,
            titlecard_path=None, titlecard_duration=4.0):

    audio_dur = _duration(audio_path)
    video_dur = _duration(base_video)

    max_start = max(0.0, video_dur - audio_dur - 1)
    start = random.uniform(0, max_start)

    ass_filter = f"ass={_esc(ass_path)}:fontsdir={_esc(config.FONTS_DIR)}"

    if titlecard_path:
        tc_dur = min(titlecard_duration, audio_dur)
        # 1. Dark overlay on video during title card window
        # 2. Burn ASS captions on the darkened video
        # 3. Overlay PNG title card centered in the frame
        filt = (
            f"[0:v]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.55:t=fill"
            f":enable='between(t,0,{tc_dur:.2f})'[dk];"
            f"[dk]{ass_filter}[cap];"
            f"[cap][2:v]overlay=x=(W-w)/2:y=(H-h)/2:enable='between(t,0,{tc_dur:.2f})'[outv]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-i", base_video,
            "-i", audio_path,
            "-i", titlecard_path,
            "-filter_complex", filt,
            "-map", "[outv]", "-map", "1:a",
            "-t", str(audio_dur),
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-i", base_video,
            "-i", audio_path,
            "-vf", ass_filter,
            "-map", "0:v", "-map", "1:a",
            "-t", str(audio_dur),
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ]

    subprocess.run(cmd, check=True)
