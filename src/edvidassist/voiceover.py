import json
from pydantic import BaseModel
import litellm
import click
from .config import Config
from .matcher import EditSegment


class VoiceoverResponse(BaseModel):
    script: str                      # 60-90s Persian voiceover narration
    estimated_seconds: int
    questions: list[str]             # exactly 3, Persian, about THIS film's scenes
    whiteboard_col1_label: str       # short label for problem/negative column
    whiteboard_col1_items: list[str] # 4-6 concrete negative concepts from THIS film's scenes
    whiteboard_col2_label: str       # short label for values/positive column
    whiteboard_col2_items: list[str] # 4-6 true values from THIS film's scenes
    whiteboard_key_insight: str      # bold sentence instructor writes on board
    flashback_text: str | None       # None for ep1


def generate_voiceover(
    segments: list[EditSegment],
    goals: list[str],
    pdf_text: str,
    config: Config,
    episode_num: int = 1,
) -> dict:
    # Build rich segment context: actual subtitle text + timestamps
    segments_context = ""
    for i, s in enumerate(segments, 1):
        m_s, s_s = int(s.start // 60), int(s.start % 60)
        m_e, s_e = int(s.end // 60), int(s.end % 60)
        segments_context += (
            f"\nبخش {i} [{m_s:02d}:{s_s:02d} - {m_e:02d}:{s_e:02d}]:\n"
            f"متن دیالوگ: {s.reason}\n"
            f"هدف آموزشی مرتبط: {s.goal}\n"
        )

    sys_prompt = f"""تو نویسنده راهنمای آموزشی برای مجموعه «ندای وظیفه» هستی.
بر اساس بخش‌های واقعی انتخاب‌شده از فیلم (دیالوگ‌ها و توضیحات آن‌ها) و اهداف آموزشی، همه موارد زیر را به فارسی بنویس.

مهم: محتوای تو باید کاملاً بر اساس دیالوگ‌ها و صحنه‌های واقعی همین فیلم باشد — نه فیلم دیگری.

- script: متن نریشن پایانی ۶۰ تا ۹۰ ثانیه که به صحنه‌های خاص این فیلم اشاره می‌کند و با سوال تأملی ختم می‌شود
- estimated_seconds: عدد صحیح
- questions: دقیقاً ۳ سوال چالش‌برانگیز فارسی درباره صحنه‌های واقعی همین فیلم
- whiteboard_col1_label: یک عنوان مفهومی و کوتاه فارسی برای ستون مفاهیم منفی یا آسیب‌های مطرح‌شده در فیلم (مانند «انزوا و گریز از واقعیت» یا «بیماری مصرف‌زدگی»)
- whiteboard_col1_items: ۴ تا ۶ عبارت کوتاه فارسی از مفاهیم منفی که در این فیلم تجربه شد
- whiteboard_col2_label: یک عنوان مفهومی و کوتاه فارسی برای ستون ارزش‌های حقیقی و پیام‌های رهایی‌بخش (مانند «ارتباط اصیل و بازگشت به زندگی» یا «معنای حقیقی زیستن»)
- whiteboard_col2_items: ۴ تا ۶ عبارت کوتاه فارسی از ارزش‌ها و راه‌حل‌های متقابل در فیلم
- whiteboard_key_insight: یک جمله کوبنده بر اساس این فیلم که مربی پای تابلو می‌نویسد
- flashback_text: null (اپیزود اول)"""

    context = f"بخش‌های انتخاب‌شده از فیلم:\n{segments_context}\n\nاهداف آموزشی کلی:\n"
    for g in goals:
        context += f"- {g}\n"

    resp = litellm.completion(
        model=config.llm_model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": context},
        ],
        response_format=VoiceoverResponse,
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        raise click.UsageError("Failed to parse voiceover JSON.")
