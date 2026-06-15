from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
ASSETS_DIR = ROOT_DIR / "assets"

BASE_VIDEO = ASSETS_DIR / "base.mp4"
TITLECARD_IMAGE = ASSETS_DIR / "title_card.png"
FONTS_DIR = ASSETS_DIR / "fonts"
FONT_BOLD = FONTS_DIR / "Montserrat-Bold.ttf"
FONT_EMOJI = Path("C:/Windows/Fonts/seguiemj.ttf")

OUTPUT_DIR   = ROOT_DIR / "output"
TEMP_DIR     = ROOT_DIR / "temp"
MUSIC_DIR        = ASSETS_DIR / "music" / "sigma"
MONEY_MUSIC_DIR  = ASSETS_DIR / "music" / "money"
LIFESTYLE_DIR    = ASSETS_DIR / "lifestyle"
EPISODES_DIR = ASSETS_DIR / "episodes"
GAMEPLAY_DIR = ASSETS_DIR / "gameplay"

TTS_VOICE = "en-US-AriaNeural"
WHISPER_MODEL = "base"
TITLECARD_AUTHOR = "Requestedreads"
TITLECARD_DURATION = 4.0
