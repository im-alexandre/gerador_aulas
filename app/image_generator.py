from __future__ import annotations

import base64
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from openai import OpenAI
from PIL import Image  # <- add Pillow

from app.config.paths import APP_DIR, USER_INPUT_IMAGE
from app.config.pipeline import (
    IMAGE_WORKERS,
    OPENAI_IMAGE_MODEL,
    OPENAI_IMAGE_SIZE,
    OPENAI_IMAGE_QUALITY,
)
from app.debug_payload import dump_payload
from app.logging_utils import log_step
from app.prompt_utils import render_prompt_template

log = logging.getLogger(__name__)

LIGHT_BG = "#F2F4F7"
DARK_BG = "#111827"


def _img_prompt_from_slide(slide: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """
    Retorna (prompt, theme, layout, style_profile, variation_id)
    """
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

    theme = random.choice(["light", "dark"])
    layout = random.choice(["linear", "radial", "grid", "split", "layered"])
    style_profile = random.choice(
        ["corporate_flat", "technical_glow", "architectural_blueprint"]
    )

    # "variador invisível" (não precisa fazer sentido, só mudar embedding)
    variation_id = str(random.randint(100000, 999999))

    prompt = render_prompt_template(
        APP_DIR / USER_INPUT_IMAGE,
        title=title,
        lead=lead,
        bullets_txt=bullets_txt,
        intent=intent,
        theme=theme,
        layout=layout,
        style_profile=style_profile,
        variation_id=variation_id,
    )

    return prompt, theme, layout, style_profile, variation_id


def _preview_text(text: str, limit: int = 200) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def _flatten_transparency(png_path: Path, *, bg_hex: str) -> None:
    """
    Se o PNG vier com alpha/transparência, achata num fundo sólido (bg_hex) e salva SEM alpha.
    """
    img = Image.open(png_path)

    # Se não tiver alpha, nada a fazer.
    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    )
    if not has_alpha:
        return

    rgba = img.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, bg_hex)
    out = Image.alpha_composite(bg, rgba).convert("RGB")
    out.save(png_path, format="PNG", optimize=True)


def generate_image_png(
    client: OpenAI,
    prompt: str,
    out_path: Path,
    *,
    model: str = OPENAI_IMAGE_MODEL,
    size: str = OPENAI_IMAGE_SIZE,
    quality: str | None = OPENAI_IMAGE_QUALITY,
    bg_hex: str = LIGHT_BG,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    if quality:
        payload["quality"] = quality

    dump_path = dump_payload(payload)
    log_step(
        log,
        out_path.parent.name,
        "generate_image_png",
        f"request_dump={dump_path}",
        level=logging.DEBUG,
    )

    img = client.images.generate(**payload)
    image_bytes = base64.b64decode(img.data[0].b64_json)
    out_path.write_bytes(image_bytes)

    # ✅ garante “sem transparência” mesmo que a API ignore o prompt
    _flatten_transparency(out_path, bg_hex=bg_hex)


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
    api_key_override: str | None = None,
) -> tuple[int, dict]:
    """
    Para cada slide standard com image.source="generated":
      - gera PNG
      - escreve em {course_dir}/{assets_dirname}/{nucleus_name}/gen_{slide_id}.png
      - injeta image.path no JSON (mantendo source/intent)
    """
    slides = plan.get("slides") or []
    if not isinstance(slides, list):
        return 0, {"model": model, "size": size, "count": 0, "cost_usd": 0}

    tasks: list[tuple[dict[str, Any], str, Path, str, str, str]] = []
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

        prompt, theme, _layout, _style, variation_id = _img_prompt_from_slide(slide)
        bg_hex = LIGHT_BG if theme == "light" else DARK_BG

        tasks.append((slide, rel, out_path, prompt, slide_id, bg_hex))

    if not tasks:
        return 0, {"model": model, "size": size, "count": 0, "cost_usd": 0}

    if not generate_images:
        reused = 0
        for slide, rel, out_path, _prompt, _slide_id, _bg_hex in tasks:
            if out_path.exists():
                image = slide.get("image") or {}
                if isinstance(image, dict):
                    image["path"] = rel
                    slide["image"] = image
                reused += 1
        return reused, {"model": model, "size": size, "count": 0, "cost_usd": 0}

    def _generate_one(prompt: str, out_path: Path, slide_id: str, bg_hex: str) -> None:
        log_step(
            log,
            nucleus_name,
            "generate_image_png",
            (
                "request: "
                f"model={model} "
                f"size={size} "
                f"quality={quality or 'default'} "
                f"slide_id={slide_id} "
                f"bg={bg_hex} "
                f"prompt_len={len(prompt)} "
                f'prompt_preview="{_preview_text(prompt)}"'
            ),
            level=logging.DEBUG,
        )

        if api_key_override:
            api_key = api_key_override.strip()
        else:
            with open("app/prompts/openai_api_key") as key_file:
                api_key = key_file.read().strip()

        client = OpenAI(api_key=api_key)
        generate_image_png(
            client=client,
            prompt=prompt,
            out_path=out_path,
            model=model,
            size=size,
            quality=quality,
            bg_hex=bg_hex,
        )

    generated = 0
    workers = max_workers if max_workers is not None else IMAGE_WORKERS

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(_generate_one, prompt, out_path, slide_id, bg_hex): (
                slide,
                rel,
            )
            for slide, rel, out_path, prompt, slide_id, bg_hex in tasks
        }

        for future in as_completed(future_map):
            slide, rel = future_map[future]
            future.result()
            image = slide.get("image") or {}
            if isinstance(image, dict):
                image["path"] = rel
                slide["image"] = image
            generated += 1

    return generated, {"model": model, "size": size, "count": generated, "cost_usd": 0}
