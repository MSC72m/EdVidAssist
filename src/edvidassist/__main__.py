import asyncio
import click
from pathlib import Path
from .config import Config
from .pdf_parser import extract_goals, extract_goals_full_from_segments
from .subtitles import load_subtitles
from .matcher import chunk_subtitles, match_segments
from .voiceover import generate_voiceover
from .tts import get_tts_provider
from .visuals import acquire_visuals
from .assembler import assemble, build_outro
from .document import generate_pdf


@click.command()
@click.argument("movie_name")
@click.argument("movie_path", type=click.Path(exists=True))
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--subtitle", type=click.Path(exists=True), help="SRT or VTT file")
@click.option("--config", "config_path", type=click.Path(exists=True), help="config.yaml path")
@click.option("--output-dir", type=click.Path(), default="output")
@click.option("--episode", default=1, type=int, help="Episode number for companion PDF")
@click.option("--music", type=click.Path(exists=True), help="Custom background music for outro")
@click.option("--visuals-dir", type=click.Path(exists=True), help="Directory of pre-downloaded B-roll clips (.mp4)")
@click.option("--padding", default=0.5, type=float, help="Padding in seconds around cut boundaries (default: 0.5s)")
@click.option("--merge-gaps", default=30.0, type=float, help="Merge clips closer than N seconds into continuous scenes (default: 30s)")
@click.option("--dev-markers", is_flag=True, default=False,
              help="Insert 1.5s black-frame markers between segments (dev only)")
def main(
    movie_name,
    movie_path,
    pdf_path,
    subtitle,
    config_path,
    output_dir,
    episode,
    music,
    visuals_dir,
    padding,
    merge_gaps,
    dev_markers,
):
    """EdVidAssist: Semantic video extraction and assembly."""
    cfg = Config.load(config_path)
    cfg.output_dir = Path(output_dir)
    cfg.work_dir.mkdir(parents=True, exist_ok=True)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: load subtitles
    print("[1/9] Loading subtitles...")
    sub_segments = load_subtitles(subtitle if subtitle else movie_name, cfg)
    print(f"       {len(sub_segments)} subtitle entries loaded")

    transcript = " ".join(s.text for s in sub_segments)

    # Step 2: extract themes
    print("[2/9] Extracting themes from PDF (grounded in film transcript)...")
    themes = extract_goals(Path(pdf_path), transcript, cfg)
    print(f"       {len(themes)} themes: {themes}")

    # Step 3: chunk subtitles
    print("[3/9] Chunking subtitles...")
    chunks = chunk_subtitles(sub_segments)
    print(f"       {len(chunks)} chunks")

    # Step 4: match segments with speech padding and smart gap merging
    print(f"[4/9] Matching segments (padding={padding}s, merge_gaps={merge_gaps}s)...")
    edit_segments = match_segments(chunks, themes, cfg, padding=padding, merge_gap=merge_gaps)
    if not edit_segments:
        print("No matching segments found.")
        return

    print(f"[5/9] EDL Summary ({len(edit_segments)} clips):")
    total_dur = 0.0
    for s in edit_segments:
        dur = s.end - s.start
        total_dur += dur
        m_s, s_s = int(s.start // 60), int(s.start % 60)
        m_e, s_e = int(s.end // 60), int(s.end % 60)
        print(f"  [{m_s:02d}:{s_s:02d}→{m_e:02d}:{s_e:02d}] ({dur:.0f}s) {s.reason[:80]}")
    print(f"       Total clip time: {total_dur:.0f}s / {total_dur/60:.1f}min")

    # Step 5: generate rich Persian goals + voiceover
    print("[6/9] Generating voiceover + companion content from matched scenes...")
    goals_full = extract_goals_full_from_segments(edit_segments, movie_name, themes, cfg)
    vo_data = generate_voiceover(edit_segments, themes, transcript[:3000], cfg, episode_num=episode)
    print(f"       Voiceover: {vo_data['estimated_seconds']}s estimated")

    # Step 6: TTS audio synthesis
    print("[7/9] Synthesising TTS audio...")
    tts = get_tts_provider(cfg)
    vo_path = cfg.work_dir / "voiceover.mp3"
    asyncio.run(tts.synthesize(vo_data["script"], cfg.tts_voice, vo_path))

    # Step 7: acquire visuals
    print("[8/9] Acquiring visuals for outro...")
    visual_clips = acquire_visuals(
        vo_data["script"],
        cfg,
        movie_path=Path(movie_path),
        visuals_dir=Path(visuals_dir) if visuals_dir else None,
    )
    print(f"       {len(visual_clips)} visual clips acquired")

    # Step 8: assemble outro with audio ducking and ambient soundtrack
    print(f"[9a/9] Assembling outro with soundtrack and sidechain audio ducking...")
    outro_path = build_outro(visual_clips, vo_path, cfg, music_path=Path(music) if music else None)

    # Step 9: assemble final video
    print(f"[9b/9] Assembling final video{' (dev markers ON)' if dev_markers else ''}...")
    final_video = assemble(Path(movie_path), edit_segments, outro_path, cfg, dev_markers=dev_markers)

    # Step 10: generate RTL Companion PDF
    print("[9c/9] Generating companion PDF...")
    final_pdf = generate_pdf(movie_name, episode, movie_name, goals_full, vo_data, cfg)

    import subprocess
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(final_video)],
        capture_output=True, text=True,
    ).stdout.strip()

    print(f"\n✓ Done!")
    print(f"  Video : {final_video}  ({float(dur):.0f}s / {float(dur)/60:.1f}min)")
    print(f"  PDF   : {final_pdf}")
    if dev_markers:
        print(f"  [DEV] Black-frame markers inserted between each segment")


if __name__ == "__main__":
    main()
