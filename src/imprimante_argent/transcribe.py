from faster_whisper import WhisperModel

from . import config

_model = None


def _get_model():
    global _model
    if _model is None:
        print(f"  Loading Whisper model '{config.WHISPER_MODEL}'...")
        _model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def get_word_timestamps(audio_path):
    model = _get_model()
    segments, _ = model.transcribe(audio_path, word_timestamps=True)
    words = []
    for segment in segments:
        for word in segment.words:
            words.append({
                "word": word.word.strip(),
                "start": word.start,
                "end": word.end,
            })
    return words
