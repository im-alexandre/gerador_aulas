from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

from PIL import Image, ImageDraw, ImageFont
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.lexers.special import TextLexer
from pygments.styles import get_style_by_name
from pygments.token import Token


Color = Tuple[int, int, int]
Segment = Tuple[str, Color]
Line = List[Segment]


def _parse_color(value: str | None, default: Color) -> Color:
    if not value:
        return default
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except Exception:
        return default


def _load_font(font_size: int, font_name: str | None = None) -> ImageFont.FreeTypeFont:
    candidates = []
    if font_name:
        candidates.append(font_name)
    candidates += [
        "C:\\Windows\\Fonts\\CascadiaMono.ttf",
        "C:\\Windows\\Fonts\\CascadiaMonoPL.ttf",
        "C:\\Windows\\Fonts\\FiraCode-Regular.ttf",
        "C:\\Windows\\Fonts\\cour.ttf",
        "C:\\Windows\\Fonts\\Courier New.ttf",
        "Courier New",
        "Courier",
    ]
    for cand in candidates:
        try:
            return ImageFont.truetype(cand, font_size)
        except Exception:
            continue
    return ImageFont.load_default()


def _get_text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> float:
    if hasattr(draw, "textlength"):
        return float(draw.textlength(text, font=font))
    bbox = font.getbbox(text)
    return float(bbox[2] - bbox[0])


def _tokenize_lines(
    code: str,
    language: str,
    theme: str,
    *,
    tab_size: int,
) -> tuple[list[Line], Color]:
    try:
        lexer = get_lexer_by_name(language, stripall=False)
    except Exception:
        lexer = TextLexer()

    style = get_style_by_name(theme)
    bg_color = _parse_color(style.background_color, (255, 255, 255))
    default_color = _parse_color(style.style_for_token(Token.Text).get("color"), (0, 0, 0))

    lines: list[Line] = [[]]
    for token, value in lex(code, lexer):
        color_hex = style.style_for_token(token).get("color")
        color = _parse_color(color_hex, default_color)
        parts = value.split("\n")
        for i, part in enumerate(parts):
            if part:
                part = part.replace("\t", " " * tab_size)
                lines[-1].append((part, color))
            if i < len(parts) - 1:
                lines.append([])
    return lines, bg_color


def render_code_to_images(
    *,
    language: str,
    code: str,
    output_dir: Path,
    max_width_px: int,
    max_height_px: int,
    base_name: str = "code",
    theme: str = "default",
    font_size: int = 28,
    padding_px: int = 24,
    tab_size: int = 4,
    line_spacing: float = 1.2,
    dpi: int = 180,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    font = _load_font(font_size)
    draw_dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    lines, bg_color = _tokenize_lines(
        code,
        language,
        theme,
        tab_size=tab_size,
    )

    ascent, descent = font.getmetrics()
    line_height = int((ascent + descent) * line_spacing)
    max_lines = (max_height_px - 2 * padding_px) // line_height
    if max_lines <= 0:
        raise ValueError("max_height_px muito pequeno para a fonte/padding.")

    def line_width(segments: Iterable[Segment]) -> float:
        return sum(_get_text_width(draw_dummy, text, font) for text, _ in segments)

    pages: list[list[Line]] = []
    for i in range(0, len(lines), max_lines):
        pages.append(lines[i : i + max_lines])

    out_paths: list[Path] = []
    for page_idx, page_lines in enumerate(pages, 1):
        max_line_width = 0.0
        for line in page_lines:
            max_line_width = max(max_line_width, line_width(line))

        width = int(min(max_width_px, max_line_width + 2 * padding_px))
        height = int(min(max_height_px, len(page_lines) * line_height + 2 * padding_px))

        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        y = padding_px
        for line in page_lines:
            x = padding_px
            for text, color in line:
                draw.text((x, y), text, font=font, fill=color)
                x += _get_text_width(draw, text, font)
            y += line_height

        out_path = output_dir / f"{base_name}_{page_idx:02d}.png"
        img.save(out_path, format="PNG", dpi=(dpi, dpi))
        out_paths.append(out_path)

    return out_paths


if __name__ == "__main__":
    sample_code = """def hello(name):
    print(f"Hello, {name}")

hello("world")
"""
    render_code_to_images(
        language="python",
        code=sample_code,
        output_dir=Path("code_images"),
        max_width_px=1200,
        max_height_px=700,
        base_name="code_s04",
        theme="default",
        font_size=28,
    )
