from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.config.pipeline import GAMMA_POLL_INTERVAL_SECONDS, GAMMA_POLL_TIMEOUT_SECONDS
from app.gamma.cards import build_cards_markdown
from app.gamma.client import generate_pptx_from_cards
from app.gamma.config import load_gamma_config
from app.gamma.extractor import extract_slide_images
from app.logging_utils import log_step


log = logging.getLogger(__name__)


def _collect_generated_slides(
    plan: dict[str, Any],
    course_dir: Path,
) -> list[tuple[int, dict[str, Any]]]:
    slides = plan.get("slides") or []
    if not isinstance(slides, list):
        return []

    targets: list[tuple[int, dict[str, Any]]] = []
    for idx, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        if (slide.get("kind") or "standard") != "standard":
            continue
        image = slide.get("image")
        if not isinstance(image, dict):
            continue
        if image.get("source") != "generated":
            continue
        intent = (image.get("intent") or "").strip()
        if not intent:
            continue
        rel_path = image.get("path")
        if isinstance(rel_path, str) and rel_path.strip():
            if (course_dir / rel_path).exists():
                continue
        targets.append((idx, slide))
    return targets


def _select_card_slides(
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    slides = plan.get("slides") or []
    if not isinstance(slides, list):
        return []
    selected: list[dict[str, Any]] = []
    for slide in slides:
        if not isinstance(slide, dict):
            continue
        image = slide.get("image")
        if not isinstance(image, dict):
            continue
        if image.get("source") != "generated":
            continue
        intent = (image.get("intent") or "").strip()
        if not intent:
            continue
        selected.append(slide)
    return selected


def materialize_generated_images_for_plan(
    plan: dict[str, Any],
    *,
    course_dir: Path,
    nucleus_name: str,
    assets_dirname: str = "assets",
    max_workers: int | None = None,
    generate_images: bool = True,
) -> tuple[int, int]:
    """
    Usa Gamma para gerar imagens dos slides com image.source="generated".
    Retorna (quantidade_criada, creditos_deduzidos).
    """
    del max_workers

    targets = _collect_generated_slides(plan, course_dir)
    if not targets:
        return 0, 0

    if not generate_images:
        reused = 0
        assets_dir = course_dir / assets_dirname / nucleus_name
        for _, slide in targets:
            image = slide.get("image") or {}
            rel = image.get("path")
            if isinstance(rel, str) and rel.strip() and (course_dir / rel).exists():
                reused += 1
                continue
            slide_id = (slide.get("slide_id") or "").strip()
            if slide_id:
                matches = list(assets_dir.glob(f"gen_{slide_id}.*"))
                if matches:
                    rel_path = f"{assets_dirname}/{nucleus_name}/{matches[0].name}"
                    if isinstance(image, dict):
                        image["path"] = rel_path
                        slide["image"] = image
                    reused += 1
        return reused, 0

    cfg = load_gamma_config()
    if not cfg:
        log_step(
            log,
            nucleus_name,
            "materialize_generated_images_for_plan",
            "Gamma desativado: gamma_config.json nao encontrado",
            level=logging.DEBUG,
        )
        return 0, 0

    card_slides = _select_card_slides(plan)
    if not card_slides:
        return 0, 0

    input_text, card_slide_ids = build_cards_markdown(card_slides)
    target_card_indices = list(range(len(card_slide_ids)))
    target_slide_ids = card_slide_ids
    assets_dir = course_dir / assets_dirname / nucleus_name
    export_path = assets_dir / "gamma_export.pptx"

    _, deducted = generate_pptx_from_cards(
        input_text,
        export_path,
        poll_interval=GAMMA_POLL_INTERVAL_SECONDS,
        timeout_seconds=GAMMA_POLL_TIMEOUT_SECONDS,
        context=nucleus_name,
    )

    extracted = extract_slide_images(
        export_path, assets_dir, target_card_indices, target_slide_ids
    )
    created = 0
    for (_, slide), out_path in zip(targets, extracted):
        if not out_path:
            continue
        rel = f"{assets_dirname}/{nucleus_name}/{out_path.name}"
        image = slide.get("image") or {}
        if isinstance(image, dict):
            image["path"] = rel
            slide["image"] = image
            created += 1

    return created, deducted
