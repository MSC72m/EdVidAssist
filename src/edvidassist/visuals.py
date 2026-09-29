import json
import subprocess
from pathlib import Path
from pydantic import BaseModel
import httpx
import litellm
import click
from .config import Config


class VisualScene(BaseModel):
    query: str
    duration: float


class VisualScenesResponse(BaseModel):
    scenes: list[VisualScene]


def _get_movie_duration(movie_path: Path) -> float:
    try:
        res = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(movie_path)
            ],
            check=True, capture_output=True, text=True,
        )
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def acquire_visuals(script: str, config: Config, movie_path: Path | None = None) -> list[Path]:
    sys_prompt = """Split this voiceover into 3-5 visual scenes. For each, provide a short
English search query suitable for stock video search (nature, contemplation, abstract concepts).
Total duration must equal voiceover audio duration."""

    resp = litellm.completion(
        model=config.llm_model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": script}
        ],
        response_format=VisualScenesResponse
    )
    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise click.UsageError("Failed to parse visual scenes JSON.")

    scenes = data.get("scenes", [])
    out_dir = config.work_dir / "visuals"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_clips: list[Path] = []
    movie_dur = _get_movie_duration(movie_path) if movie_path and movie_path.exists() else 0.0

    for i, scene in enumerate(scenes):
        query = scene["query"]
        duration = float(scene["duration"])
        out_path = out_dir / f"scene_{i:03d}.mp4"

        fetched = False
        # Strategy 1: Pexels stock footage if API key is provided
        if config.pexels_api_key:
            try:
                with httpx.Client(headers={"Authorization": config.pexels_api_key}, timeout=15.0) as client:
                    search = client.get("https://api.pexels.com/videos/search", params={
                        "query": query, "per_page": 5
                    })
                    if search.status_code == 200:
                        results = search.json().get("videos", [])
                        for vid in results:
                            if vid["duration"] >= duration:
                                files = vid.get("video_files", [])
                                hd = [f for f in files if f.get("quality") == "hd" and f.get("width", 0) >= 1920]
                                link = hd[0]["link"] if hd else (files[0]["link"] if files else None)

                                if link:
                                    clip_resp = client.get(link, follow_redirects=True)
                                    if clip_resp.status_code == 200:
                                        raw_path = out_dir / f"raw_{i:03d}.mp4"
                                        raw_path.write_bytes(clip_resp.content)

                                        subprocess.run([
                                            "ffmpeg", "-y", "-ss", "0", "-i", str(raw_path),
                                            "-t", str(duration),
                                            "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
                                            "-c:v", "libx264", "-crf", "18",
                                            "-preset", "fast", "-an", "-r", "24", str(out_path)
                                        ], check=True, capture_output=True)
                                        out_clips.append(out_path)
                                        fetched = True
                                        break
            except Exception:
                fetched = False

        # Strategy 2: Extract cinematic B-roll moments from the movie itself
        if not fetched and movie_path and movie_dur > 30.0:
            try:
                # Distribute timestamps across movie timeline (between 10% and 85%)
                step = 0.75 / max(1, len(scenes))
                offset_ratio = 0.10 + i * step
                start_sec = max(5.0, min(movie_dur - duration - 5.0, movie_dur * offset_ratio))

                subprocess.run([
                    "ffmpeg", "-y", "-ss", str(start_sec), "-i", str(movie_path),
                    "-t", str(duration),
                    "-vf", (
                        "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                        "eq=contrast=1.05:brightness=-0.02,"
                        "zoompan=z='min(zoom+0.0008,1.1)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=24"
                    ),
                    "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                    "-an", "-r", "24", "-pix_fmt", "yuv420p", str(out_path)
                ], check=True, capture_output=True)
                out_clips.append(out_path)
                fetched = True
            except Exception:
                fetched = False

        # Strategy 3: Stylized cinematic color background (no ugly raw text)
        if not fetched:
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=#101826:s=1920x1080:d={duration}",
                "-vf", (
                    "drawbox=x=0:y=0:w=1920:h=1080:color=#1E293B@0.6:t=fill,"
                    "boxblur=10:1"
                ),
                "-c:v", "libx264", "-r", "24", "-pix_fmt", "yuv420p", str(out_path)
            ], check=True, capture_output=True)
            out_clips.append(out_path)

    return out_clips
