from __future__ import annotations

import base64
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.config.pipeline import (
    IMAGE_WORKERS,
    OPENAI_IMAGE_MODEL,
    OPENAI_IMAGE_SIZE,
    OPENAI_IMAGE_QUALITY,
)


def _img_prompt_from_slide(slide: dict[str, Any]) -> str:
    title = (slide.get("title") or "").strip()
    lead = (slide.get("lead") or "").strip()
    bullets = slide.get("bullets") or []

    intent = ""
    image = slide.get("image") or {}
    if isinstance(image, dict):
        intent = (image.get("intent") or "").strip()

    bullets_txt = "\n".join(
        f"- {b}" for b in bullets[:6] if isinstance(b, str) and b.strip()
    )

    return (
        "Crie uma imagem para slide de aula (PowerPoint), limpa e didatica.\n"
        "Estilo: vetorial/flat, fundo claro, poucas cores, sem texto legivel, sem logos, sem marcas d'agua.\n"
        "Use icones genericos, formas simples, setas, fluxo e agrupamento visual.\n\n"
        "CONTEXTO DO SLIDE (APENAS PARA COMPREENSÃO, NAO VISUAL):\n"
        "O texto abaixo e fornecido SOMENTE para orientar o conceito da imagem.\n"
        "NAO deve aparecer na imagem, nem parcial nem indiretamente.\n\n"
        f"TITULO DO SLIDE: {title}\n"
        f"LEAD (contexto): {lead}\n"
        f"BULLETS (pontos):\n{bullets_txt}\n\n"
        "REGRAS DE TEXTO NA IMAGEM (STRICT):\n"
        "- PROIBIDO qualquer texto, letra, numero ou pseudo-texto.\n"
        "- PROIBIDO caracteres embaralhados ou simbolos que imitem escrita.\n"
        "- NAO usar rotulos, legendas ou captions.\n"
        "- Use APENAS icones, formas, setas, cores e agrupamento visual.\n\n"
        f"INTENT (o que precisa comunicar visualmente): {intent}\n\n"
        "Se houver conflito entre o contexto do slide e as regras visuais,\n"
        "as regras visuais SEMPRE prevalecem.\n"
        "Entregue uma unica composicao clara que represente o intent."
    ).strip()


def generate_image_png(
    client: OpenAI,
    prompt: str,
    out_path: Path,
    *,
    model: str = OPENAI_IMAGE_MODEL,
    size: str = OPENAI_IMAGE_SIZE,
    quality: str | None = OPENAI_IMAGE_QUALITY,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    if quality:
        payload["quality"] = quality

    img = client.images.generate(**payload)

    image_bytes = base64.b64decode(img.data[0].b64_json)
    out_path.write_bytes(image_bytes)


def materialize_generated_images_for_plan(
    plan: dict[str, Any],
    *,
    course_dir: Path,
    nucleus_name: str,
    assets_dirname: str = "assets",
    model: str = OPENAI_IMAGE_MODEL,
    size: str = OPENAI_IMAGE_SIZE,
    quality: str | None = OPENAI_IMAGE_QUALITY,
    max_workers: int | None = None,
    generate_images: bool = True,
) -> tuple[int, dict]:
    """
    Para cada slide standard com image.source="generated":
      - gera PNG
      - escreve em {course_dir}/{assets_dirname}/{nucleus_name}/gen_{slide_id}.png
      - injeta image.path no JSON (mantendo source/intent)
    Retorna (quantidade_criada, custo_estimado).
    """
    slides = plan.get("slides") or []
    if not isinstance(slides, list):
        return 0, {"model": model, "size": size, "count": 0, "cost_usd": 0}

    tasks: list[tuple[dict[str, Any], str, Path, str]] = []
    for slide in slides:
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

        # já tem path? só valida existência e segue
        rel_path = image.get("path")
        if isinstance(rel_path, str) and rel_path.strip():
            if (course_dir / rel_path).exists():
                continue

        slide_id = (slide.get("slide_id") or "").strip()
        if not slide_id:
            slide_id = f"s{len(tasks) + 1:02d}"
        rel = f"{assets_dirname}/{nucleus_name}/gen_{slide_id}.png"
        out_path = course_dir / rel

        prompt = _img_prompt_from_slide(slide)
        tasks.append((slide, rel, out_path, prompt))

    if not tasks:
        return 0, {"model": model, "size": size, "count": 0, "cost_usd": 0}

    if generate_images and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Defina OPENAI_API_KEY.")

    if not generate_images:
        reused = 0
        for slide, rel, out_path, _prompt in tasks:
            if out_path.exists():
                image = slide.get("image") or {}
                if isinstance(image, dict):
                    image["path"] = rel
                    slide["image"] = image
                reused += 1
        return reused, {"model": model, "size": size, "count": 0, "cost_usd": 0}

    def _generate_one(prompt: str, out_path: Path) -> None:
        client = OpenAI()
        generate_image_png(
            client=client,
            prompt=prompt,
            out_path=out_path,
            model=model,
            size=size,
            quality=quality,
        )

    generated = 0
    workers = max_workers if max_workers is not None else IMAGE_WORKERS
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(_generate_one, prompt, out_path): (slide, rel)
            for slide, rel, out_path, prompt in tasks
        }
        for future in as_completed(future_map):
            slide, rel = future_map[future]
            future.result()
            image = slide.get("image") or {}
            if isinstance(image, dict):
                image["path"] = rel
                slide["image"] = image
            generated += 1

    from app.openai_cost import compute_image_cost

    return generated, compute_image_cost(model, size, generated)
