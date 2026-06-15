"""
Regenerate all video types, upload each to catbox.moe, print links.
Files are kept in output/ after upload.
"""
import subprocess
import sys
import requests
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
PYTHON = sys.executable


def run(label, *cmd):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    subprocess.run([PYTHON, str(ROOT / "main.py"), *cmd], check=True, cwd=ROOT)


def upload(path: Path) -> str:
    print(f"  Uploading {path.name} ({path.stat().st_size // 1024 // 1024}MB) to catbox.moe...")
    with open(path, "rb") as f:
        r = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (path.name, f, "video/mp4")},
            timeout=600,
        )
    r.raise_for_status()
    url = r.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"Unexpected catbox response: {url}")
    print(f"  -> {url}")
    return url


def latest(pattern="*.mp4") -> Path:
    files = sorted(OUTPUT.glob(pattern), key=lambda f: f.stat().st_mtime)
    return files[-1] if files else None


links = {}

# ── Stocks – AAPL DCA ───────────────────────────────────────────────────────
run("Stocks: AAPL DCA since 2015", "stocks", "dca", "AAPL", "Apple", "2015")
links["AAPL DCA"] = upload(latest())

# ── Montage ──────────────────────────────────────────────────────────────────
run("Montage", "montage")
links["Montage"] = upload(latest())

# ── Family Guy (1 part, 60s) ─────────────────────────────────────────────────
run("Family Guy", "familyguy", "--parts", "1", "--duration", "60")
links["Family Guy"] = upload(latest())

# ── Brat – Notti Bop ─────────────────────────────────────────────────────────
run("Brat – Notti Bop", "brat", str(ROOT / "assets/music/notti_bop.mp3"),
    "--artist", "Kyle Richh", "--watermark", "@geldmaker")
links["Brat"] = upload(latest())

# ── RWJ (1 part, 60s) ────────────────────────────────────────────────────────
run("RWJ", "rwj", "--parts", "1", "--duration", "60")
links["RWJ"] = upload(latest())

# ── Results ──────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  DONE — Video links")
print("="*60)
for name, url in links.items():
    print(f"  {name:15s}  {url}")
