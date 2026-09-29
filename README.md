# EdVidAssist (ندای وظیفه)

> **Agent-assisted semantic video extraction, assembly, and pedagogical companion booklet generator.**

EdVidAssist takes a full-length movie, its subtitles, and a pedagogical reference PDF (such as the *ندای وظیفه* youth discussion curriculum), then:
1. Grounding in the film's actual dialogue, identifies semantically relevant video segments under a strict runtime ceiling (≤15 minutes total, ≤5 minutes per segment).
2. Smoothly edits and stitches those clips together with crossfades, speech-boundary padding, and optional dev inspection markers.
3. Generates an outro voiceover script connecting the film's core themes to educational goals, synthesizes high-fidelity TTS narration, and mixes it over an ambient soundtrack with **dynamic sidechain audio ducking**.
4. Compiles a Right-to-Left (RTL) Persian instructor companion PDF using **Typst**, matching the *ندای وظیفه* instructor booklet schema.

---

## Installation & Setup

### Option A: Install as an Agent Skill (Recommended for Claude Code, OpenCode, Pi, Codex)
Using the Agent Skills CLI:
```bash
npx skills add MSC72m/EdVidAssist
```
Or in an OpenCode session:
```bash
opencode run "run edvidassist skill on movie.mp4"
```

### Option B: Run via NPX / Node
```bash
npx edvidassist "Movie Name" /path/to/movie.mp4 /path/to/goals.pdf --subtitle /path/to/subs.srt
```

### Option C: Python / UV Local Setup
```bash
git clone https://github.com/MSC72m/EdVidAssist.git
cd EdVidAssist
uv sync
uv pip install -e .
```

### System Dependencies
- **FFmpeg & FFprobe**: `brew install ffmpeg`
- **Typst**: `~/.local/bin/typst` or `brew install typst`

### Environment Variables (`.env`)
Create or edit `.env` in the repository root:
```ini
OPENAI_API_KEY=aa-...                       # AvalAI proxy or OpenAI API key
OPENAI_API_BASE=https://api.avalai.ir/v1    # Optional: custom base URL
EDVIDASSIST_LLM_MODEL=openai/gpt-4o         # Model for ranking and script generation
EDVIDASSIST_EMBEDDING_MODEL=openai/text-embedding-3-small
EDVIDASSIST_TTS_PROVIDER=openai             # openai | elevenlabs | gemini
EDVIDASSIST_PEXELS_API_KEY=...              # Optional: stock footage search
EDVIDASSIST_OPENSUBTITLES_API_KEY=...       # Optional: automated subtitle downloads
```

---

## CLI Reference

```bash
uv run python -m edvidassist [OPTIONS] MOVIE_NAME MOVIE_PATH PDF_PATH
```

### Arguments
- `MOVIE_NAME`: Display title of the film (e.g. `"The Hobbit"` or `"Cosmos Laundromat"`).
- `MOVIE_PATH`: Path to the local input movie file (`.mp4`, `.mkv`).
- `PDF_PATH`: Path to the pedagogical curriculum reference PDF (`.pdf`).

### Options
| Flag | Default | Description |
|---|---|---|
| `--subtitle PATH` | Auto-search | Path to subtitle file (`.srt`, `.vtt`). If omitted, queries OpenSubtitles API. |
| `--output-dir PATH` | `output/` | Directory where final `.mp4` and `.pdf` files are saved. |
| `--episode INTEGER` | `1` | Episode number printed on the companion booklet header. |
| `--music PATH` | Ambient synth | Custom background music audio file for outro ducking bed. |
| `--visuals-dir PATH` | Auto-extract | Directory of pre-downloaded B-roll clips (`.mp4`) curated by agent/user. |
| `--padding FLOAT` | `0.5` | Pre- and post-roll boundary padding (in seconds) to avoid clipping dialogue. |
| `--merge-gaps FLOAT` | `30.0` | Merges consecutive segments closer than N seconds to maintain narrative flow. |
| `--dev-markers` | `False` | Inserts 1.5s visual cards (`[DEV MARKER] SEG X/Y mm:ss`) between cuts to audit editing boundaries. |
| `--config PATH` | None | Path to optional custom `config.yaml`. |

---

## Companion PDF Structure (*ندای وظیفه* Schema)

The generated companion document mirrors the exact layout of the reference Persian youth instructor guides:
1. **سربرگ اپیزود (Episode Header)**: Episode number and title in running header with Persian numerals.
2. **یادآوری اصول مربی‌گری (Instructor Reminder)**: Fixed didactic guidelines box for mentoring teenagers.
3. **کد و هدف محتوایی و معنایی (Content & Meaning Goals)**: 3–4 numbered pedagogical goals with a bold conceptual header and an explanatory paragraph grounded in the film's actual dialogue.
4. **سوالات چالش‌برانگیز (Challenging Reflection Questions)**: 3 thought-provoking engagement questions about the film's moral and existential dilemmas.
5. **نقشه راه روی تخته (Two-Column Whiteboard Matrix)**:
   - **ستون اول (Negative Concepts)**: Destructive behaviors, illusions, or materialism depicted in the film.
   - **ستون دوم (True Values)**: Authentic connection, courage, and genuine existential meaning.
   - **هنر مربی (Key Insight)**: High-impact takeaway sentence written on the blackboard.
6. **فلش‌بک (Flashback)**: Conceptual bridge linking to the previous episode (omitted for Episode 1).
7. **متن گفتار پایانی (Voiceover Script)**: Complete Persian narration script with custom styling.

---

## Agentic Workflow (For AI Coding Agents)

EdVidAssist is built to be controlled interactively by AI agents (Claude Code, OpenCode, Pi, Codex). Rather than executing a blind black-box run, an agent can inspect and refine each stage:

```python
from pathlib import Path
from edvidassist.config import Config
from edvidassist.subtitles import load_subtitles
from edvidassist.matcher import chunk_subtitles, match_segments
from edvidassist.pdf_parser import extract_goals, extract_goals_full_from_segments
from edvidassist.voiceover import generate_voiceover
from edvidassist.assembler import assemble, build_outro
from edvidassist.document import generate_pdf

cfg = Config.load()

# 1. Ingest subtitles and extract themes
subtitles = load_subtitles("subtitles.srt", cfg)
transcript = " ".join(s.text for s in subtitles)
themes = extract_goals(Path("curriculum.pdf"), transcript, cfg)

# 2. Match candidate clips with custom padding
chunks = chunk_subtitles(subtitles)
edl = match_segments(chunks, themes, cfg, padding=0.5, merge_gap=35.0)

# 3. Agent reviews EDL and refines cuts
# (Agent can prune clips, adjust timestamps, or bridge narrative gaps)

# 4. Generate grounded Persian booklet & script
goals_full = extract_goals_full_from_segments(edl, "Movie Title", themes, cfg)
vo_data = generate_voiceover(edl, themes, transcript[:3000], cfg, episode_num=1)

# 5. Assemble video and compile RTL PDF
# (Agent can pass custom B-roll and ambient music)
```

---

## License

AGPL-3.0 © EdVidAssist Contributors.
