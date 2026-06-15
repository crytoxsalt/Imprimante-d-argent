from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from imprimante_argent import config

_W  = 1080
_BG = (255, 255, 255)
_FG = (15, 15, 15)

_RED   = (220, 50,  50)
_GREEN = (40, 130,  50)
_BLUE  = (21, 101, 192)
_GRAY  = (160, 160, 160)

_BOLD = str(config.FONT_BOLD)


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_BOLD, size)


def _draw_segments(draw, segments, font, y, canvas_w):
    """Draw mixed-color text segments centered on one line."""
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    total_w = sum(dummy.textlength(t, font=font) for t, _ in segments)
    x = (canvas_w - total_w) / 2
    for text, color in segments:
        draw.text((x, y), text, font=font, fill=color)
        x += dummy.textlength(text, font=font)


def render_title_dca(ticker_name: str, monthly: float, start_year: int) -> Image.Image:
    """
    Multi-color bold title matching data.dragonn style:
      POV: You've been [investing]red
      [$X]green a month in [TICKER] since
      [YEAR]blue
    """
    fn_big  = _font(72)
    fn_src  = _font(26)
    line_h  = 88
    pad_top = 60
    pad_bot = 50

    lines = [
        [("POV: You've been ", _FG), ("investing", _RED)],
        [(f"${monthly:,.0f}", _GREEN), (f" a month in {ticker_name} since", _FG)],
        [(str(start_year), _BLUE)],
    ]

    title_h = pad_top + len(lines) * line_h + pad_bot

    img  = Image.new("RGB", (_W, title_h), _BG)
    draw = ImageDraw.Draw(img)

    y = pad_top
    for seg_line in lines:
        _draw_segments(draw, seg_line, fn_big, y, _W)
        y += line_h

    # Source attribution bottom-right
    draw.text((_W - 24, title_h - 30), "Source: yahoo.finance",
              font=fn_src, fill=_GRAY, anchor="rs")

    # Thin separator line
    draw.line([(0, title_h - 3), (_W, title_h - 3)], fill=(210, 210, 210), width=2)

    return img


def render_title_comparison(
    ticker_names: dict[str, str], investment: float, start_year: int
) -> Image.Image:
    """
    Multi-color bold title for comparison video:
      POV: Back in [YEAR]blue you invested
      [$X]green in [TICKER vs TICKER]red
    """
    fn_big  = _font(68)
    fn_src  = _font(26)
    line_h  = 84
    pad_top = 60
    pad_bot = 50

    names = list(ticker_names.values())
    if len(names) >= 2:
        vs_text = " vs ".join(names)
    else:
        vs_text = names[0]

    lines = [
        [("POV: Back in ", _FG), (str(start_year), _BLUE), (" you invested", _FG)],
        [(f"${investment:,.0f}", _GREEN), (f" in {vs_text}", _RED)],
    ]

    title_h = pad_top + len(lines) * line_h + pad_bot

    img  = Image.new("RGB", (_W, title_h), _BG)
    draw = ImageDraw.Draw(img)

    y = pad_top
    for seg_line in lines:
        _draw_segments(draw, seg_line, fn_big, y, _W)
        y += line_h

    draw.text((_W - 24, title_h - 30), "Source: yahoo.finance",
              font=fn_src, fill=_GRAY, anchor="rs")
    draw.line([(0, title_h - 3), (_W, title_h - 3)], fill=(210, 210, 210), width=2)

    return img


# Keep legacy function for any callers that still use plain-text title
def render_title(title_text: str) -> Image.Image:
    fn     = _font(56)
    line_h = 72
    pad    = 60

    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    words = title_text.split()
    lines, cur = [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if dummy.textlength(cand, font=fn) <= _W - 80:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    h   = pad + len(lines) * line_h + pad
    img = Image.new("RGB", (_W, h), _BG)
    d   = ImageDraw.Draw(img)
    y   = pad
    for line in lines:
        d.text((40, y), line, font=fn, fill=_FG)
        y += line_h
    return img
