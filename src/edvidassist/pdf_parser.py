from pathlib import Path
import pymupdf
import litellm
import click
import json
from pydantic import BaseModel
from .config import Config


class PDFThemes(BaseModel):
    themes: list[str]  # abstract universal themes, film-agnostic, for embedding search


class PDFGoalParagraph(BaseModel):
    bold_header: str  # short Persian phrase ≤8 words
    body: str         # full Persian paragraph about THIS film's actual scenes/dialogue


class PDFGoalsFull(BaseModel):
    goals: list[PDFGoalParagraph]


def _read_text(pdf_path: Path) -> str:
    doc = pymupdf.open(pdf_path)
    return "\n".join(page.get_text("text") for page in doc)


def extract_goals(pdf_path: Path, transcript: str, config: Config) -> list[str]:
    """Extract searchable themes grounded in the actual film transcript.

    The PDF tells us WHAT KIND of themes to look for (format/structure).
    The transcript tells us WHAT THIS FILM actually contains.
    Output: short English phrases describing what THIS film discusses,
    suitable for embedding search against the film's subtitle chunks.
    """
    pdf_text = _read_text(pdf_path)
    if not pdf_text.strip():
        raise click.UsageError("PDF contains no extractable text; OCR not supported")
    if not transcript.strip():
        raise click.UsageError("Film transcript is empty")

    sys_prompt = """You are a content analyst for an educational video program.

You receive:
1. An educational PDF that uses a specific film as an example to teach human themes
2. A film transcript from the ACTUAL film being processed

Your job: read the PDF to understand WHAT KINDS of themes are being taught (e.g. greed, isolation, awakening to true values), then find those SAME KINDS of themes in the actual film transcript.

Output 3-6 short English phrases describing what THIS film's transcript actually discusses that matches those theme categories. Ground each phrase in the actual dialogue/events from the transcript.

Rules:
- Do NOT mention the PDF's example film (e.g. Hobbit, Thorin)
- DO use character names and events from the actual transcript
- Each theme must be findable via embedding search in the transcript
- If the transcript has no match for a theme, skip it"""

    user_content = (
        f"=== EDUCATIONAL PDF (format reference) ===\n{pdf_text[:3000]}\n\n"
        f"=== ACTUAL FILM TRANSCRIPT (content source) ===\n{transcript[:6000]}"
    )

    resp = litellm.completion(
        model=config.llm_model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format=PDFThemes,
    )
    data = json.loads(resp.choices[0].message.content)
    return data["themes"]


def extract_goals_full_from_segments(
    matched_segments: list,  # list[EditSegment]
    movie_name: str,
    themes: list[str],
    config: Config,
) -> list[dict]:
    """Generate rich Persian instructor paragraphs from THIS film's actual matched segments.
    Content is entirely based on what the matched clips actually say.
    """
    segments_context = "\n".join(
        f"[{int(s.start//60):02d}:{int(s.start%60):02d}] {s.reason}"
        for s in matched_segments if s.reason.strip()
    )

    sys_prompt = f"""تو نویسنده راهنمای مربیان برای مجموعه «ندای وظیفه» هستی.
بر اساس دیالوگ‌ها و صحنه‌های واقعی فیلم «{movie_name}» که در زیر آمده، اهداف محتوایی و معنایی را به زبان فارسی روان و تربیتی بنویس.

قوانین نگارش:
۱. تمام متون (چه bold_header و چه body) باید صد در صد به زبان فارسی باشند و هیچ واژه انگلیسی در آن‌ها نباشد.
۲. bold_header: عنوان کوتاه مفهومی (حداکثر ۸ واژه فارسی) مانند: «نقد احساس تنهایی و پوچی»، «جستجوی معنا در انتخاب‌های جدید»، «بهای سنگین تغییر هویت».
۳. body: یک پاراگراف کامل توضیحی (شروع با عباراتی چون «تبیین این مفهوم از طریق داستان فیلم {movie_name} و شخصیت... که چگونه...» یا «نشان دادن چالشِ...») که چگونگی انتقال مفهوم به نوجوان را شفاف سازد.
۴. از اسامی واقعی شخصیت‌ها و رویدادهای همین دیالوگ‌ها استفاده کن. هیچ اشاره‌ای به فیلم‌های دیگر (مانند هابیت) نکن.
۵. دقیقاً ۳ یا ۴ هدف تولید کن."""

    resp = litellm.completion(
        model=config.llm_model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"دیالوگ‌های واقعی فیلم:\n{segments_context}"},
        ],
        response_format=PDFGoalsFull,
    )
    data = json.loads(resp.choices[0].message.content)
    return data["goals"]
