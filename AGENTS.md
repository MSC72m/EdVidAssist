---
name: edvidassist
description: Run EdVidAssist pipeline — convert a movie file + Persian educational PDF (ندای وظیفه format) into a ≤15-minute compiled video of semantically matched film segments plus an AI voiceover outro, and a full RTL Persian instructor companion PDF.
allowed-tools: Bash, Read, Edit, Write
---

# EdVidAssist Agent Skill

Use this skill when tasked with creating an educational video compilation and instructor companion booklet from a movie and a reference lesson plan (e.g. *ندای وظیفه* curriculum).

Project location: `/Users/msc8/code/EdVidAssist`

---

## Agent Role & Philosophy

EdVidAssist is **not a passive script**; the agent acts as an **intelligent video editor and educational director**:
1. **The reference PDF is a thematic guide, not content to copy**: The PDF defines pedagogical categories (e.g. greed, loneliness, authentic purpose). The agent must ground all extracted goals, questions, and voiceovers in the **actual dialogue and characters of the movie being processed**.
2. **Review Edit Decisions for Narrative Continuity**: When subtitle matching picks segments with short gaps between them (e.g. 20–40 seconds), verify whether crucial action or reaction beats were dropped. Use `--merge-gaps` or extend timestamps so scenes don't cut abruptly mid-action.
3. **Curate Outro Visuals & Audio**: Rather than accepting generic fallbacks, inspect the voiceover beats. The agent can download thematic B-roll or extract poignant visual frames from the film into `--visuals-dir`, and supply an ambient soundtrack via `--music`.

---

## Quick Execution

### Automated Run
```bash
uv run --project /Users/msc8/code/EdVidAssist python -m edvidassist \
  "Movie Name" \
  /path/to/movie.mp4 \
  /path/to/curriculum.pdf \
  --subtitle /path/to/subtitles.srt \
  --episode 1 \
  --output-dir output
```

### Dev Inspection Run (Visual Cut Markers & Gap Merging)
```bash
uv run --project /Users/msc8/code/EdVidAssist python -m edvidassist \
  "Movie Name" \
  /path/to/movie.mp4 \
  /path/to/curriculum.pdf \
  --subtitle /path/to/subtitles.srt \
  --padding 0.5 \
  --merge-gaps 35.0 \
  --dev-markers
```
*Note: `--dev-markers` inserts 1.5-second visual cards (`[DEV MARKER] SEG X/Y mm:ss`) at each cut boundary to visually audit editing decisions.*

---

## Step-by-Step Interactive Agent Workflow

When running EdVidAssist interactively, execute or script these stages:

### Stage 1: Ingest Subtitles & Audit Transcript
Load subtitles and check total spoken dialogue span:
```python
from edvidassist.config import Config
from edvidassist.subtitles import load_subtitles

cfg = Config.load()
subtitles = load_subtitles("subtitles.srt", cfg)
transcript = " ".join(s.text for s in subtitles)
print(f"Loaded {len(subtitles)} lines. Words: {len(transcript.split())}")
```
*Tip: If the movie has long non-verbal sequences (e.g. action or musical climaxes), note those timestamps so they can be merged or preserved.*

### Stage 2: Extract Grounded Thematic Goals
Pass both the curriculum PDF and the film transcript:
```python
from pathlib import Path
from edvidassist.pdf_parser import extract_goals

themes = extract_goals(Path("curriculum.pdf"), transcript, cfg)
print("Extracted themes:", themes)
```
*Rule: Ensure extracted themes do NOT mention characters from other example movies (e.g. Thorin/Hobbit) unless that is the actual film.*

### Stage 3: Match & Refine the Edit Decision List (EDL)
Match transcript chunks against themes, applying boundary padding (`padding=0.5`) and smart gap merging (`merge_gap=35.0`):
```python
from edvidassist.matcher import chunk_subtitles, match_segments

chunks = chunk_subtitles(subtitles)
edl = match_segments(chunks, themes, cfg, padding=0.5, merge_gap=35.0)

for s in edl:
    print(f"[{s.start:.1f}s -> {s.end:.1f}s] ({s.end - s.start:.1f}s): {s.reason[:60]}")
```
*Agent check: Confirm no cuts occur mid-sentence. Ensure total duration is under `max_total_duration - 120s` (default: ≤780s).*

