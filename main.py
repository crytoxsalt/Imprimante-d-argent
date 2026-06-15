import re
import sys
import argparse
import random
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from imprimante_argent import config


def cmd_reddit(args):
    from imprimante_argent.main import run
    run(args.subreddit)


def cmd_familyguy(args):
    from imprimante_argent.fgdownload import download_segment, episode_url
    from imprimante_argent.splitscreen import compose
    SEASONS = {4: 30, 5: 18, 6: 12, 7: 16, 8: 21}
    SKIP_INTRO, SKIP_OUTRO = 60, 120

    gameplay_clips = list(config.GAMEPLAY_DIR.glob("*.mp4"))
    if not gameplay_clips:
        sys.exit(f"No gameplay clips in {config.GAMEPLAY_DIR}")

    season  = random.choice(list(SEASONS.keys()))
    episode = random.randint(1, SEASONS[season])
    url     = episode_url(season, episode)

    total     = args.duration * args.parts
    max_start = max(SKIP_INTRO, 1320 - SKIP_OUTRO - total)
    seg_start = random.randint(SKIP_INTRO, max_start)

    print(f"Episode:  Family Guy S{season:02d}E{episode:02d}")
    print(f"Parts:    {args.parts} x {args.duration}s  (offset {seg_start}s)\n")

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())

    for part in range(1, args.parts + 1):
        part_start = seg_start + (part - 1) * args.duration
        print(f"--- Part {part}/{args.parts}  (offset {part_start}s) ---")

        config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        tv_clip = config.TEMP_DIR / f"fg_part{part}.mp4"

        # Retry up to 10 times with a different episode if API returns nothing
        srt_path = None
        for attempt in range(10):
            try:
                srt_path = download_segment(url, tv_clip, start=part_start, duration=args.duration)
                break
            except Exception:
                if attempt == 9:
                    raise
                season  = random.choice(list(SEASONS.keys()))
                episode = random.randint(1, SEASONS[season])
                url     = episode_url(season, episode)
                print(f"  Retrying with S{season:02d}E{episode:02d}...")
                seg_start = random.randint(SKIP_INTRO, max_start)
                part_start = seg_start + (part - 1) * args.duration

        gameplay = random.choice(gameplay_clips)
        print(f"Gameplay: {gameplay.name}")

        out = config.OUTPUT_DIR / f"fg_s{season:02d}e{episode:02d}_part{part}_{timestamp}.mp4"
        compose(
            tv_clip, gameplay, out,
            min_dur=float(args.duration),
            max_dur=float(args.duration),
            part_label=f"Part {part}",
            srt_path=srt_path,
            clip_offset=float(part_start),
        )
        print()

    print(f"All {args.parts} parts saved to {config.OUTPUT_DIR}/")


def cmd_rwj(args):
    from imprimante_argent.rwj import run
    rwj_dir = config.ASSETS_DIR / "rwj"
    if args.video:
        video = Path(args.video)
    else:
        videos = list(rwj_dir.glob("*.mp4")) + list(rwj_dir.glob("*.webm"))
        if not videos:
            sys.exit(f"No videos in {rwj_dir}\nRun: python scripts/pull_tiktok.py")
        video = random.choice(videos)
        print(f"Video: {video.name}")
    run(video, parts=args.parts, duration=args.duration,
        title=args.title or None, use_base=args.use_base)


def cmd_brat(args):
    import time
    from imprimante_argent.brat import run
    music_path = Path(args.music_path)
    if not music_path.exists():
        sys.exit(f"Music file not found: {music_path}")
    out = config.OUTPUT_DIR / f"brat_{int(time.time())}.mp4"
    run(music_path, out, model_size=args.model, artist=args.artist, watermark=args.watermark, whisper=args.whisper)


def cmd_movies(args):
    from imprimante_argent.fgdownload import movie_url, download_segment
    from imprimante_argent.movieclip import compose

    MOVIES = {
        550:    "Fight Club",
        278:    "The Shawshank Redemption",
        680:    "Pulp Fiction",
        155:    "The Dark Knight",
        27205:  "Inception",
        157336: "Interstellar",
        13:     "Forrest Gump",
        603:    "The Matrix",
        769:    "Goodfellas",
        475557: "Joker",
        496243: "Parasite",
        419430: "Get Out",
        546554: "Knives Out",
        24428:  "The Avengers",
        76341:  "Mad Max Fury Road",
        299534: "Avengers Endgame",
        11:     "Star Wars A New Hope",
        120:    "Lord of the Rings Fellowship",
        122:    "Lord of the Rings Return of the King",
        597:    "Titanic",
    }

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())

    for part in range(1, args.parts + 1):
        print(f"--- Part {part}/{args.parts} ---")
        config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        clip_file = config.TEMP_DIR / f"movie_part{part}.mp4"

        tmdb_id    = None
        srt_path   = None
        clip_start = None

        for attempt in range(10):
            tmdb_id    = random.choice(list(MOVIES.keys()))
            url        = movie_url(tmdb_id)
            clip_start = random.randint(600, 4800)   # 10–80 min in
            print(f"  Movie: {MOVIES[tmdb_id]} (TMDB {tmdb_id})  offset {clip_start}s")
            try:
                srt_path = download_segment(url, clip_file, start=clip_start, duration=args.duration)
                break
            except Exception as e:
                if attempt == 9:
                    raise
                print(f"  Failed ({e}), retrying with different movie...")

        slug = re.sub(r"[^a-z0-9]+", "_", MOVIES[tmdb_id].lower()).strip("_")
        out  = config.OUTPUT_DIR / f"movie_{slug}_p{part}_{timestamp}.mp4"
        compose(clip_file, out, clip_start=float(clip_start),
                duration=float(args.duration), srt_path=srt_path)
        print()

    print(f"All {args.parts} parts saved to {config.OUTPUT_DIR}/")


