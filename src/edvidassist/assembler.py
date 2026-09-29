import subprocess
from pathlib import Path
from .config import Config
from .matcher import EditSegment


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, check=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode())


def _duration(path: Path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(res.stdout.strip())


def _extract_segment(movie_path: Path, start: float, duration: float, out: Path) -> None:
    _run([
        "ffmpeg", "-y", "-ss", str(start), "-i", str(movie_path),
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-s", "1920x1080", "-r", "24", str(out),
    ])


def _marker_clip(label: str, duration: float, out: Path) -> None:
    """Dev-only: black frame with white text label."""
    safe = label.replace("'", "").replace(":", " ")[:60]
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=black:s=1920x1080:d={duration}",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-vf", (
            f"drawtext=text='{safe}':fontcolor=white:fontsize=36"
            ":x=(w-text_w)/2:y=(h-text_h)/2"
            ":fontfile=/System/Library/Fonts/Supplemental/Arial.ttf"
            ",drawtext=text='[DEV MARKER]':fontcolor=yellow:fontsize=24"
            ":x=(w-text_w)/2:y=h-60"
            ":fontfile=/System/Library/Fonts/Supplemental/Arial.ttf"
        ),
        "-c:v", "libx264", "-r", "24",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-t", str(duration), str(out),
    ])


def _generate_ambient_bed(duration: float, out_path: Path) -> Path:
    """Synthesize warm ambient chord pad when no custom music is provided."""
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=110:duration={duration + 2.0}",
        "-f", "lavfi", "-i", f"sine=frequency=164.81:duration={duration + 2.0}",
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration + 2.0}",
        "-filter_complex", (
            "[0:a][1:a][2:a]amix=inputs=3[chord];"
            "[chord]lowpass=f=350,volume=0.20,afade=t=in:st=0:d=1.5,afade=t=out:st="
            f"{max(0.0, duration - 2.0)}:d=2.0[pad]"
        ),
        "-map", "[pad]",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        str(out_path),
    ])
    return out_path


def build_outro(
    visual_clips: list[Path],
    voiceover_path: Path,
    config: Config,
    music_path: Path | None = None,
) -> Path:
    out_path = config.work_dir / "outro.mp4"
    if not visual_clips:
        return out_path

    N = len(visual_clips)
    durations = [_duration(c) for c in visual_clips]
    td = config.transition_duration
    filter_strs = []

    # 1. Video crossfades
    if N > 1:
        for i in range(N - 1):
            offset = sum(durations[:i+1]) - (i + 1) * td
            in1 = "[0:v]" if i == 0 else f"[v_mix_{i-1}]"
            filter_strs.append(
                f"{in1}[{i+1}:v]xfade=transition=fade:duration={td}:offset={offset:.2f}[v_mix_{i}]"
            )
        v_out = f"[v_mix_{N-2}]"
    else:
        v_out = "[0:v]"

    total_outro_dur = sum(durations) - max(0, N - 1) * td

    # 2. Background music bed + audio ducking
    music_file: Path
    if music_path and Path(music_path).exists():
        music_file = Path(music_path)
    else:
        ambient_out = config.work_dir / "ambient_bed.aac"
        _generate_ambient_bed(total_outro_dur + 2.0, ambient_out)
        music_file = ambient_out

    # Inputs:
    # 0..N-1: visual clips
    # N: voiceover_path
    # N+1: music_file
    cmd = ["ffmpeg", "-y"]
    for c in visual_clips:
        cmd.extend(["-i", str(c)])
    cmd.extend(["-i", str(voiceover_path)])
    cmd.extend(["-i", str(music_file)])

    # Sidechain audio ducking with asplit
    voice_idx = N
    music_idx = N + 1
    filter_strs.append(f"[{music_idx}:a]volume=0.22,aloop=loop=-1:size=2e+09[music_loop]")
    filter_strs.append(f"[{voice_idx}:a]asplit=2[voice_sc][voice_mix]")
    filter_strs.append(
        f"[music_loop][voice_sc]sidechaincompress=threshold=0.08:ratio=5:attack=80:release=450[ducked_music]"
    )
    filter_strs.append(f"[ducked_music][voice_mix]amix=inputs=2:duration=longest:dropout_transition=2[aout]")
    filter_complex_str = "; ".join(filter_strs)

    cmd.extend([
        "-filter_complex", filter_complex_str,
        "-map", v_out,
        "-map", "[aout]",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-r", "24",
        "-t", f"{total_outro_dur:.2f}",
        str(out_path),
    ])
    _run(cmd)
    return out_path


def assemble(
    movie_path: Path,
    segments: list[EditSegment],
    outro_path: Path,
    config: Config,
    dev_markers: bool = False,
) -> Path:
    segs_dir = config.work_dir / "segments"
    segs_dir.mkdir(parents=True, exist_ok=True)

    clips: list[Path] = []

    for i, seg in enumerate(segments):
        out = segs_dir / f"seg_{i:03d}.mp4"
        _extract_segment(movie_path, seg.start, seg.end - seg.start, out)

        if dev_markers and i > 0:
            marker = segs_dir / f"marker_{i:03d}.mp4"
            label = f"SEG {i+1}/{len(segments)}  {int(seg.start//60):02d}:{int(seg.start%60):02d}"
            _marker_clip(label, 1.5, marker)
            clips.append(marker)

        clips.append(out)

    if dev_markers:
        outro_marker = segs_dir / "marker_outro.mp4"
        _marker_clip("OUTRO (AI voiceover)", 1.5, outro_marker)
        clips.append(outro_marker)

    clips.append(outro_path)
    out_path = config.output_dir / f"{movie_path.stem}_edvidassist.mp4"
    return _concat_with_transitions(clips, out_path, config)


def _concat_with_transitions(clips: list[Path], out_path: Path, config: Config) -> Path:
    if not clips:
        return out_path
    if len(clips) == 1:
        subprocess.run(["cp", str(clips[0]), str(out_path)], check=True)
        return out_path

    N = len(clips)
    durations = [_duration(c) for c in clips]
    td = config.transition_duration
    filter_strs = []

    for i in range(N - 1):
        offset = sum(durations[:i+1]) - (i + 1) * td
        in1 = "[0:v]" if i == 0 else f"[v_{i-1}]"
        filter_strs.append(
            f"{in1}[{i+1}:v]xfade=transition=dissolve:duration={td}:offset={offset:.2f}[v_{i}]"
        )

    a_inputs = "".join(f"[{i}:a]" for i in range(N))
    filter_strs.append(f"{a_inputs}concat=n={N}:v=0:a=1[a_concat]")
    filter_strs.append("[a_concat]loudnorm=I=-16:TP=-1.5:LRA=11[a_norm]")

    cmd = ["ffmpeg", "-y"]
    for c in clips:
        cmd.extend(["-i", str(c)])
    cmd.extend([
        "-filter_complex", "; ".join(filter_strs),
        "-map", f"[v_{N-2}]",
        "-map", "[a_norm]",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-r", "24",
        str(out_path),
    ])
    _run(cmd)
    return out_path
