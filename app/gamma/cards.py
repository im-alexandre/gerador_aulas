from __future__ import annotations

from typing import Any


def _normalize_bullets(bullets: Any) -> list[str]:
    if not isinstance(bullets, list):
        return []
    out: list[str] = []
    for b in bullets:
        if isinstance(b, str) and b.strip():
            out.append(b.strip())
    return out


def _image_spec(image: Any) -> str | None:
    if not isinstance(image, dict):
        return None
    source = (image.get("source") or "").strip()
    if source == "generated":
        intent = (image.get("intent") or "").strip()
        return f"Imagem (gerar): {intent}" if intent else None
    path = (image.get("path") or "").strip()
    if path:
        return f"Imagem (usar): {path}"
    return None


def build_cards_markdown(slides: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """Gera markdown de cards (1 card por slide) e retorna slide_ids."""
    cards: list[str] = []
    slide_ids: list[str] = []

    for idx, slide in enumerate(slides, 1):
        title = (slide.get("title") or "").strip()
        lead = (slide.get("lead") or "").strip()
        bullets = _normalize_bullets(slide.get("bullets"))
        image_line = _image_spec(slide.get("image"))

        slide_id = (slide.get("slide_id") or "").strip() or f"s{idx:02d}"
        slide_ids.append(slide_id)

        lines = [f"# {title}" if title else "# Slide"]
        if lead:
            lines += ["", f"Lead: {lead}"]
        if bullets:
            lines += ["", "Bullets:"]
            lines += [f"- {b}" for b in bullets]
        if image_line:
            lines += ["", image_line]

        cards.append("\n".join(lines).strip())

    return "\n\n---\n\n".join(cards), slide_ids
