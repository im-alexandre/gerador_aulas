import argparse
from pathlib import Path

from app.config.pipeline import (
    DEFAULT_MODEL,
    NUCLEUS_WORKERS,
    OPENAI_IMAGE_MODEL,
    OPENAI_IMAGE_QUALITY,
)
from app.runner import RunConfig, run_pipeline


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
    course_dir = Path(args.course_dir).resolve() if args.course_dir else None
    if course_dir is None:
        raise SystemExit("--curso-dir é obrigatório.")

    only_set = None
    if args.only:
        only_set = {name.strip() for name in args.only.split(",") if name.strip()}

    config = RunConfig(
        course_dir=course_dir,
        template_id=args.template_id,
        only=only_set,
        model=args.model,
        nucleus_workers=args.nucleus_workers,
        force=args.force,
        image_provider=args.image_provider,
        image_model=args.image_model,
        image_quality=args.image_quality,
        reuse_assets=args.reuse_assets,
        verbose=args.verbose,
        openai_api_key=None,
    )
    run_pipeline(config=config)


if __name__ == "__main__":
    main()
