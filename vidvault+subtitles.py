import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

import requests


API_BASE = "https://vidvault.ru/api"
PRIMARY_PROXY = "https://dl.gemlelispe.workers.dev"
FALLBACK_PROXY = "https://vlaq11.site"
DEFAULT_URL = "https://vidvault.ru/tv/1434/1/1"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/149.0.0.0 Safari/537.36"
)


def log(message):
    print(str(message).encode("ascii", errors="replace").decode("ascii"), flush=True)


def parse_vidvault_url(url):
    path = urlparse(url).path.strip("/")
    match = re.fullmatch(r"tv/(\d+)/(\d+)/(\d+)", path)
    if not match:
        raise ValueError("Expected a VidVault TV URL like https://vidvault.ru/tv/1434/1/1")

    tmdb_id, season, episode = match.groups()
    return {
        "type": "tv",
        "tmdbId": int(tmdb_id),
        "season": int(season),
        "episode": int(episode),
    }


def get_media(page_url):
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Referer": page_url,
            "Origin": "https://vidvault.ru",
        }
    )

    log("[1/4] Getting VidVault request token...")
    token_response = session.get(f"{API_BASE}/get-token", timeout=30)
    token_response.raise_for_status()
    token_data = token_response.json()
    token = token_data.get("token") or token_data.get("t")
    if not token:
        raise RuntimeError(f"Token response did not include a token: {token_data}")
    log(f"      token: {token[:12]}... ({len(token)} chars)")

    payload = parse_vidvault_url(page_url)
    log("[2/4] Requesting download links...")
    links_response = session.post(
        f"{API_BASE}/download-proxy",
        headers={"x-request-token": token},
        json=payload,
        timeout=30,
    )
    links_response.raise_for_status()
    data = links_response.json()

    mp4_data = data.get("mp4Data", {})
    download_data = mp4_data.get("downloadInfo", {}).get("data", {})
    downloads = download_data.get("downloads", [])
    downloads = [item for item in downloads if item.get("format") == "MP4" and item.get("url")]
    if not downloads:
        raise RuntimeError("VidVault did not return any MP4 downloads.")

    captions = download_data.get("captions") or mp4_data.get("captions") or []
    captions = [item for item in captions if item.get("lan") and item.get("url")]

    return {
        "downloads": sorted(downloads, key=lambda item: int(item.get("resolution", 0))),
        "captions": captions,
    }


def pick_download(downloads, resolution):
    if resolution == "best":
        return downloads[-1]

    wanted = int(resolution)
    exact = [item for item in downloads if int(item.get("resolution", 0)) == wanted]
    if exact:
        return exact[0]

    available = ", ".join(str(item.get("resolution")) for item in downloads)
    raise ValueError(f"Resolution {wanted} not found. Available: {available}")


def pick_captions(captions, subtitle):
    if subtitle == "none":
        return []
    if not captions:
        return []
    if subtitle == "all":
        return captions

    exact = [item for item in captions if item.get("lan", "").lower() == subtitle.lower()]
    if exact:
        return exact

    english = [item for item in captions if item.get("lan", "").lower() == "en"]
    if subtitle == "en" and english:
        return english

    available = ", ".join(sorted({item.get("lan", "?") for item in captions}))
    raise ValueError(f"Subtitle language '{subtitle}' not found. Available: {available}")


def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return value or "subtitle"


def download_caption(caption, output_stem, referer):
    lan = safe_name(caption.get("lan", "sub"))
    subtitle_path = Path(f"{output_stem}.{lan}.srt")
    response = requests.get(
        caption["url"],
        headers={
            "User-Agent": USER_AGENT,
            "Referer": referer,
        },
        timeout=60,
    )
    response.raise_for_status()
    subtitle_path.write_bytes(response.content)
    return subtitle_path


def proxied_url(raw_url, name, proxy_base=PRIMARY_PROXY):
    encoded = quote(raw_url, safe="")
    encoded_name = quote(name, safe="")
    return f"{proxy_base}/{encoded}?n={encoded_name}"


