import os
from PIL import Image, ImageDraw, ImageFont

from . import config

FONT_BOLD = config.FONT_BOLD
FONT_EMOJI = config.FONT_EMOJI

# Empirical text area within Card 1.png after scaling to 1080px wide
# Original card is 1920x960 → scaled to 1080x540 (factor 0.5625)
_TEXT_X      = 318   # x start of title text, aligned with card controls
_TEXT_Y      = 230   # y start of title text (below logo + emoji row)
_TEXT_MAX_W  = 460   # max text width inside the white card
_TEXT_LINE_H = 32    # line height
_TEXT_SIZE   = 25    # font size


def apply_title_to_card(title, card_path, output_path):
    """Scale card_path to 1080px wide and write title into the empty text area."""
    fn = ImageFont.truetype(FONT_BOLD, _TEXT_SIZE)

    card = Image.open(card_path).convert("RGBA")
    target_w = 1080
    target_h = int(card.height * target_w / card.width)
    card = card.resize((target_w, target_h), Image.LANCZOS)

    d = ImageDraw.Draw(card)
    lines = _wrap(d, title, fn, _TEXT_MAX_W)
    for i, line in enumerate(lines):
        d.text((_TEXT_X, _TEXT_Y + i * _TEXT_LINE_H), line,
               font=fn, fill=(14, 14, 14, 255))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    card.save(output_path, "PNG")
    return target_h

VIDEO_W = 1080
CARD_W  = 920
CARD_X  = (VIDEO_W - CARD_W) // 2
PAD     = 38
RADIUS  = 24
LINE_H  = 52
SHADOW  = 10  # card drop shadow offset


def _f(path, size):
    return ImageFont.truetype(path, size)


def _wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        candidate = f"{cur} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_w:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def generate_title_card(title, output_path):
    fn_author = _f(FONT_BOLD, 28)
    fn_title  = _f(FONT_BOLD, 38)
    fn_small  = _f(FONT_BOLD, 21)

    scratch = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines   = _wrap(scratch, title, fn_title, CARD_W - PAD * 2)

    AV      = 54
    title_h = len(lines) * LINE_H
    # layout rows: PAD | avatar(54) | 14 | emojis(28) | 20 | title | 22 | divider(1) | 16 | bottom(26) | PAD
    card_h  = PAD + AV + 14 + 28 + 20 + title_h + 22 + 1 + 16 + 26 + PAD

    # Canvas big enough for card + shadow
    canvas_w = VIDEO_W
    canvas_h = card_h + SHADOW

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    d      = ImageDraw.Draw(canvas)

    # Drop shadow
    sx, sy = CARD_X + SHADOW, SHADOW
    d.rounded_rectangle(
        [sx, sy, sx + CARD_W - 1, sy + card_h - 1],
        radius=RADIUS, fill=(0, 0, 0, 120),
    )

    # White card
    cx, cy = CARD_X, 0
    d.rounded_rectangle(
        [cx, cy, cx + CARD_W - 1, cy + card_h - 1],
        radius=RADIUS, fill=(255, 255, 255, 255),
    )

    # Avatar circle (Reddit orange)
    av_x, av_y = cx + PAD, cy + PAD
    d.ellipse([av_x, av_y, av_x + AV, av_y + AV], fill=(255, 69, 0, 255))
    # "R" letter inside avatar
    fn_av = _f(FONT_BOLD, 28)
    d.text((av_x + AV // 2, av_y + AV // 2), "R",
           font=fn_av, fill=(255, 255, 255, 255), anchor="mm")

    # Author name + checkmark
    name_x = av_x + AV + 16
    name_y = av_y + (AV - 28) // 2
    author = config.TITLECARD_AUTHOR
    d.text((name_x, name_y), author, font=fn_author, fill=(0, 0, 0, 255))
    nw = d.textlength(author, font=fn_author)
    d.text((name_x + nw + 6, name_y), "✓",
           font=fn_author, fill=(29, 155, 240, 255))

    # Emoji row
    emoji_y = av_y + AV + 14
    try:
        fn_em = _f(FONT_EMOJI, 22)
        d.text((cx + PAD, emoji_y), "🧸 👑 ♟️ 🎭 🎩 💀 😭 🤐",
               font=fn_em, fill=(0, 0, 0, 255), embedded_color=True)
    except Exception:
        pass

    # Title lines
    title_y = emoji_y + 28 + 20
    for i, line in enumerate(lines):
        d.text((cx + PAD, title_y + i * LINE_H), line,
               font=fn_title, fill=(15, 15, 15, 255))

    # Divider line
    div_y = title_y + title_h + 22
    d.line([(cx + PAD, div_y), (cx + CARD_W - PAD, div_y)],
           fill=(220, 220, 220, 255), width=1)

    # Bottom row
    bot_y = div_y + 16
    d.text((cx + PAD,       bot_y), "♡  99+",  font=fn_small, fill=(140, 140, 140, 255))
    d.text((cx + PAD + 130, bot_y), "💬  99+", font=fn_small, fill=(140, 140, 140, 255))
    sh_txt = "Share  ↑"
    sh_w = d.textlength(sh_txt, font=fn_small)
    d.text((cx + CARD_W - PAD - sh_w, bot_y), sh_txt,
           font=fn_small, fill=(140, 140, 140, 255))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return canvas_h
