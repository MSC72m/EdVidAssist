import subprocess
from pathlib import Path
from .config import Config

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

def _pnum(n: int) -> str:
    return str(n).translate(_PERSIAN_DIGITS)

def _escape_typ(s: str) -> str:
    """Escape Typst special chars in literal text."""
    return s.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("#", "\\#")


def generate_pdf(
    title: str,
    episode_num: int,
    movie_name: str,
    goals_full: list[dict],   # list of {bold_header, body} — Persian
    voiceover_data: dict,
    config: Config,
) -> Path:
    tpl = (Path(__file__).parent / "templates" / "companion.typ").read_text("utf-8")

    # ── goals block ──────────────────────────────────────────────────────────
    goals_lines = []
    for i, g in enumerate(goals_full, 1):
        header = _escape_typ(g["bold_header"] if isinstance(g, dict) else g)
        body = _escape_typ(g["body"] if isinstance(g, dict) and "body" in g else "")
        goals_lines.append(
            f"#block(inset: (bottom: 8pt))[\n"
            f"  #text(weight: \"bold\")[{_pnum(i)}. {header}:] {body}\n"
            f"]"
        )
    goals_content = "\n".join(goals_lines)

    # ── questions ────────────────────────────────────────────────────────────
    questions_content = "\n".join(
        f"#block(inset: (right: 1em, bottom: 4pt))[• {_escape_typ(q)}]"
        for q in voiceover_data.get("questions", [])
    )

    # ── whiteboard ───────────────────────────────────────────────────────────
    col1_label = _escape_typ(voiceover_data.get("whiteboard_col1_label", ""))
    col2_label = _escape_typ(voiceover_data.get("whiteboard_col2_label", ""))
    col1_items = "، ".join(_escape_typ(x) for x in voiceover_data.get("whiteboard_col1_items", []))
    col2_items = "، ".join(_escape_typ(x) for x in voiceover_data.get("whiteboard_col2_items", []))
    key_insight = _escape_typ(voiceover_data.get("whiteboard_key_insight", ""))

    # ── flashback ────────────────────────────────────────────────────────────
    flashback_text = voiceover_data.get("flashback_text")
    if flashback_text:
        flashback_section = (
            f"#text(weight: \"bold\", size: 12pt)[فلش‌بک به اپیزود قبل:]\n"
            f"#v(0.5em)\n"
            f"#block[{_escape_typ(flashback_text)}]\n"
            f"#v(1em)\n"
        )
    else:
        flashback_section = ""

    rendered = tpl
    rendered = rendered.replace("{{ episode_title }}", _escape_typ(movie_name))
    rendered = rendered.replace("{{ episode_header }}", f"درسنامه اختصاصی اپیزود {_pnum(episode_num)}: {_escape_typ(movie_name)}")
    rendered = rendered.replace("{{ instructor_reminder }}", "همکار گرامی، لطفاً قبل از شروع این ایستگاه، متن اصول کلی مربی‌گری و مدیریت حلقه در ابتدای کتابچه را به دقت مرور کنید. بر روی لایه‌ی فطری و عقلانی نوجوان تمرکز کنید؛ گارد مخاطب را با بحث‌های زودرس مذهبی فعال نکنید و اجازه دهید زنجیره‌ی نقد سراب‌های مادی پله‌پله پیش برود.")
    rendered = rendered.replace("{{ goals_content }}", goals_content)
    rendered = rendered.replace("{{ questions_content }}", questions_content)
    rendered = rendered.replace("{{ wb_col1_label }}", col1_label)
    rendered = rendered.replace("{{ wb_col2_label }}", col2_label)
    rendered = rendered.replace("{{ wb_col1_items }}", col1_items)
    rendered = rendered.replace("{{ wb_col2_items }}", col2_items)
    rendered = rendered.replace("{{ whiteboard_key_insight }}", key_insight)
    rendered = rendered.replace("{{ flashback_section }}", flashback_section)
    rendered = rendered.replace("{{ voiceover_script }}", _escape_typ(voiceover_data.get("script", "")))

    out_typ = config.work_dir / "companion.typ"
    out_pdf = config.output_dir / f"{movie_name.replace(' ', '_')}_companion.pdf"
    config.output_dir.mkdir(parents=True, exist_ok=True)
    out_typ.write_text(rendered, encoding="utf-8")

    env_path = f"{Path.home()}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
    try:
        result = subprocess.run(
            ["typst", "compile", str(out_typ), str(out_pdf)],
            check=True, capture_output=True, text=True,
            env={"PATH": env_path, "HOME": str(Path.home())},
        )
        if result.stderr:
            print(f"Typst warnings: {result.stderr[:300]}")
    except FileNotFoundError:
        print("Warning: Typst not found, skipping companion PDF. Install: https://typst.app")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Typst compilation failed:\n{e.stderr[:500]}")

    return out_pdf
