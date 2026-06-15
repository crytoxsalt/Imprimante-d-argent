import asyncio
import edge_tts

from . import config


async def _generate(text, output_path, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_tts(text, output_path, voice=None):
    asyncio.run(_generate(text, output_path, voice or config.TTS_VOICE))
