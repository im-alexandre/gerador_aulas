import argparse
import logging
import os
import sys
import json
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.config.paths import (
    APP_DIR,
    PROJECT_ROOT,
    PROMPT_MD,
    TEMPLATE_PPTX,
)
from app.config.pipeline import (
    DEFAULT_MODEL,
    EXCLUDE_DIRS,
    NUCLEUS_WORKERS,
    GAMMA_COST_BRL_PER_CREDIT,
    USE_CODE_INTERPRETER,
    OPENAI_IMAGE_MODEL,
    OPENAI_IMAGE_SIZE,
    OPENAI_IMAGE_QUALITY,
)
from app.path_utils import (
    find_course_dir,
    resolve_prompt_path,
    resolve_template_path,
)
from app.nucleus_processor import process_nucleus_dir
from app.roteiro_zip import extract_roteiros_zip, distribute_roteiros
from app.content_splitter import split_course_content
from app.template_mapping import ensure_template_mapping
from app.logging_utils import setup_logging, log_step


EXPECTED_ROOT = Path(__file__).resolve().parent
CWD = Path.cwd().resolve()

if CWD != EXPECTED_ROOT:
    print(
        "[ERRO] Programa rodando fora do root esperado\n"
        f"  CWD atual: {CWD}\n"
        f"  Root esperado: {EXPECTED_ROOT}",
        file=sys.stderr,
    )
    sys.exit(2)


REQUIRED = [
    "app.py",
    "app/prompts/prompt_gpt.md",
    "app/gpt_planner.py",
]

root = Path(__file__).resolve().parent

missing = [p for p in REQUIRED if not (root / p).exists()]
if missing:
    raise SystemExit(
        "Root incorreto ou projeto incompleto. Faltando:\n" + "\n".join(missing)
    )


log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--curso-dir", dest="course_dir")
    ap.add_argument(
        "--template",
        dest="template_path",
        help="Caminho do template PPTX (override do default).",
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
        "--image-size",
        choices=["1024x1024", "1024x1536", "1536x1024"],
        default=OPENAI_IMAGE_SIZE,
        help="Tamanho da imagem gerada.",
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
    ci_group = ap.add_mutually_exclusive_group()
    ci_group.add_argument(
        "--use-code-interpreter",
        dest="use_code_interpreter",
        action="store_true",
        help="Forcar uso do code interpreter para ler DOCX.",
    )
    ci_group.add_argument(
        "--no-code-interpreter",
        dest="use_code_interpreter",
        action="store_false",
        help="Nao usar code interpreter; extrai DOCX localmente.",
    )
    ap.set_defaults(use_code_interpreter=USE_CODE_INTERPRETER)
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

    template_path = (
        Path(args.template_path).resolve()
        if args.template_path
        else resolve_template_path(PROJECT_ROOT, TEMPLATE_PPTX)
    )
    ensure_template_mapping(template_path, force=args.force)

    log_step(
        log, course_dir.name, "split_course_content", "Extraindo nucleos conceituais"
    )
    split_course_content(course_dir, force=args.force)
    log_step(log, course_dir.name, "extract_roteiros_zip", "Importando roteiros")
    extract_roteiros_zip(course_dir, force=args.force)
    log_step(log, course_dir.name, "distribute_roteiros", "Distribuindo roteiros")
    distribute_roteiros(course_dir, force=args.force)

    nuclei = []
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

    gamma_total = 0
    gamma_by_nucleus: dict[str, int] = {}
    openai_total = 0.0
    openai_by_nucleus: dict[str, dict] = {}
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
                image_size=args.image_size,
                image_quality=args.image_quality,
                template_path=template_path,
                force=args.force,
                use_code_interpreter=args.use_code_interpreter,
                generate_images=not args.reuse_assets,
                image_provider=args.image_provider,
            ): entry.name
            for entry in nuclei
        }
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                result = future.result() or {}
                deducted = int(result.get("gamma_deducted") or 0)
                gamma_total += deducted
                gamma_by_nucleus[name] = deducted
                llm_cost = result.get("openai_llm") or {}
                img_cost = result.get("openai_images") or {}
                nucleus_cost = float(llm_cost.get("cost_usd") or 0) + float(
                    img_cost.get("cost_usd") or 0
                )
                openai_total += nucleus_cost
                openai_by_nucleus[name] = {
                    "llm": llm_cost,
                    "images": img_cost,
                    "total_cost_usd": round(nucleus_cost, 6),
                }
            except Exception as exc:
                log.error(f"[{name}] Falha no processamento: {exc}")
                raise

    cost_summary: dict[str, object] = {
        "course_dir": str(course_dir),
        "gamma": {
            "total_deducted": gamma_total,
            "cost_brl_per_credit": GAMMA_COST_BRL_PER_CREDIT,
            "total_cost_brl": round(gamma_total * GAMMA_COST_BRL_PER_CREDIT, 2),
            "by_nucleus": gamma_by_nucleus,
        },
        "openai": {
            "total_cost_usd": round(openai_total, 6),
            "by_nucleus": openai_by_nucleus,
        },
    }

    if gamma_by_nucleus:
        summary_path = course_dir / "gamma_credits.json"
        by_nucleus_cost = {
            name: round(credits * GAMMA_COST_BRL_PER_CREDIT, 2)
            for name, credits in gamma_by_nucleus.items()
        }
        summary_path.write_text(
            json.dumps(
                {
                    "course_dir": str(course_dir),
                    "total_deducted": gamma_total,
                    "cost_brl_per_credit": GAMMA_COST_BRL_PER_CREDIT,
                    "total_cost_brl": round(gamma_total * GAMMA_COST_BRL_PER_CREDIT, 2),
                    "by_nucleus": gamma_by_nucleus,
                    "by_nucleus_cost_brl": by_nucleus_cost,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        log_step(
            log,
            course_dir.name,
            "cost_summary",
            f"Gamma creditos: {gamma_total}",
            level=logging.DEBUG,
        )
        log_step(
            log,
            course_dir.name,
            "cost_summary",
            f"Gamma custo estimado: R$ {gamma_total * GAMMA_COST_BRL_PER_CREDIT:.2f}",
            level=logging.DEBUG,
        )

    if openai_by_nucleus:
        openai_path = course_dir / "openai_cost.json"
        openai_path.write_text(
            json.dumps(
                {
                    "course_dir": str(course_dir),
                    "total_cost_usd": round(openai_total, 6),
                    "by_nucleus": openai_by_nucleus,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        log_step(
            log,
            course_dir.name,
            "cost_summary",
            f"OpenAI custo estimado: {openai_total:.6f} USD",
            level=logging.DEBUG,
        )

    dist_dir = course_dir / "dist"
    if dist_dir.exists():
        for item in dist_dir.glob("*.pptx"):
            item.unlink()
    dist_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for entry in nuclei:
        pptx_path = entry / f"{entry.name}.pptx"
        if not pptx_path.exists():
            continue
        shutil.copy2(pptx_path, dist_dir / pptx_path.name)
        copied += 1
    log_step(log, course_dir.name, "copy_dist", "Apresentacoes prontas")

    costs_dir = PROJECT_ROOT / "custos"
    costs_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(costs_dir.glob(f"{course_dir.name}_*_custo.json"))
    next_idx = len(existing) + 1
    summary_path = costs_dir / f"{course_dir.name}_{next_idx}_custo.json"
    summary_path.write_text(
        json.dumps(cost_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
