import argparse
import logging
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.config.paths import (
    APP_DIR,
    PROJECT_ROOT,
    PROMPT_MD,
    TEMPLATE_CATALOG,
    OPENAI_KEY_PATH,
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
from app.path_utils import (
    find_course_dir,
    resolve_prompt_path,
    resolve_template_id,
)
from app.roteiro_zip import distribute_roteiros, extract_roteiros_zip
from app.template_mapping import ensure_template_mapping, validate_template_layouts

root = Path(__file__).resolve().parent

log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--curso-dir", dest="course_dir")
    ap.add_argument(
        "--template-id",
        dest="template_id",
        required=True,
        help="ID do template (ex.: graduacao, tecnico).",
    )
    ap.add_argument(
        "--only",
        help="Processar apenas nucleos informados (separados por virgula).",
    )
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument(
        "--nucleus-workers",
        type=int,
        default=NUCLEUS_WORKERS,
        help="Numero maximo de nucleos processados em paralelo.",
    )
    ap.add_argument("--force", action="store_true")
    ap.add_argument(
        "--image-provider",
        choices=["gamma", "openai"],
        default="openai",
        help="Provedor de imagens: gamma ou openai.",
    )
    ap.add_argument(
        "--image-model",
        choices=["gpt-image-1-mini", "gpt-image-1.5"],
        default=OPENAI_IMAGE_MODEL,
        help="Modelo OpenAI para geracao de imagens.",
    )
    ap.add_argument(
        "--image-quality",
        choices=["low", "medium", "high"],
        default=OPENAI_IMAGE_QUALITY,
        help="Qualidade da imagem gerada.",
    )
    ap.add_argument(
        "--reuse-assets",
        action="store_true",
        help="Reaproveitar imagens geradas (nao chamar API de imagens).",
    )
    ap.add_argument("--verbose", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    sys.path.insert(0, str(PROJECT_ROOT))

    course_dir = (
        Path(args.course_dir).resolve()
        if args.course_dir
        else find_course_dir(PROJECT_ROOT, EXCLUDE_DIRS)
    )
    os.environ.setdefault("COURSE_DIR", str(course_dir))
    os.environ.setdefault("APP_DIR", str(APP_DIR))

    prompt_path = resolve_prompt_path(APP_DIR, PROMPT_MD)
    prompt_md = prompt_path.read_text(encoding="utf-8")

    template_id = (args.template_id or "").strip().lower()
    template_path = resolve_template_id(
        PROJECT_ROOT,
        template_id,
        TEMPLATE_CATALOG,
    )

    if template_id == "graduacao":
        image_size = "1024x1536"
    elif template_id == "tecnico":
        image_size = "1536x1024"
    else:
        image_size = OPENAI_IMAGE_SIZE

    if not template_path.exists():
        raise SystemExit(f"Template não encontrado: {template_path}")
    ensure_template_mapping(template_path, force=args.force)
    validate_template_layouts(template_path)

    log_step(
        log, course_dir.name, "split_course_content", "Extraindo nucleos conceituais"
    )
    split_course_content(course_dir, force=args.force)
    log_step(log, course_dir.name, "extract_roteiros_zip", "Importando roteiros")
    extract_roteiros_zip(course_dir, force=args.force)
    log_step(log, course_dir.name, "distribute_roteiros", "Distribuindo roteiros")
    distribute_roteiros(course_dir, force=args.force)

    nuclei: list[Path] = []
    only_set = None
    if args.only:
        only_set = {name.strip() for name in args.only.split(",") if name.strip()}
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

    nucleus_workers = int(args.nucleus_workers)
    if nucleus_workers <= 0:
        raise SystemExit("--nucleus-workers deve ser >= 1.")

    with ThreadPoolExecutor(max_workers=nucleus_workers) as executor:
        future_map = {
            executor.submit(
                process_nucleus_dir,
                nucleus_dir=entry,
                course_dir=course_dir,
                prompt_md=prompt_md,
                model=args.model,
                image_model=args.image_model,
                image_size=image_size,
                image_quality=args.image_quality,
                template_path=template_path,
                force=args.force,
                generate_images=not args.reuse_assets,
                image_provider=args.image_provider,
                api_key_path=OPENAI_KEY_PATH,
            ): entry.name
            for entry in nuclei
        }

        for future in as_completed(future_map):
            name = future_map[future]
            try:
                future.result()
            except Exception:
                log.exception("[%s] Falha no processamento", name)
                raise

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


if __name__ == "__main__":
    main()
