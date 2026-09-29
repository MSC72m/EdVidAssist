import json
from dataclasses import dataclass
import numpy as np
import litellm
import click
from pydantic import BaseModel
from .config import Config
from .subtitles import SubSegment


@dataclass
class TranscriptChunk:
    start: float
    end: float
    text: str
    segment_indices: list[int]


@dataclass
class EditSegment:
    start: float
    end: float
    goal: str          # which PDF goal this covers
    reason: str        # actual subtitle text from the clip (for voiceover/PDF content)


class MatcherSegment(BaseModel):
    start: float
    end: float
    goal: str          # the PDF goal this segment covers
    clip_text: str     # verbatim or lightly summarised subtitle text from this clip


class MatcherResponse(BaseModel):
    segments: list[MatcherSegment]


def chunk_subtitles(segments: list[SubSegment], window_sec: float = 30.0) -> list[TranscriptChunk]:
    chunks = []
    if not segments:
        return chunks

    current_chunk: list[tuple[int, SubSegment]] = []
    current_start = segments[0].start

    for i, seg in enumerate(segments):
        if not current_chunk:
            current_chunk.append((i, seg))
            current_start = seg.start
            continue

        prev_seg = current_chunk[-1][1]
        gap = seg.start - prev_seg.end
        duration = seg.end - current_start

        if duration >= window_sec or gap > 5.0:
            chunks.append(TranscriptChunk(
                start=current_start,
                end=prev_seg.end,
                text=" ".join(s[1].text for s in current_chunk),
                segment_indices=[s[0] for s in current_chunk],
            ))
            current_chunk = [(i, seg)]
            current_start = seg.start
        else:
            current_chunk.append((i, seg))

    if current_chunk:
        chunks.append(TranscriptChunk(
            start=current_start,
            end=current_chunk[-1][1].end,
            text=" ".join(s[1].text for s in current_chunk),
            segment_indices=[s[0] for s in current_chunk],
        ))

    return chunks


def match_segments(chunks: list[TranscriptChunk], goals: list[str], config: Config) -> list[EditSegment]:
    if not chunks or not goals:
        return []

    all_texts = goals + [c.text for c in chunks]
    batch_size = 2000
    all_embeddings: list[list[float]] = []

    for i in range(0, len(all_texts), batch_size):
        resp = litellm.embedding(model=config.embedding_model, input=all_texts[i:i+batch_size])
        all_embeddings.extend([d["embedding"] for d in resp.data])

    goal_emb = np.array(all_embeddings[:len(goals)])
    chunk_emb = np.array(all_embeddings[len(goals):])
    goal_emb /= np.linalg.norm(goal_emb, axis=1, keepdims=True)
    chunk_emb /= np.linalg.norm(chunk_emb, axis=1, keepdims=True)
    sim_matrix = np.dot(goal_emb, chunk_emb.T)

    candidate_text = ""
    for i, goal in enumerate(goals):
        top_indices = np.argsort(sim_matrix[i])[::-1][:20]
        candidate_text += f"\nGoal: {goal}\nCandidates:\n"
        for idx in top_indices:
            c = chunks[idx]
            candidate_text += f"[{c.start:.1f} - {c.end:.1f}] {c.text}\n"

    sys_prompt = f"""You are a video editor. Given content goals and candidate transcript segments, select the best clips.

Rules:
- Each segment ≤ {config.max_segment_duration}s
- Total ≤ {config.max_total_duration - 120}s
- No overlaps
- Every goal covered by at least one segment
- goal: copy the exact goal text from above
- clip_text: copy the ACTUAL SUBTITLE TEXT from the candidate you chose (verbatim, not a description of the goal)"""

    for attempt in range(3):
        resp = litellm.completion(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": candidate_text},
            ],
            response_format=MatcherResponse,
        )
        try:
            data = json.loads(resp.choices[0].message.content)
            result = []
            for s in data["segments"]:
                result.append(EditSegment(
                    start=float(s["start"]),
                    end=float(s["end"]),
                    goal=s["goal"],
                    reason=s["clip_text"],  # actual subtitle text
                ))
            result.sort(key=lambda x: x.start)

            total = 0.0
            for i, s in enumerate(result):
                if s.end - s.start > config.max_segment_duration:
                    raise ValueError(f"Segment > {config.max_segment_duration}s")
                if i > 0 and s.start < result[i-1].end:
                    raise ValueError("Overlapping segments")
                total += s.end - s.start
            if total > config.max_total_duration - 120:
                raise ValueError("Total duration exceeded")

            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            if attempt == 2:
                raise click.UsageError(f"Failed to generate valid edit segments: {e}")
            sys_prompt += f"\nLast attempt failed: {e}. Fix it."

    return []
