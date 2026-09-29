#set text(lang: "fa", font: ("Vazirmatn", "Arial"), size: 11pt)
#set page(
  width: 21cm, height: 29.7cm,
  margin: (top: 2.5cm, bottom: 2.5cm, left: 2cm, right: 2cm),
  header: [
    #set text(size: 9pt, fill: gray)
    #grid(
      columns: (1fr, 1fr),
      align(right)[ندای وظیفه],
      align(left)[{{ episode_title }}]
    )
    #line(length: 100%, stroke: 0.5pt + gray)
  ],
  numbering: "۱",
)
#set par(leading: 1.2em, justify: false)
#set text(dir: rtl)

// ── Main title block ──────────────────────────────────────────
#v(0.5em)
#align(center)[
  #text(size: 16pt, weight: "bold")[{{ episode_header }}]
]
#v(1.5em)

// ── Section 1: Instructor reminder ───────────────────────────
#block(fill: luma(240), inset: 10pt, radius: 4pt, width: 100%)[
  #text(weight: "bold")[یادآوری اصول مربی‌گری:] \
  {{ instructor_reminder }}
]
#v(1em)

// ── Section 2: Goals ─────────────────────────────────────────
#text(weight: "bold", size: 12pt)[کد و هدف محتوایی و معنایی اپیزود:]
#v(0.5em)
{{ goals_content }}
#v(1em)

// ── Section 3: Challenge questions ───────────────────────────
#text(weight: "bold", size: 12pt)[سوالات چالش‌برانگیز برای درگیر کردن مخاطب:]
#v(0.5em)
{{ questions_content }}
#v(1em)

// ── Section 4: Whiteboard roadmap ────────────────────────────
#text(weight: "bold", size: 12pt)[نقشه راه روی تخته و هدایت گفت‌وگو:]
#v(0.5em)
#block[مربی عبارات کلیدی زیر را که از دل حرف‌های نوجوانان بیرون می‌کشد، پای تابلو به صورت دو ستون متقابل می‌نویسد:]
#v(0.5em)
#grid(
  columns: (1fr, 1fr),
  gutter: 12pt,
  block(stroke: 1pt + black, inset: 8pt, radius: 3pt, width: 100%)[
    #align(center)[#text(weight: "bold")[{{ wb_col1_label }}]]
    #v(0.3em)
    {{ wb_col1_items }}
  ],
  block(stroke: 2pt + blue, inset: 8pt, radius: 3pt, width: 100%)[
    #align(center)[#text(weight: "bold")[{{ wb_col2_label }}]]
    #v(0.3em)
    {{ wb_col2_items }}
  ],
)
#v(0.5em)
#block[#text(weight: "bold")[هنر مربی:] {{ whiteboard_key_insight }}]
#v(1em)

// ── Section 5: Flashback (only if not episode 1) ─────────────
{{ flashback_section }}

// ── Section 6: Voiceover script ──────────────────────────────
#line(length: 100%, stroke: 0.5pt + gray)
#v(0.5em)
#text(weight: "bold", size: 12pt)[متن گفتار پایانی (نریشن ویدیو):]
#v(0.5em)
#block(stroke: (right: 3pt + eastern), inset: (right: 10pt, y: 6pt))[
  {{ voiceover_script }}
]