def proxy_works(url, referer):
    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": referer,
            "Range": "bytes=0-0",
        },
        stream=True,
        timeout=30,
    )
    response.close()
    return response.status_code == 206


def run_ffmpeg(input_url, output_path, referer, sample_seconds=None):
    command = [
        "ffmpeg",
        "-y",
    ]
    if sample_seconds:
        command.extend(["-ss", "0", "-t", str(sample_seconds)])
    command.extend(
        [
            "-headers",
            f"Referer: {referer}\r\nUser-Agent: {USER_AGENT}\r\n",
            "-i",
            input_url,
            "-c",
            "copy",
            str(output_path),
        ]
    )

    log("[4/4] Running ffmpeg...")
    log("      " + " ".join(command[:6]) + " ...")
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Download an authorized VidVault TV episode MP4 and separate SRT subtitles."
    )
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="VidVault TV episode URL.")
    parser.add_argument(
        "-r",
        "--resolution",
        default="best",
        help="Resolution to download, for example 360, 480, 720, 1080, or best.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output MP4 path. Defaults to vidvault_<resolution>.mp4.",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Only save the first N seconds, for example --sample 60.",
    )
    parser.add_argument(
        "--save-response",
        default=None,
        help="Optional JSON path to save the MP4 download metadata.",
    )
    parser.add_argument(
        "--subtitle",
        default="en",
        help="Subtitle language to download as SRT, for example en, es, all, or none. Defaults to en.",
    )
    parser.add_argument(
        "--subtitles-only",
        action="store_true",
        help="Only download subtitle files. Do not download the MP4.",
    )
    args = parser.parse_args()

    try:
        media = get_media(args.url)
        downloads = media["downloads"]
        captions = media["captions"]
        log("[3/4] MP4 options:")
        for item in downloads:
            size = int(item.get("size", 0))
            log(
                f"      {item.get('resolution')}p "
                f"{size / 1024 / 1024:.1f} MB "
                f"duration={item.get('duration')}s"
            )
        if captions:
            languages = ", ".join(
                f"{item.get('lan')}:{item.get('lanName', item.get('lan'))}" for item in captions
            )
            log(f"      subtitles: {languages}")
        else:
            log("      subtitles: none returned")

        if args.save_response:
            Path(args.save_response).write_text(json.dumps(media, indent=2), encoding="utf-8")

        selected_captions = pick_captions(captions, args.subtitle)
        if args.subtitle != "none" and not selected_captions:
            log("      no matching subtitles returned")

        subtitle_stem = Path(args.output).stem if args.output else "vidvault_subtitles"
        subtitle_paths = []
        for caption in selected_captions:
            log(f"      downloading subtitle {caption.get('lan')} ({caption.get('lanName', '')})...")
            subtitle_paths.append(download_caption(caption, subtitle_stem, args.url))

        if args.subtitles_only:
            if not subtitle_paths:
                raise RuntimeError("No subtitles were downloaded.")
            for subtitle_path in subtitle_paths:
                log(f"Subtitle: {subtitle_path.resolve()}")
            return 0

        selected = pick_download(downloads, args.resolution)
        resolution = selected.get("resolution")
        output = Path(args.output or f"vidvault_{resolution}.mp4")
        if args.sample and args.output is None:
            output = Path(f"vidvault_{resolution}_sample_{args.sample}s.mp4")

        name = output.stem
        input_url = proxied_url(selected["url"], name)
        if not proxy_works(input_url, args.url):
            log("      primary proxy rejected range test; trying fallback proxy...")
            input_url = proxied_url(selected["url"], name, FALLBACK_PROXY)
            if not proxy_works(input_url, args.url):
                raise RuntimeError("Both VidVault proxy URLs rejected the MP4 range test.")

        run_ffmpeg(input_url, output, args.url, args.sample)
        log(f"Done: {output.resolve()}")
        if subtitle_paths:
            for subtitle_path in subtitle_paths:
                log(f"Subtitle: {subtitle_path.resolve()}")
    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