def cmd_montage(args):
    import time
    from imprimante_argent.montage import compose
    music_path = Path(args.music_path) if args.music_path else None
    out = config.OUTPUT_DIR / f"montage_{int(time.time())}.mp4"
    compose(out, every_n_beats=args.every_n_beats, music_path=music_path)


def cmd_stocks(args):
    from imprimante_argent.stocks import run_dca, run_comparison

    if args.stock_cmd == "dca":
        run_dca(args.ticker, args.name, args.year, args.monthly, args.vid_duration)
    elif args.stock_cmd == "compare":
        names = args.names if args.names else args.tickers
        if len(names) != len(args.tickers):
            sys.exit("--names must have the same number of entries as tickers")
        run_comparison(args.tickers, dict(zip(args.tickers, names)),
                       args.year, args.investment, args.vid_duration)


def main():
    p = argparse.ArgumentParser(prog="main.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- reddit ---
    r = sub.add_parser("reddit", help="Generate a Reddit story video")
    r.add_argument("subreddit", nargs="?", default=None)

    # --- familyguy ---
    fg = sub.add_parser("familyguy", help="Generate split-screen Family Guy TikTok parts")
    fg.add_argument("--parts",    type=int, default=3,   help="Number of parts (default: 3)")
    fg.add_argument("--duration", type=int, default=120, help="Seconds per part (default: 120)")

    # --- rwj ---
    rw = sub.add_parser("rwj", help="Ray William Johnson 4-panel split-screen parts")
    rw.add_argument("--video",    default=None, help="Path to TikTok video (default: random from assets/rwj/)")
    rw.add_argument("--parts",    type=int, default=2,  help="Number of parts (default: 2)")
    rw.add_argument("--duration", type=int, default=60, help="Seconds per part (default: 60)")
    rw.add_argument("--title",    default=None, help='Story title (default: auto-generated from video transcript)')
    rw.add_argument("--use-base", action="store_true", help="Use base.mp4 for bottom-left instead of GTA")

    # --- brat ---
    br = sub.add_parser("brat", help="BRAT-style lyric video using bratAnimator")
    br.add_argument("music_path", help="Path to music file (MP3, WAV, etc.)")
    br.add_argument("--model", default="base", help="Whisper model size (default: base)")
    br.add_argument("--artist", default="", help="Artist name to improve LRCLIB search")
    br.add_argument("--watermark", default="@geldmaker", help="Text shown during silence (default: @geldmaker)")
    br.add_argument("--whisper", action="store_true", help="Skip LRCLIB and use Whisper directly")

    # --- movies ---
    mv = sub.add_parser("movies", help="Portrait movie clip with burned-in subtitles")
    mv.add_argument("--parts",    type=int, default=1,  help="Number of clips (default: 1)")
    mv.add_argument("--duration", type=int, default=60, help="Seconds per clip (default: 60)")

    # --- montage ---
    mo = sub.add_parser("montage", help="Luxury lifestyle montage with beat-synced cuts")
    mo.add_argument("--every-n-beats", type=int, default=2,
                    help="Cut every N beats (default: 2 = ~1s cuts at 120BPM)")
    mo.add_argument("--music-path", default=None,
                    help="Path to specific music file (default: random from money playlist)")

    # --- stocks ---
    st = sub.add_parser("stocks", help="Generate a stock investment video")
    st_sub = st.add_subparsers(dest="stock_cmd", required=True)

    dca = st_sub.add_parser("dca", help="Monthly DCA chart")
    dca.add_argument("ticker")
    dca.add_argument("name")
    dca.add_argument("year", type=int)
    dca.add_argument("--monthly",      type=float, default=100.0)
    dca.add_argument("--vid-duration", type=float, default=90.0)

    cmp = st_sub.add_parser("compare", help="Multi-stock comparison chart")
    cmp.add_argument("tickers", nargs="+")
    cmp.add_argument("--names",        nargs="+")
    cmp.add_argument("--year",         type=int,   required=True)
    cmp.add_argument("--investment",   type=float, default=1000.0)
    cmp.add_argument("--vid-duration", type=float, default=90.0)

    args = p.parse_args()

    if args.cmd == "brat":
        cmd_brat(args)
    elif args.cmd == "movies":
        cmd_movies(args)
    elif args.cmd == "rwj":
        cmd_rwj(args)
    elif args.cmd == "montage":
        cmd_montage(args)
    elif args.cmd == "reddit":
        cmd_reddit(args)
    elif args.cmd == "familyguy":
        cmd_familyguy(args)
    elif args.cmd == "stocks":
        cmd_stocks(args)


if __name__ == "__main__":
    main()
