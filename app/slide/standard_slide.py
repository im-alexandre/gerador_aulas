from __future__ import annotations

from app.slide.base_slide import BaseSlide, register_slide
from app.slide.render_utils import (
    get_placeholder_by_idx,
    resolve_image_path,
    set_bullets,
    set_lead_with_bullets,
    set_text,
)


@register_slide
class StandardSlide(BaseSlide):
    """Slide padrão de conteúdo (kind='standard')."""

    KIND = "standard"
    LAYOUT_NAME = "standard"

    @classmethod
    def validate(cls, slide: dict, assets_base, idx: int) -> list[str]:
        errors = cls.validate_common(slide, idx)
        lead = slide.get("lead")
        if not isinstance(lead, str) or not lead.strip():
            errors.append(f"Slide {idx}: lead ausente ou inválido.")

        image = slide.get("image")
        if not isinstance(image, dict):
            errors.append(f"Slide {idx}: image ausente ou inválido.")
            return errors

        source = image.get("source")
        if source == "docx":
            if image.get("intent"):
                errors.append(
                    f"Slide {idx}: image.intent não permitido quando source=docx."
                )
            errors += cls.validate_image(image, assets_base, idx)
        elif source == "generated":
            intent = image.get("intent")
            errors += cls.validate_image_intent(intent, idx)
        else:
            errors.append(f"Slide {idx}: image.source inválido ({source}).")

        return errors

    @classmethod
    def render(cls, slide: dict, dst_slide, assets_base, ph_map: dict) -> None:
        """Renderiza o slide padrão."""
        set_text(
            get_placeholder_by_idx(dst_slide, ph_map.get("title")),
            slide.get("title", ""),
        )

        bullets = slide.get("bullets") or []
        lead = slide.get("lead") or ""
        lead_shape = get_placeholder_by_idx(dst_slide, ph_map.get("lead"))
        bullets_shape = get_placeholder_by_idx(dst_slide, ph_map.get("bullets"))
        if lead_shape and bullets_shape:
            set_text(lead_shape, lead)
            set_bullets(bullets_shape, bullets)
        else:
            set_lead_with_bullets(bullets_shape or lead_shape, lead, bullets)

        image = slide.get("image") or {}
        image_path = image.get("path")
        if image_path:
            image_box = get_placeholder_by_idx(dst_slide, ph_map.get("image"))
            if image_box:
                img_path = resolve_image_path(assets_base, image_path)
                if img_path.exists():
                    dst_slide.shapes.add_picture(
                        str(img_path),
                        image_box.left,
                        image_box.top,
                        image_box.width,
                        image_box.height,
                    )
