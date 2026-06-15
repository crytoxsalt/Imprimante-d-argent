"""
VidVault episode downloader — based on vidvault+subtitles.py.
Exposes download_segment() for the Family Guy pipeline.
"""
import re
import subprocess
from pathlib import Path
from urllib.parse import quote, urlparse

import requests

API_BASE       = "https://vidvault.ru/api"
PRIMARY_PROXY  = "https://dl.gemlelispe.workers.dev"
FALLBACK_PROXY = "https://vlaq11.site"
TMDB_ID        = 1434   # Family Guy
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/149.0.0.0 Safari/537.36"
)


def log(msg):
    print(str(msg).encode("ascii", errors="replace").decode("ascii"), flush=True)


def episode_url(season: int, episode: int) -> str:
    return f"https://vidvault.ru/tv/{TMDB_ID}/{season}/{episode}"


def movie_url(tmdb_id: int) -> str:
    return f"https://vidvault.ru/movie/{tmdb_id}"


def _parse_url(url: str) -> dict:
    path = urlparse(url).path.strip("/")
    tv = re.fullmatch(r"tv/(\d+)/(\d+)/(\d+)", path)
    if tv:
        tmdb_id, season, ep = tv.groups()
        return {"type": "tv", "tmdbId": int(tmdb_id), "season": int(season), "episode": int(ep)}
    mov = re.fullmatch(r"movie/(\d+)", path)
    if mov:
        return {"type": "movie", "tmdbId": int(mov.group(1))}
    raise ValueError(f"Expected https://vidvault.ru/tv/1434/1/1 or https://vidvault.ru/movie/550")


def _get_media(page_url: str) -> dict:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Referer":    page_url,
        "Origin":     "https://vidvault.ru",
    })

    log("[1/4] Getting VidVault token...")
    r = session.get(f"{API_BASE}/get-token", timeout=30)
    r.raise_for_status()
    data  = r.json()
    token = data.get("token") or data.get("t")
    if not token:
        raise RuntimeError(f"No token in response: {data}")

    log("[2/4] Requesting download links...")
    r = session.post(
        f"{API_BASE}/download-proxy",
        headers={"x-request-token": token},
        json=_parse_url(page_url),
        timeout=30,
    )
    r.raise_for_status()
    body          = r.json() or {}
    mp4_data      = body.get("mp4Data", {})
    download_data = mp4_data.get("downloadInfo", {}).get("data", {})
    downloads     = [d for d in download_data.get("downloads", [])
                     if d.get("format") == "MP4" and d.get("url")]
    if not downloads:
        raise RuntimeError(f"VidVault returned no MP4 downloads for {page_url}")

    captions = download_data.get("captions") or mp4_data.get("captions") or []
    captions = [c for c in captions if c.get("lan") and c.get("url")]

    return {
        "downloads": sorted(downloads, key=lambda d: int(d.get("resolution", 0))),
        "captions":  captions,
    }


def _pick(downloads: list, resolution: str = "best") -> dict:
    if resolution == "best":
        return downloads[-1]
    wanted = int(resolution)
    exact  = [d for d in downloads if int(d.get("resolution", 0)) == wanted]
    if exact:
        return exact[0]
    available = ", ".join(str(d.get("resolution")) for d in downloads)
    raise ValueError(f"Resolution {wanted} not available. Options: {available}")


def _proxied(raw_url: str, name: str, proxy: str = PRIMARY_PROXY) -> str:
    return f"{proxy}/{quote(raw_url, safe='')}?n={quote(name, safe='')}"


def _proxy_works(url: str, referer: str) -> bool:
    r = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Referer": referer, "Range": "bytes=0-0"},
        stream=True, timeout=30,
    )
    r.close()
    return r.status_code == 206


def _ffmpeg(input_url: str, output_path: Path, referer: str,
            start: int = 0, duration: int = None) -> None:
    cmd = ["ffmpeg", "-y"]
    if duration:
        cmd += ["-ss", str(start), "-t", str(duration)]
    cmd += [
        "-headers", f"Referer: {referer}\r\nUser-Agent: {USER_AGENT}\r\n",
        "-i", input_url,
        "-c", "copy",
        str(output_path),
    ]
    log("[4/4] Downloading via ffmpeg...")
    subprocess.run(cmd, check=True)


def _download_caption(caption: dict, out_path: Path, referer: str) -> Path:
    """Download a single caption track as an SRT file."""
    lan  = re.sub(r"[^A-Za-z0-9._-]+", "_", caption.get("lan", "sub")).strip("._") or "sub"
    dest = out_path.with_suffix(f".{lan}.srt")
    r = requests.get(
        caption["url"],
        headers={"User-Agent": USER_AGENT, "Referer": referer},
        timeout=60,
    )
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


def download_segment(page_url: str, out_path: Path,
                     start: int = 0, duration: int = None,
                     resolution: str = "best") -> "Path | None":
    """
    Download a segment of a VidVault episode to out_path.
    Returns the English SRT caption path if available, else None.
    """
    media     = _get_media(page_url)
    downloads = media["downloads"]
    captions  = media["captions"]

    log("[3/4] Available qualities:")
    for d in downloads:
        size = int(d.get("size", 0))
        log(f"      {d.get('resolution')}p  {size/1024/1024:.1f} MB  "
            f"duration={d.get('duration')}s")

    selected = _pick(downloads, resolution)
    name     = Path(out_path).stem
    url      = _proxied(selected["url"], name)

    if not _proxy_works(url, page_url):
        log("      Primary proxy failed, trying fallback...")
        url = _proxied(selected["url"], name, FALLBACK_PROXY)
        if not _proxy_works(url, page_url):
            raise RuntimeError("Both proxies rejected the range test.")

    _ffmpeg(url, out_path, page_url, start=start, duration=duration)

    # Download English captions (or first available language)
    srt_path = None
    en_caps  = [c for c in captions if c.get("lan", "").lower() == "en"] or captions[:1]
    if en_caps:
        try:
            srt_path = _download_caption(en_caps[0], out_path, page_url)
            log(f"      Caption: {srt_path.name}")
        except Exception as e:
            log(f"      Caption download failed: {e}")

    return srt_path
