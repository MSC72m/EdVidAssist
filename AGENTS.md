# EdVidAssist — Agent Skill

This project converts a movie + an educational Persian PDF into a ≤15-minute
compilation video with a Persian instructor companion PDF (ندای وظیفه format).

## Quick start

```bash
uv run python -m edvidassist "Movie Name" /path/to/movie.mp4 /path/to/goals.pdf
```

With existing subtitle file:
```bash
uv run python -m edvidassist "Movie Name" /path/to/movie.mp4 /path/to/goals.pdf \
  --subtitle /path/to/subs.srt \
  --episode 2 \
  --output-dir output
```

## Required env vars (copy from .env or set manually)

```
OPENAI_API_KEY=...
OPENAI_API_BASE=https://api.avalai.ir/v1   # AvalAI proxy; or https://api.openai.com/v1
EDVIDASSIST_LLM_MODEL=openai/gpt-4o
EDVIDASSIST_EMBEDDING_MODEL=openai/text-embedding-3-small
EDVIDASSIST_TTS_PROVIDER=openai            # or elevenlabs
EDVIDASSIST_PEXELS_API_KEY=...             # optional; fallback = black frames
EDVIDASSIST_OPENSUBTITLES_API_KEY=...      # optional; needed if no --subtitle
EDVIDASSIST_OPENSUBTITLES_USERNAME=...
EDVIDASSIST_OPENSUBTITLES_PASSWORD=...
```

## System requirements

```bash
ffmpeg --version   # brew install ffmpeg
typst --version    # ~/.local/bin/typst  OR  brew install typst
```

## Pipeline steps (agent can invoke individually)

| Step | Import path | What it returns |
|------|-------------|-----------------|
| Extract short goals (for search) | `edvidassist.pdf_parser.extract_goals(pdf, config)` | `list[str]` |
| Extract full Persian goals (for PDF) | `edvidassist.pdf_parser.extract_goals_full(pdf, config)` | `list[dict]` with `bold_header`, `body` |
| Load subtitles | `edvidassist.subtitles.load_subtitles(path_or_name, config)` | `list[SubSegment]` |
| Chunk subtitles | `edvidassist.matcher.chunk_subtitles(segs)` | `list[TranscriptChunk]` |
| Match segments | `edvidassist.matcher.match_segments(chunks, goals, config)` | `list[EditSegment]` |
| Generate voiceover data | `edvidassist.voiceover.generate_voiceover(segs, goals, pdf_text, config, episode_num)` | `dict` (script, questions, whiteboard, flashback) |
| Synthesise TTS | `asyncio.run(provider.synthesize(text, voice, out_path))` | `Path` to .mp3 |
| Acquire visuals | `edvidassist.visuals.acquire_visuals(script, config)` | `list[Path]` |
| Build outro | `edvidassist.assembler.build_outro(clips, vo_path, config)` | `Path` |
| Assemble final video | `edvidassist.assembler.assemble(movie_path, segments, outro, config)` | `Path` |
| Generate companion PDF | `edvidassist.document.generate_pdf(title, episode_num, movie_name, goals_full, vo_data, config)` | `Path` |

## Companion PDF section schema

The output PDF mirrors the ندای وظیفه instructor booklet exactly:
1. **درسنامه اختصاصی اپیزود N** — episode header
2. **یادآوری اصول مربی‌گری** — fixed instructor reminder block
3. **کد و هدف محتوایی** — numbered Persian goals with bold header + body paragraph
4. **سوالات چالش‌برانگیز** — 3 audience engagement questions
5. **نقشه راه روی تخته** — two-column whiteboard (negative vs positive concepts)
6. **فلش‌بک** — link to previous episode (auto-skipped for episode 1)
7. **متن گفتار پایانی** — Persian voiceover script

## Tuning knobs

| Config key | Default | Effect |
|---|---|---|
| `max_segment_duration` | 300s | Max single clip length |
| `max_total_duration` | 900s | Total video ceiling |
| `transition_duration` | 1.0s | Crossfade between clips |
| `llm_model` | openai/gpt-4o | Any litellm model string |

Override via env `EDVIDASSIST_MAX_SEGMENT_DURATION=180` or `config.yaml`.

## Example test run (uses bundled sample files)

```bash
cd /path/to/EdVidAssist
cp /path/to/subs.srt dummy.srt   # provide any SRT for testing
uv run python -m edvidassist "The Hobbit" \
  docs/examples/video.mp4 \
  "docs/examples/205_temp_file_id_جزوه_ندای_وظیفه.pdf" \
  --subtitle dummy.srt

# Expected outputs:
# output/The_Hobbit_edvidassist.mp4  — compiled video ≤15min
# output/The_Hobbit_companion.pdf    — Persian instructor PDF
```
