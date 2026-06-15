import json
import random
import subprocess
import shutil
from pathlib import Path

import librosa
import numpy as np

from . import config

W, H           = 1080, 1920
VIDEO_DURATION = 35.0


def _video_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-select_streams", "v:0", str(path)],
        capture_output=True, text=True, check=True,
    )
    for s in json.loads(r.stdout).get("streams", []):
        if "duration" in s:
            return float(s["duration"])
    r2 = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(r2.stdout)["format"]["duration"])


def _music_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(r.stdout)["format"]["duration"])


def _beat_intervals(music_path, start, duration, every_n_beats=2):
    """Return list of clip durations aligned to beats in the music."""
    print("Detecting beats...", flush=True)
    y, sr = librosa.load(str(music_path), sr=None, offset=start,
                         duration=duration, mono=True)
    _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Take every Nth beat so clips are ~1-2s instead of one per 0.5s
    beat_times = beat_times[::every_n_beats]

    # Add endpoint so last clip runs to the video end
    beat_times = np.append(beat_times, duration)

    # Clip durations = gap between consecutive beats
    intervals = np.diff(beat_times).tolist()
    # Remove any negative or near-zero intervals
    intervals = [max(0.1, iv) for iv in intervals if iv > 0.05]

    tempo = 60.0 / (np.mean(np.diff(beat_times)) / every_n_beats) if len(beat_times) > 1 else 0
    print(f"  ~{tempo:.0f} BPM  |  {len(intervals)} cuts over {duration:.0f}s", flush=True)
    return intervals


def compose(output_path, every_n_beats=2, music_path=None):
    clips = list(config.LIFESTYLE_DIR.glob("*.mp4")) + \
            list(config.LIFESTYLE_DIR.glob("*.mov"))
    if not clips:
        raise FileNotFoundError(f"No clips found in {config.LIFESTYLE_DIR}")

    if music_path is None:
        music_files = list(config.MONEY_MUSIC_DIR.glob("*.mp3")) + \
                      list(config.MONEY_MUSIC_DIR.glob("*.m4a"))
        if not music_files:
            raise FileNotFoundError(f"No music in {config.MONEY_MUSIC_DIR}")
        music_path = random.choice(music_files)

    print(f"Music: {music_path.name}")

    music_total = _music_duration(music_path)
    music_start = round(random.uniform(0, max(0.0, music_total - VIDEO_DURATION - 1)), 2)
    print(f"Music offset: {music_start:.1f}s")

    intervals = _beat_intervals(music_path, music_start, VIDEO_DURATION, every_n_beats)

    config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    random.shuffle(clips)
    clip_pool    = clips[:]
    segment_paths = []

    for i, seg_len in enumerate(intervals):
        if not clip_pool:
            clip_pool = clips[:]
            random.shuffle(clip_pool)
        clip     = clip_pool.pop()
        dur      = _video_duration(clip)
        seg_len  = round(min(seg_len, dur), 3)
        max_start = max(0.0, dur - seg_len)
        start    = round(random.uniform(0, max_start), 3)

        out = config.TEMP_DIR / f"seg_{i:04d}.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(start), "-t", str(seg_len),
            "-i", str(clip),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                   f"crop={W}:{H},setsar=1",
            "-an",
            "-c:v", "libx264", "-crf", "20", "-preset", "fast",
            "-r", "30",
            str(out),
        ], check=True, capture_output=True)
        segment_paths.append(out)
        print(f"  [{i+1:3d}] {clip.name:<10} {start:.2f}s + {seg_len:.2f}s")

    total = sum(intervals)
    print(f"\n{len(segment_paths)} beats  =  {total:.1f}s")

    # Concat
    concat_list = config.TEMP_DIR / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in segment_paths:
            escaped = p.resolve().as_posix().replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    joined = config.TEMP_DIR / "joined.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(joined),
    ], check=True, capture_output=True)

    print("Mixing music...")
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(joined),
            "-ss", str(music_start), "-t", str(VIDEO_DURATION), "-i", str(music_path),
            "-map", "0:v", "-map", "1:a",
            "-t", str(VIDEO_DURATION),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(output_path),
        ], check=True)
    finally:
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)

    print(f"\nDone -> {output_path}")
    return output_path
