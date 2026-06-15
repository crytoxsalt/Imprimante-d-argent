import json
import random
import subprocess
from pathlib import Path

import numpy as np

from imprimante_argent import config

from .data  import dca_portfolio, lump_sum_portfolios
from .chart import dca_chart_frames, comparison_chart_frames
from .card  import render_title_dca, render_title_comparison

_W, _H  = 1080, 1920
_FPS    = 24
_BG     = (255, 255, 255)
DEFAULT_DURATION = 60.0


def run_dca(
    ticker: str,
    ticker_name: str,
    start_year: int,
    monthly: float = 100.0,
    duration: float = DEFAULT_DURATION,
) -> str:
    print(f"Fetching {ticker} data since {start_year}...")
    df = dca_portfolio(ticker, start_year, monthly)

    output_path = config.OUTPUT_DIR / f"{ticker.lower()}_dca_{start_year}.mp4"
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    title_img = render_title_dca(ticker_name, monthly, start_year)
    n_frames  = int(_FPS * duration)

    print(f"Rendering {n_frames} frames ({duration:.0f}s)...")
    _compose(
        title_img,
        dca_chart_frames(df, ticker_name, n_frames, _FPS),
        output_path,
        duration,
    )

    print(f"\nDone -> {output_path}")
    return str(output_path)


def run_comparison(
    tickers: list[str],
    ticker_names: dict[str, str],
    start_year: int,
    investment: float = 1000.0,
    duration: float = DEFAULT_DURATION,
) -> str:
    print(f"Fetching data for {', '.join(tickers)} since {start_year}...")
    portfolios = lump_sum_portfolios(tickers, start_year, investment)

    slug        = "_vs_".join(t.lower() for t in tickers) + f"_{start_year}"
    output_path = config.OUTPUT_DIR / f"{slug}.mp4"
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    title_img = render_title_comparison(ticker_names, investment, start_year)
    n_frames  = int(_FPS * duration)

    print(f"Rendering {n_frames} frames ({duration:.0f}s)...")
    _compose(
        title_img,
        comparison_chart_frames(portfolios, ticker_names, n_frames, _FPS),
        output_path,
        duration,
    )

    print(f"\nDone -> {output_path}")
    return str(output_path)


def _pick_music() -> Path:
    config.MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    files = (
        list(config.MUSIC_DIR.glob("*.mp3"))
        + list(config.MUSIC_DIR.glob("*.m4a"))
        + list(config.MUSIC_DIR.glob("*.opus"))
        + list(config.MUSIC_DIR.glob("*.webm"))
    )
    if not files:
        raise FileNotFoundError(
            f"No music files found in {config.MUSIC_DIR}. "
            "Run: python download_playlist.py"
        )
    return random.choice(files)


def _audio_start(path: Path, duration: float) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    total = float(json.loads(r.stdout)["format"]["duration"])
    return random.uniform(0, max(0.0, total - duration - 1))


def _compose(title_img, frame_gen, output_path, duration: float):
    """Pipe raw RGB frames to FFmpeg with a random playlist song."""
    music = _pick_music()
    start = _audio_start(music, duration)
    safe  = music.name.encode("ascii", errors="replace").decode()
    print(f"  Music: {safe} (from {start:.0f}s)")

    proc = subprocess.Popen([
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{_W}x{_H}", "-framerate", str(_FPS),
        "-i", "pipe:0",
        "-stream_loop", "-1", "-ss", str(start), "-t", str(duration),
        "-i", str(music),
        "-map", "0:v", "-map", "1:a",
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    ], stdin=subprocess.PIPE)

    title_arr = np.array(title_img, dtype=np.uint8)
    title_h   = title_arr.shape[0]
    canvas    = np.full((_H, _W, 3), _BG, dtype=np.uint8)
    canvas[:title_h] = title_arr

    try:
        for chart_img in frame_gen:
            chart_arr = np.array(chart_img, dtype=np.uint8)
            ch        = chart_arr.shape[0]
            canvas[title_h:title_h + ch] = chart_arr
            proc.stdin.write(canvas.tobytes())
    finally:
        proc.stdin.close()

    proc.wait()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, "ffmpeg")
