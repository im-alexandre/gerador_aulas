from __future__ import annotations

from app.slide.base_slide import BaseSlide, register_slide
from app.slide.render_utils import (
    get_placeholder_by_idx,
    set_bullets,
    set_code,
    set_text,
)


@register_slide
class CodeSlide(BaseSlide):
    """Slide de código (kind='code')."""

    KIND = "code"
    LAYOUT_NAME = "code"

    @classmethod
    def validate(cls, slide: dict, assets_base, idx: int) -> list[str]:
        errors = cls.validate_common(slide, idx)
        image = slide.get("image") or {}
        if (image.get("path") or "").strip() or (image.get("intent") or "").strip():
            errors.append(f"Slide {idx}: kind=code não usa imagem.")

        code = slide.get("code") or {}
        if not isinstance(code, dict):
            errors.append(f"Slide {idx}: code ausente ou inválido.")
        else:
            code_text = code.get("text")
            if not isinstance(code_text, str) or not code_text.strip():
                errors.append(f"Slide {idx}: code.text ausente ou vazio.")

            code_language = code.get("language")
            if not isinstance(code_language, str) or not code_language.strip():
                errors.append(f"Slide {idx}: code.language ausente ou vazio.")
        return errors

    @classmethod
    def render(cls, slide: dict, dst_slide, assets_base, ph_map: dict) -> None:
        """Renderiza o slide de código."""
        set_text(
            get_placeholder_by_idx(dst_slide, ph_map.get("title")),
            slide.get("title", ""),
        )

        code = slide.get("code", {}) or {}
        code_text = code.get("text", "")
        bullets = slide.get("bullets") or []

        code_shape = get_placeholder_by_idx(dst_slide, ph_map.get("code"))
        bullets_shape = get_placeholder_by_idx(dst_slide, ph_map.get("bullets"))

        if code_shape:
            set_code(code_shape, code_text)
        if bullets_shape:
            set_bullets(bullets_shape, bullets)
        if not code_shape and bullets_shape:
            combined = code_text
            if bullets:
                combined += "\n\n" + "\n".join(f"- {b}" for b in bullets)
            set_code(bullets_shape, combined)
