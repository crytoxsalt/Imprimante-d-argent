"""
Transcribe a video with faster-whisper, then generate a title locally
using google/flan-t5-base (no API key, runs on CPU, free).
"""
import subprocess
import tempfile
from pathlib import Path


def _extract_audio(video_path: Path, out_wav: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-ac", "1", "-ar", "16000",
         "-vn", str(out_wav)],
        check=True, capture_output=True,
    )


def transcribe(video_path: Path, model_size: str = "base") -> str:
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav = Path(f.name)

    try:
        _extract_audio(video_path, wav)
        segments, _ = model.transcribe(str(wav), beam_size=1)
        return " ".join(s.text.strip() for s in segments)
    finally:
        wav.unlink(missing_ok=True)


def generate_title(transcript: str) -> str:
    from transformers import T5Tokenizer, T5ForConditionalGeneration

    prompt = "summarize: " + transcript[:600]

    tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
    model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-base")
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=40, num_beams=4)
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    # Take first 5 words of the summary as the title
    words = summary.split()
    title = " ".join(words[:5]).rstrip(".,;:!?")
    return title


def title_from_video(video_path: Path, model_size: str = "base") -> str:
    print("Transcribing video...")
    transcript = transcribe(video_path, model_size)
    print(f"Transcript ({len(transcript)} chars): {transcript[:120]}...")
    print("Generating title (flan-t5-base, local)...")
    title = generate_title(transcript)
    print(f"Generated title: {title}")
    return title
