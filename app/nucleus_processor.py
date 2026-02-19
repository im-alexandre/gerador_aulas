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
from app.logging_utils import log_step


log = logging.getLogger(__name__)


def process_nucleus_dir(
    api_key_override: str | None,
    nucleus_dir: Path,
    course_dir: Path,
    prompt_md: str,
    model: str,
    image_model: str,
    image_size: str,
    image_quality: str | None,
    template_path: Path,
    force: bool,
    use_code_interpreter: bool = False,
    generate_images: bool = True,
    image_provider: str = "openai",
):
    """Processa um núcleo: tag -> JSON -> render."""
    content_docx = find_content_docx(nucleus_dir)
    roteiro_docx = find_roteiro_docx(nucleus_dir)

    if not content_docx or not roteiro_docx:
        log_step(
            log,
            nucleus_dir.name,
            "process_nucleus_dir",
            "Documentos de conteudo/roteiro nao encontrados",
        )
        return

    tagged_docx = nucleus_dir / f"{nucleus_dir.name}_tagged.docx"
    assets_dir = course_dir / ASSETS_DIRNAME / nucleus_dir.name
    tag_prefix = f"{ASSETS_DIRNAME}/{nucleus_dir.name}"

    if tagged_docx.exists() and not force:
        log_step(
            log,
            nucleus_dir.name,
            "create_tagged_docx",
            "Conteudo preparado",
        )
    else:
        created = create_tagged_docx(
            source_docx=content_docx,
            tagged_docx=tagged_docx,
            assets_dir=assets_dir,
            tag_prefix=tag_prefix,
        )
        log_step(
            log,
            nucleus_dir.name,
            "create_tagged_docx",
            "Conteudo preparado",
        )
        log_step(
            log,
            nucleus_dir.name,
            "create_tagged_docx",
            f"Tagged DOCX gerado com {created} imagem(ns)",
            level=logging.DEBUG,
        )

    plan_json = nucleus_dir / PLAN_JSON_NAME
    plan = generate_plan_for_dir(
        api_key_override=api_key_override,
        content_docx=tagged_docx,
        roteiro_docx=roteiro_docx,
        prompt_md=prompt_md,
        model=model,
        output_json=plan_json,
        force=force,
        strict_json=True,
        use_code_interpreter=use_code_interpreter,
    )
    if plan is None and plan_json.exists():
        plan = load_plan(plan_json)

    if plan is None:
        log_step(
            log,
            nucleus_dir.name,
            "generate_plan_for_dir",
            "Plano nao gerado",
        )
        return {"gamma_deducted": 0}

    errors = validate_plan(plan, assets_base=course_dir)
    if errors:
        for err in errors:
            log.error(f"[{nucleus_dir.name}] {err}")
        raise SystemExit("Validação do plano falhou.")

    log_step(
        log,
        nucleus_dir.name,
        "materialize_generated_images_for_plan",
        "Gerando imagens",
    )
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
            log_step(
                log,
                nucleus_dir.name,
                "materialize_generated_images_for_plan",
                f"Imagens Gamma: {created_gamma} (creditos: {gamma_deducted})",
                level=logging.DEBUG,
            )
        else:
            log_step(
                log,
                nucleus_dir.name,
                "materialize_generated_images_for_plan",
                f"Imagens Gamma reaproveitadas: {created_gamma}",
                level=logging.DEBUG,
            )

    created_openai = openai_materialize_generated_images(
        plan,
        course_dir=course_dir,
        nucleus_name=nucleus_dir.name,
        assets_dirname=ASSETS_DIRNAME,
        model=image_model,
        size=image_size,
        quality=image_quality,
        generate_images=generate_images,
        api_key_override=api_key_override,
    )
    if generate_images:
        log_step(
            log,
            nucleus_dir.name,
            "materialize_generated_images_for_plan",
            f"Imagens OpenAI: {created_openai}",
            level=logging.DEBUG,
        )
    else:
        log_step(
            log,
            nucleus_dir.name,
            "materialize_generated_images_for_plan",
            f"Imagens OpenAI reaproveitadas: {created_openai}",
            level=logging.DEBUG,
        )
    plan_json.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    output_pptx = nucleus_dir / f"{nucleus_dir.name}.pptx"
    log_step(
        log,
        nucleus_dir.name,
        "render_from_plan",
        "Gerando apresentacao baseada no template",
    )
    render_from_plan(
        plan=plan,
        template_path=template_path,
        output_path=output_pptx,
        assets_base=course_dir,
        title=None,
    )
    log_step(
        log,
        nucleus_dir.name,
        "render_from_plan",
        f"PPTX gerado: {output_pptx}",
        level=logging.DEBUG,
    )
