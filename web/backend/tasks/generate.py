"""
Celery tasks that wrap the existing Cashroll pipeline functions.
Each task isolates TEMP_DIR per run to prevent concurrent job collisions.
"""
import sys
import tempfile
import shutil
import traceback
from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add repo src to path so existing pipelines can be imported
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from .celery_app import celery
from ..config import settings

# Sync engine for Celery tasks (Celery workers are sync)
_engine = create_engine(settings.database_url_sync)
_Session = sessionmaker(bind=_engine)


def _update_job(job_id: str, **kwargs):
    with _Session() as session:
        from ..models import Job
        job = session.get(Job, job_id)
        if job:
            for k, v in kwargs.items():
                setattr(job, k, v)
            session.commit()


def _log(job_id: str, line: str):
    """Append a log line to Redis list for SSE streaming."""
    import redis
    r = redis.from_url(settings.redis_url)
    r.rpush(f"job_logs:{job_id}", line)
    r.ltrim(f"job_logs:{job_id}", -1000, -1)  # keep last 1000 lines


def _run_pipeline(job_id: str, fn, *args, **kwargs):
    """Common wrapper: sets status, runs fn, handles errors."""
    import imprimante_argent.config as cfg

    _update_job(job_id, status="running")
    _log(job_id, "Job started")

    tmp = tempfile.mkdtemp()
    cfg.TEMP_DIR = Path(tmp)
    cfg.OUTPUT_DIR = Path(settings.output_dir)
    cfg.ASSETS_DIR = Path(settings.assets_dir)
    cfg.BASE_VIDEO = cfg.ASSETS_DIR / "base.mp4"
    cfg.TITLECARD_IMAGE = cfg.ASSETS_DIR / "title_card.png"
    cfg.FONTS_DIR = cfg.ASSETS_DIR / "fonts"
    cfg.FONT_BOLD = cfg.FONTS_DIR / "Montserrat-Bold.ttf"
    cfg.MUSIC_DIR = cfg.ASSETS_DIR / "music" / "sigma"
    cfg.MONEY_MUSIC_DIR = cfg.ASSETS_DIR / "music" / "money"
    cfg.LIFESTYLE_DIR = cfg.ASSETS_DIR / "lifestyle"
    cfg.EPISODES_DIR = cfg.ASSETS_DIR / "episodes"
    cfg.GAMEPLAY_DIR = cfg.ASSETS_DIR / "gameplay"
    cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        output = fn(*args, **kwargs)
        output_path = str(output) if output else None
        _log(job_id, f"Done -> {output_path}")
        _update_job(job_id, status="done", output_path=output_path, completed_at=datetime.utcnow())
        return output_path
    except Exception:
        err = traceback.format_exc()
        _log(job_id, f"FAILED:\n{err}")
        _update_job(job_id, status="failed", error=err, completed_at=datetime.utcnow())
        raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@celery.task(name="web.backend.tasks.generate.reddit", bind=True)
def task_reddit(self, job_id: str, params: dict):
    from imprimante_argent.main import run
    _run_pipeline(job_id, run, subreddit=params.get("subreddit"))


@celery.task(name="web.backend.tasks.generate.brat", bind=True)
def task_brat(self, job_id: str, params: dict):
    from imprimante_argent.brat import run
    music_path = Path(params["music_path"])
    output_path = Path(settings.output_dir) / f"brat_{job_id[:8]}.mp4"
    _run_pipeline(
        job_id, run,
        music_path=music_path,
        output_path=output_path,
        model_size=params.get("model_size", "base"),
        artist=params.get("artist", ""),
        watermark=params.get("watermark", "@cashroll"),
    )


@celery.task(name="web.backend.tasks.generate.montage", bind=True)
def task_montage(self, job_id: str, params: dict):
    from imprimante_argent.montage import compose
    output_path = Path(settings.output_dir) / f"montage_{job_id[:8]}.mp4"
    music_path = Path(params["music_path"]) if params.get("music_path") else None
    _run_pipeline(
        job_id, compose,
        output_path,
        every_n_beats=params.get("every_n_beats", 2),
        music_path=music_path,
    )


@celery.task(name="web.backend.tasks.generate.stocks_dca", bind=True)
def task_stocks_dca(self, job_id: str, params: dict):
    from imprimante_argent.stocks import run_dca
    _run_pipeline(
        job_id, run_dca,
        params["ticker"],
        params["name"],
        int(params["year"]),
        monthly=float(params.get("monthly", 100.0)),
        vid_duration=float(params.get("vid_duration", 90.0)),
    )


@celery.task(name="web.backend.tasks.generate.stocks_compare", bind=True)
def task_stocks_compare(self, job_id: str, params: dict):
    from imprimante_argent.stocks import run_comparison
    tickers = params["tickers"]
    names = params.get("names", tickers)
    _run_pipeline(
        job_id, run_comparison,
        tickers,
        dict(zip(tickers, names)),
        int(params["year"]),
        investment=float(params.get("investment", 1000.0)),
        vid_duration=float(params.get("vid_duration", 90.0)),
    )


