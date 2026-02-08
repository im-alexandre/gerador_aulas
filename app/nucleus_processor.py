from __future__ import annotations

import logging
import json
from pathlib import Path

from app.config.paths import ASSETS_DIRNAME, PLAN_JSON_NAME
from app.docx_tagger import create_tagged_docx, find_content_docx, find_roteiro_docx
from app.gpt_planner import generate_plan_for_dir
from app.gamma.orchestrator import (
    materialize_generated_images_for_plan as gamma_materialize_generated_images,
)
from app.image_generator import (
    materialize_generated_images_for_plan as openai_materialize_generated_images,
)
from app.pptx_renderer import load_plan, render_from_plan
from app.slide import validate_plan
from app.openai_cost import compute_llm_cost


log = logging.getLogger(__name__)


def process_nucleus_dir(
    nucleus_dir: Path,
    course_dir: Path,
    prompt_md: str,
    model: str,
    template_path: Path,
    force: bool,
    generate_images: bool = True,
    image_provider: str = "gamma",
) -> dict[str, object]:
    """Processa um núcleo: tag -> JSON -> render."""
    content_docx = find_content_docx(nucleus_dir)
    roteiro_docx = find_roteiro_docx(nucleus_dir)

    if not content_docx or not roteiro_docx:
        log.info(f"[{nucleus_dir.name}] DOCX de conteúdo/roteiro não encontrado.")
        return

    tagged_docx = nucleus_dir / f"{nucleus_dir.name}_tagged.docx"
    assets_dir = course_dir / ASSETS_DIRNAME / nucleus_dir.name
    tag_prefix = f"{ASSETS_DIRNAME}/{nucleus_dir.name}"

    if tagged_docx.exists() and not force:
        log.info(f"[{nucleus_dir.name}] Tagged DOCX já existe.")
    else:
        created = create_tagged_docx(
            source_docx=content_docx,
            tagged_docx=tagged_docx,
            assets_dir=assets_dir,
            tag_prefix=tag_prefix,
        )
        log.info(f"[{nucleus_dir.name}] Tagged DOCX gerado com {created} imagem(ns).")

    plan_json = nucleus_dir / PLAN_JSON_NAME
    plan, usage = generate_plan_for_dir(
        content_docx=tagged_docx,
        roteiro_docx=roteiro_docx,
        prompt_md=prompt_md,
        model=model,
        output_json=plan_json,
        force=force,
        strict_json=True,
    )
    if plan is None and plan_json.exists():
        plan = load_plan(plan_json)
        usage = None

    if plan is None:
        log.info(f"[{nucleus_dir.name}] Plano não gerado.")
        return {"gamma_deducted": 0}

    errors = validate_plan(plan, assets_base=course_dir)
    if errors:
        for err in errors:
            log.error(f"[{nucleus_dir.name}] {err}")
        raise SystemExit("Validação do plano falhou.")

    log.info(f"[{nucleus_dir.name}] Image provider: {image_provider}")
    created_gamma = 0
    gamma_deducted = 0
    if image_provider == "gamma":
        created_gamma, gamma_deducted = gamma_materialize_generated_images(
            plan,
            course_dir=course_dir,
            nucleus_name=nucleus_dir.name,
            assets_dirname=ASSETS_DIRNAME,
            generate_images=generate_images,
        )
        if generate_images:
            log.info(
                f"[{nucleus_dir.name}] Imagens Gamma: {created_gamma} (creditos: {gamma_deducted})"
            )
        else:
            log.info(
                f"[{nucleus_dir.name}] Imagens Gamma reaproveitadas: {created_gamma}"
            )

    created_openai, openai_images_cost = openai_materialize_generated_images(
        plan,
        course_dir=course_dir,
        nucleus_name=nucleus_dir.name,
        assets_dirname=ASSETS_DIRNAME,
        generate_images=generate_images,
    )
    if image_provider == "openai":
        label = "Imagens OpenAI"
    else:
        label = "Imagens OpenAI (fallback)"
    if generate_images:
        log.info(f"[{nucleus_dir.name}] {label}: {created_openai}")
    else:
        log.info(f"[{nucleus_dir.name}] {label} reaproveitadas: {created_openai}")
    plan_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    output_pptx = nucleus_dir / f"{nucleus_dir.name}.pptx"
    render_from_plan(
        plan=plan,
        template_path=template_path,
        output_path=output_pptx,
        assets_base=course_dir,
        title=None,
    )
    log.info(f"[{nucleus_dir.name}] PPTX gerado: {output_pptx}")
    llm_cost = compute_llm_cost(model, usage)
    return {
        "gamma_deducted": gamma_deducted,
        "openai_llm": llm_cost,
        "openai_images": openai_images_cost,
    }
