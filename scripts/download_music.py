"""Download songs from a playlist file to assets/music/ as MP3 via yt-dlp.

Line formats supported:
  Blue Bands                              → search "Blue Bands"
  VYZEE-https://youtube.com/watch?v=...  → download that URL directly
  1. Blue Bands                           → numbered list, search
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT      = Path(__file__).resolve().parents[1]
MUSIC_DIRS = {
    "playlist.txt":      ROOT / "assets" / "music" / "sigma",
    "moneyplaylist.txt": ROOT / "assets" / "music" / "money",
}

URL_RE = re.compile(r"https?://\S+")


def parse_entries(path: Path) -> list[tuple[str, str]]:
    """Return list of (label, url_or_search_query)."""
    entries = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("=") or line.startswith("-"):
            continue
        # Strip leading "1." numbering
        line = re.sub(r"^\d+\.\s*", "", line)
        url_match = URL_RE.search(line)
        if url_match:
            url   = url_match.group()
            label = line[:url_match.start()].strip().rstrip("-").strip() or url
            entries.append((label, url))
        else:
            entries.append((line, f"ytsearch1:{line}"))
    return entries



def main():
    if len(sys.argv) < 2:
        print("Usage: python download_music.py <playlist.txt>")
        print("       python download_music.py scripts/moneyplaylist.txt")
        sys.exit(1)

    playlist = Path(sys.argv[1])
    if not playlist.exists():
        playlist = ROOT / sys.argv[1]
    if not playlist.exists():
        sys.exit(f"Playlist not found: {sys.argv[1]}")

    music_dir = MUSIC_DIRS.get(playlist.name, ROOT / "assets" / "music" / "sigma")
    music_dir.mkdir(parents=True, exist_ok=True)
    entries = parse_entries(playlist)
    print(f"Downloading {len(entries)} tracks to {music_dir}\n")

    failed = []
    for i, (label, query) in enumerate(entries, 1):
        print(f"[{i}/{len(entries)}] {label}")
        try:
            subprocess.run([
                "yt-dlp", query,
                "-x", "--audio-format", "mp3", "--audio-quality", "0",
                "-o", str(music_dir / "%(title)s.%(ext)s"),
                "--no-playlist", "--progress",
            ], check=True)
        except subprocess.CalledProcessError:
            print(f"  ⚠  Failed: {label}")
            failed.append(label)

    mp3s = list(music_dir.glob("*.mp3"))
    print(f"\nDone - {len(mp3s)} files in {music_dir}")
    if failed:
        print("Failed:", ", ".join(failed))


if __name__ == "__main__":
    main()
