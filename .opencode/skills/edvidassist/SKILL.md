---
name: edvidassist
description: Run EdVidAssist pipeline — convert a movie file + Persian educational PDF (ندای وظیفه format) into a ≤15-minute compiled video of semantically matched film segments plus an AI voiceover outro, and a full RTL Persian instructor companion PDF.
---

# EdVidAssist Pipeline

Project: `/Users/msc8/code/EdVidAssist`

## Run

```bash
uv run --project /Users/msc8/code/EdVidAssist python -m edvidassist \
  "Movie Name" /path/to/movie.mp4 /path/to/goals.pdf \
  --subtitle /path/to/subs.srt --episode N --output-dir output

# Dev mode: black-frame markers between segments
uv run --project /Users/msc8/code/EdVidAssist python -m edvidassist \
  "Movie Name" /path/to/movie.mp4 /path/to/goals.pdf \
  --subtitle /path/to/subs.srt --dev-markers
```

## Outputs
- `output/<MovieName>_edvidassist.mp4`
- `output/<MovieName>_companion.pdf`
