import httpx
import click
from pathlib import Path
from typing import Protocol
from .config import Config

class TTSProvider(Protocol):
    async def synthesize(self, text: str, voice: str, output_path: Path) -> Path: ...

class OpenAITTS:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def synthesize(self, text: str, voice: str, output_path: Path) -> Path:
        import os
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{base_url}/audio/speech",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": "tts-1", "input": text, "voice": voice},
                timeout=30.0
            )
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
            return output_path

class ElevenLabsTTS:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def synthesize(self, text: str, voice: str, output_path: Path) -> Path:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                headers={"xi-api-key": self.api_key},
                json={"text": text, "model_id": "eleven_multilingual_v2"},
                timeout=30.0
            )
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
            return output_path

class GeminiTTS:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    async def synthesize(self, text: str, voice: str, output_path: Path) -> Path:
        raise NotImplementedError("Gemini TTS requires custom base64 decode. Add when requested.")

def get_tts_provider(config: Config) -> TTSProvider:
    key = config.tts_api_key
    if not key:
        import os
        key = os.getenv("OPENAI_API_KEY") if config.tts_provider == "openai" else os.getenv("ELEVENLABS_API_KEY")
    if not key:
        raise click.UsageError(f"API key missing for TTS provider {config.tts_provider}")
        
    if config.tts_provider == "openai":
        return OpenAITTS(key)
    elif config.tts_provider == "elevenlabs":
        return ElevenLabsTTS(key)
    elif config.tts_provider == "gemini":
        return GeminiTTS(key)
    raise click.UsageError(f"Unknown TTS provider {config.tts_provider}")