### Stage 4: Author Persian Companion Booklet & Voiceover
Generate rich pedagogical Persian goals and voiceover data grounded in the matched clips:
```python
from edvidassist.pdf_parser import extract_goals_full_from_segments
from edvidassist.voiceover import generate_voiceover

goals_full = extract_goals_full_from_segments(edl, "Movie Name", themes, cfg)
vo_data = generate_voiceover(edl, themes, transcript[:3000], cfg, episode_num=1)
```

The resulting `vo_data` dictionary contains:
- `script`: 60–90 second Persian concluding voiceover narration.
- `questions`: 3 engagement questions for the audience.
- `whiteboard_col1_label` & `whiteboard_col1_items`: Negative concepts/illusions table.
- `whiteboard_col2_label` & `whiteboard_col2_items`: True values/positive alternatives table.
- `whiteboard_key_insight`: Key takeaway sentence for the blackboard.
- `flashback_text`: Episode bridge (null for Episode 1).

### Stage 5: Outro Audio & B-Roll Curation
1. Synthesize TTS narration:
```python
import asyncio
from edvidassist.tts import get_tts_provider

tts = get_tts_provider(cfg)
vo_path = cfg.work_dir / "voiceover.mp3"
asyncio.run(tts.synthesize(vo_data["script"], cfg.tts_voice, vo_path))
```
2. Curate B-roll visuals:
   - The agent can search and place 3–5 relevant video clips (`.mp4`) into `.edvidassist_work/visuals/`.
   - Alternatively, `acquire_visuals` automatically extracts cinematic B-roll from the movie with slow Ken Burns drift (`zoompan`) and 1080p framing.

### Stage 6: Assembly with Sidechain Audio Ducking
Stitch outro clips with background music ducking, then concatenate movie segments:
```python
from edvidassist.assembler import assemble, build_outro

# Mixes voiceover over ambient soundtrack (volume ducks dynamically when narrator speaks)
outro_path = build_outro(visual_clips, vo_path, cfg, music_path=None)

# Frame-accurate cut re-encoding + xfade crossfades + EBU R128 loudnorm
final_video = assemble(Path("movie.mp4"), edl, outro_path, cfg, dev_markers=False)
```

### Stage 7: Compile Typst Persian Companion PDF
```python
from edvidassist.document import generate_pdf

final_pdf = generate_pdf("Movie Name", 1, "Movie Name", goals_full, vo_data, cfg)
```
*Output verification: Ensure PDF exists and contains all 7 sections of the ندای وظیفه format.*

---

## CLI Options Cheatsheet

| Option | What it does |
|---|---|
| `--subtitle PATH` | Supply pre-existing SRT/VTT file |
| `--episode INTEGER` | Sets episode number in booklet header |
| `--music PATH` | Custom ambient background music for outro ducking bed |
| `--visuals-dir PATH` | Folder of agent-curated B-roll clips |
| `--padding FLOAT` | Boundary padding in seconds around cuts (default: `0.5s`) |
| `--merge-gaps FLOAT` | Merge close dialogue segments into continuous scenes (default: `30s`) |
| `--dev-markers` | Adds 1.5s visual title cards at cuts for reviewing edit boundaries |
| `--output-dir PATH` | Custom destination folder |

---

## Quality Checklist for Completed Run

Before delivering results to the user, verify:
- [ ] **Video length**: Total runtime ≤ 15 minutes (`ffprobe -show_entries format=duration`).
- [ ] **No speech clipping**: Each cut has speech padding and starts/ends cleanly.
- [ ] **Outro sound design**: Voiceover plays over an ambient soundtrack bed with audible ducking.
- [ ] **PDF schema**: Contains Episode header, Instructor reminder box, numbered Persian goals, 3 questions, 2-column whiteboard table, and voiceover text.
- [ ] **Grounded content**: PDF and voiceover refer strictly to the characters and scenes of the current film.
