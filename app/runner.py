from __future__ import annotations

import logging
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from openai import OpenAI

from app.config.paths import (
    APP_DIR,
    PROJECT_ROOT,
    PROMPT_MD,
    TEMPLATE_CATALOG,
)
from app.config.pipeline import (
    DEFAULT_MODEL,
    EXCLUDE_DIRS,
    NUCLEUS_WORKERS,
    OPENAI_IMAGE_MODEL,
    OPENAI_IMAGE_QUALITY,
    OPENAI_IMAGE_SIZE,
)
from app.content_splitter import split_course_content
from app.logging_utils import log_step, setup_logging
from app.nucleus_processor import process_nucleus_dir
from app.path_utils import resolve_prompt_path, resolve_template_id
from app.roteiro_zip import distribute_roteiros, extract_roteiros_zip
from app.template_mapping import ensure_template_mapping, validate_template_layouts

log = logging.getLogger(__name__)


@dataclass
class RunConfig:
    course_dir: Path
    template_id: str
    only: set[str] | None = None
    model: str = DEFAULT_MODEL
    nucleus_workers: int = NUCLEUS_WORKERS
    force: bool = False
    image_provider: str = "openai"
    image_model: str = OPENAI_IMAGE_MODEL
    image_quality: str | None = OPENAI_IMAGE_QUALITY
    reuse_assets: bool = False
    verbose: bool = False
    openai_api_key: str | None = None


def _resolve_image_size(template_id: str) -> str:
    template_key = (template_id or "").strip().lower()
    if template_key == "graduacao":
        return "1024x1536"
    if template_key == "tecnico":
        return "1536x1024"
    return OPENAI_IMAGE_SIZE


def run_pipeline(
    config: RunConfig,
    progress_cb: Callable[[int, int, str], None] | None = None,
    log_cb: Callable[[str], None] | None = None,
    cancel_event=None,
) -> None:
    setup_logging(config.verbose)
    sys.path.insert(0, str(PROJECT_ROOT))

    course_dir = config.course_dir.resolve()
    os.environ.setdefault("COURSE_DIR", str(course_dir))
    os.environ.setdefault("APP_DIR", str(APP_DIR))

    prompt_path = resolve_prompt_path(APP_DIR, PROMPT_MD)
    prompt_md = prompt_path.read_text(encoding="utf-8")

    template_id = (config.template_id or "").strip().lower()
    template_path = resolve_template_id(
        PROJECT_ROOT,
        template_id,
        TEMPLATE_CATALOG,
    )
    if not template_path.exists():
        raise SystemExit(f"Template não encontrado: {template_path}")
    ensure_template_mapping(template_path, force=config.force)
    validate_template_layouts(template_path)

    image_size = _resolve_image_size(template_id)

    def _log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    log_step(
        log, course_dir.name, "split_course_content", "Extraindo nucleos conceituais"
    )
    _log("Extraindo núcleos conceituais...")
    split_course_content(course_dir, force=config.force)
    log_step(log, course_dir.name, "extract_roteiros_zip", "Importando roteiros")
    _log("Importando roteiros...")
    extract_roteiros_zip(course_dir, force=config.force)
    log_step(log, course_dir.name, "distribute_roteiros", "Distribuindo roteiros")
    _log("Distribuindo roteiros...")
    distribute_roteiros(course_dir, force=config.force)

    nuclei: list[Path] = []
    only_set = config.only
    for entry in course_dir.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in EXCLUDE_DIRS:
            continue
        if only_set is not None and entry.name not in only_set:
            continue
        nuclei.append(entry)

    nucleus_workers = int(config.nucleus_workers)
    if nucleus_workers <= 0:
        raise SystemExit("--nucleus-workers deve ser >= 1.")

    total = len(nuclei)
    completed = 0

    with ThreadPoolExecutor(max_workers=nucleus_workers) as executor:
        future_map = {}
        for entry in nuclei:
            if cancel_event is not None and cancel_event.is_set():
                _log("Cancelamento solicitado. Parando envio de novos núcleos.")
                break
            future = executor.submit(
                process_nucleus_dir,
                nucleus_dir=entry,
                course_dir=course_dir,
                prompt_md=prompt_md,
                model=config.model,
                image_model=config.image_model,
                image_size=image_size,
                image_quality=config.image_quality,
                template_path=template_path,
                force=config.force,
                generate_images=not config.reuse_assets,
                image_provider=config.image_provider,
                api_key_override=config.openai_api_key,
            )
            future_map[future] = entry.name

        for future in as_completed(future_map):
            name = future_map[future]
            try:
                future.result()
                _log(f"[{name}] concluído")
            except Exception:
                log.exception("[%s] Falha no processamento", name)
                _log(f"[{name}] falha no processamento")
                raise
            completed += 1
            if progress_cb:
                progress_cb(completed, total, name)

            if cancel_event is not None and cancel_event.is_set():
                _log("Cancelamento solicitado. Aguardando tarefas em andamento.")

    dist_dir = course_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    for item in dist_dir.glob("*.pptx"):
        item.unlink()

    copied = 0
    for entry in nuclei:
        pptx_path = entry / f"{entry.name}.pptx"
        if not pptx_path.exists():
            continue
        shutil.copy2(pptx_path, dist_dir / pptx_path.name)
        copied += 1

    log_step(log, course_dir.name, "copy_dist", f"Apresentacoes prontas ({copied})")
    _log(f"Apresentações prontas ({copied}).")
    client = OpenAI(api_key=config.openai_api_key)
    files = client.files.list()
    _log("Deletando arquivos da nuvem OpenAi")
    for f in files:
        _log(f"Deletando arquivo: {f.filename}")
        log_step(
            log, course_dir.name, "deleta_arquivos", f"Deletando arquivo {f.filename}"
        )
        client.files.delete(f.id)
    _log(f"{len(list(files))} Arquivos deletados")
