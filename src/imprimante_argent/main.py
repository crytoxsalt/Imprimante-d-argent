import shutil

from . import config
from .captions import generate_ass
from .preprocess import preprocess
from .reddit import get_story
from .titlecard import apply_title_to_card
from .transcribe import get_word_timestamps
from .tts import generate_tts
from .video import compose


def run(subreddit=None):
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching Reddit story...")
    story = get_story(subreddit)
    print(f"  r/{story['subreddit']}: {story['title'][:70]}...")

    post_id = story["id"]
    audio_path = config.TEMP_DIR / "audio.mp3"
    ass_path = config.TEMP_DIR / "captions.ass"
    card_path = config.TEMP_DIR / "titlecard.png"
    output_path = config.OUTPUT_DIR / f"{post_id}.mp4"

    try:
        print("Building title card...")
        apply_title_to_card(story["title"], config.TITLECARD_IMAGE, card_path)

        print("Generating TTS audio...")
        generate_tts(preprocess(story["text"]), audio_path)

        print("Transcribing for word timestamps (Whisper)...")
        words = get_word_timestamps(audio_path)
        print(f"  {len(words)} words timestamped")

        print("Building captions (.ass)...")
        generate_ass(words, ass_path)

        print("Composing final video...")
        compose(
            config.BASE_VIDEO,
            audio_path,
            ass_path,
            output_path,
            titlecard_path=card_path,
            titlecard_duration=config.TITLECARD_DURATION,
        )
    finally:
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)

    print(f"\nDone -> {output_path}")
    return output_path
