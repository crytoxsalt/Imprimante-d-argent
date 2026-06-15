"""Download a random video from a TikTok account using yt-dlp.

Usage:
  python scripts/pull_tiktok.py                        # random from @realraywilliam
  python scripts/pull_tiktok.py --user otheraccount
  python scripts/pull_tiktok.py --out assets/gameplay
"""
import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USER = "realraywilliam"
DEFAULT_OUT  = ROOT / "assets" / "rwj"


def fetch_video_list(user, limit=50):
    print(f"Fetching video list from @{user} (up to {limit})...", flush=True)
    result = subprocess.run([
        "yt-dlp",
        "--flat-playlist",
        "--playlist-end", str(limit),
        "-J",
        "--no-warnings",
        f"https://www.tiktok.com/@{user}",
    ], capture_output=True, text=True)

    if result.returncode != 0:
        sys.exit(f"yt-dlp error:\n{result.stderr}")

    data = json.loads(result.stdout)
    entries = data.get("entries") or []
    if not entries:
        sys.exit("No videos found — account may be private or yt-dlp needs cookies.")
    return entries


def download(entry, out_dir: Path):
    url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
    title = entry.get("title", entry.get("id", "?"))
    safe_title = title.encode("cp1252", errors="replace").decode("cp1252")
    print(f"\nSelected: {safe_title}")
    print(f"URL:      {url}\n")

    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "yt-dlp", url,
        "-o", str(out_dir / "%(uploader)s_%(id)s.%(ext)s"),
        "--no-playlist",
    ], check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--user",  default=DEFAULT_USER, help="TikTok username (no @)")
    p.add_argument("--out",   default=str(DEFAULT_OUT), help="Output directory")
    p.add_argument("--limit", type=int, default=50, help="How many videos to sample from (default 50)")
    args = p.parse_args()

    entries = fetch_video_list(args.user, args.limit)
    print(f"Found {len(entries)} videos, picking one at random...")
    download(random.choice(entries), Path(args.out))


if __name__ == "__main__":
    main()
