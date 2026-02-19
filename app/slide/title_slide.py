from __future__ import annotations

from app.slide.base_slide import BaseSlide, register_slide
from app.slide.render_utils import get_placeholder_by_idx, set_text


@register_slide
class TitleSlide(BaseSlide):
    """Slide de capa (kind='title')."""

    KIND = "title"
    LAYOUT_NAME = "title"

    @classmethod
    def validate(cls, slide: dict, assets_base, idx: int) -> list[str]:
        errors = cls.validate_common(slide, idx)
        image = slide.get("image") or {}
        code = slide.get("code") or {}
        if (image.get("path") or "").strip() or (image.get("intent") or "").strip():
            errors.append(f"Slide {idx}: kind=title não usa imagem.")

        # code existe por causa do schema, mas deve ser "vazio"
        if (code.get("language") or "").strip() or (code.get("text") or "").strip():
            errors.append(f"Slide {idx}: kind=title não usa code.")
        return errors

    @classmethod
    def render(cls, slide: dict, dst_slide, assets_base, ph_map: dict) -> None:
        """Renderiza o slide de capa."""
        set_text(
            get_placeholder_by_idx(dst_slide, ph_map.get("title")),
            slide.get("title", ""),
        )