@celery.task(name="web.backend.tasks.generate.familyguy", bind=True)
def task_familyguy(self, job_id: str, params: dict):
    import random, time
    from imprimante_argent.fgdownload import download_segment, episode_url
    from imprimante_argent.splitscreen import compose
    import imprimante_argent.config as cfg

    _update_job(job_id, status="running")
    tmp = tempfile.mkdtemp()
    cfg.TEMP_DIR = Path(tmp)
    cfg.OUTPUT_DIR = Path(settings.output_dir)
    cfg.ASSETS_DIR = Path(settings.assets_dir)
    cfg.GAMEPLAY_DIR = cfg.ASSETS_DIR / "gameplay"
    cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        SEASONS = {4: 30, 5: 18, 6: 12, 7: 16, 8: 21}
        SKIP_INTRO, SKIP_OUTRO = 60, 120
        parts = int(params.get("parts", 3))
        duration = int(params.get("duration", 120))
        gameplay_clips = list(cfg.GAMEPLAY_DIR.glob("*.mp4"))

        season = random.choice(list(SEASONS.keys()))
        episode = random.randint(1, SEASONS[season])
        url = episode_url(season, episode)
        total = duration * parts
        max_start = max(SKIP_INTRO, 1320 - SKIP_OUTRO - total)
        seg_start = random.randint(SKIP_INTRO, max_start)
        timestamp = int(time.time())
        outputs = []

        for part in range(1, parts + 1):
            part_start = seg_start + (part - 1) * duration
            tv_clip = cfg.TEMP_DIR / f"fg_part{part}.mp4"
            srt_path = None
            for attempt in range(10):
                try:
                    srt_path = download_segment(url, tv_clip, start=part_start, duration=duration)
                    break
                except Exception:
                    if attempt == 9:
                        raise
                    season = random.choice(list(SEASONS.keys()))
                    episode = random.randint(1, SEASONS[season])
                    url = episode_url(season, episode)
                    seg_start = random.randint(SKIP_INTRO, max_start)
                    part_start = seg_start + (part - 1) * duration
            gameplay = random.choice(gameplay_clips) if gameplay_clips else None
            out = cfg.OUTPUT_DIR / f"fg_s{season:02d}e{episode:02d}_p{part}_{timestamp}.mp4"
            compose(tv_clip, gameplay, out, min_dur=float(duration), max_dur=float(duration),
                    part_label=f"Part {part}", srt_path=srt_path)
            outputs.append(str(out))
            _log(job_id, f"Part {part}/{parts} done -> {out}")

        _update_job(job_id, status="done", output_path=",".join(outputs), completed_at=datetime.utcnow())
        return outputs
    except Exception:
        err = traceback.format_exc()
        _update_job(job_id, status="failed", error=err, completed_at=datetime.utcnow())
        raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@celery.task(name="web.backend.tasks.generate.movies", bind=True)
def task_movies(self, job_id: str, params: dict):
    import random, re, time
    from imprimante_argent.fgdownload import movie_url, download_segment
    from imprimante_argent.movieclip import compose
    import imprimante_argent.config as cfg

    _update_job(job_id, status="running")
    tmp = tempfile.mkdtemp()
    cfg.TEMP_DIR = Path(tmp)
    cfg.OUTPUT_DIR = Path(settings.output_dir)
    cfg.ASSETS_DIR = Path(settings.assets_dir)
    cfg.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    MOVIES = {
        550: "Fight Club", 278: "The Shawshank Redemption", 680: "Pulp Fiction",
        155: "The Dark Knight", 27205: "Inception", 157336: "Interstellar",
        13: "Forrest Gump", 603: "The Matrix", 769: "Goodfellas",
        475557: "Joker", 496243: "Parasite",
    }

    try:
        parts = int(params.get("parts", 1))
        duration = int(params.get("duration", 60))
        timestamp = int(time.time())
        outputs = []

        for part in range(1, parts + 1):
            clip_file = cfg.TEMP_DIR / f"movie_part{part}.mp4"
            tmdb_id = srt_path = clip_start = None
            for attempt in range(10):
                tmdb_id = random.choice(list(MOVIES.keys()))
                url = movie_url(tmdb_id)
                clip_start = random.randint(600, 4800)
                try:
                    srt_path = download_segment(url, clip_file, start=clip_start, duration=duration)
                    break
                except Exception:
                    if attempt == 9:
                        raise
            slug = re.sub(r"[^a-z0-9]+", "_", MOVIES[tmdb_id].lower()).strip("_")
            out = cfg.OUTPUT_DIR / f"movie_{slug}_p{part}_{timestamp}.mp4"
            compose(clip_file, out, clip_start=float(clip_start), duration=float(duration), srt_path=srt_path)
            outputs.append(str(out))
            _log(job_id, f"Part {part}/{parts} done -> {out}")

        _update_job(job_id, status="done", output_path=",".join(outputs), completed_at=datetime.utcnow())
        return outputs
    except Exception:
        err = traceback.format_exc()
        _update_job(job_id, status="failed", error=err, completed_at=datetime.utcnow())
        raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
