import re
from dataclasses import dataclass
from pathlib import Path
import pysubs2
import httpx
import click
from .config import Config

@dataclass
class SubSegment:
    start: float
    end: float
    text: str

def load_subtitles(path_or_name: str, config: Config) -> list[SubSegment]:
    # Path A - File provided
    if Path(path_or_name).exists() and Path(path_or_name).suffix.lower() in [".srt", ".vtt"]:
        subs = pysubs2.load(path_or_name)
        return _parse_pysubs2(subs)
        
    # Path B - Download from OpenSubtitles
    if not config.opensubtitles_api_key:
        raise click.UsageError("Provide --subtitle file or set EDVIDASSIST_OPENSUBTITLES_API_KEY")
        
    if not config.opensubtitles_username or not config.opensubtitles_password:
        raise click.UsageError("OpenSubtitles requires username and password")
        
    client = httpx.Client(headers={"Api-Key": config.opensubtitles_api_key})
    
    # Login
    login_resp = client.post("https://api.opensubtitles.com/api/v1/login", json={
        "username": config.opensubtitles_username,
        "password": config.opensubtitles_password
    })
    if login_resp.status_code != 200:
        raise click.UsageError(f"OpenSubtitles login failed: {login_resp.text}")
    token = login_resp.json()["token"]
    
    # Search
    client.headers["Authorization"] = f"Bearer {token}"
    search_resp = client.get("https://api.opensubtitles.com/api/v1/subtitles", params={
        "query": path_or_name,
        "languages": "en"
    })
    search_resp.raise_for_status()
    results = search_resp.json()["data"]
    if not results:
        raise click.UsageError(f"No subtitles found for '{path_or_name}' on OpenSubtitles")
        
    file_id = results[0]["attributes"]["files"][0]["file_id"]
    
    # Download
    dl_resp = client.post("https://api.opensubtitles.com/api/v1/download", json={
        "file_id": file_id
    })
    dl_resp.raise_for_status()
    
    dl_url = dl_resp.json()["link"]
    file_resp = httpx.get(dl_url)
    file_resp.raise_for_status()
    
    # Write to temp and load
    temp_path = config.work_dir / "temp.srt"
    config.work_dir.mkdir(parents=True, exist_ok=True)
    temp_path.write_bytes(file_resp.content)
    
    subs = pysubs2.load(str(temp_path))
    return _parse_pysubs2(subs)

def _parse_pysubs2(subs) -> list[SubSegment]:
    out = []
    for line in subs:
        text = re.sub(r'<[^>]+>|{[^}]+}', '', line.text).strip()
        text = text.replace(r"\N", " ").replace("\n", " ").strip()
        if text:
            out.append(SubSegment(
                start=line.start / 1000.0,
                end=line.end / 1000.0,
                text=text
            ))
    return out
