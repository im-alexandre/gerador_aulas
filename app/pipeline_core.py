import logging
import time
from pathlib import Path

from app.browser import open_document
from app.gamma_api import (
    generate_content_from_template,
    get_gamma_url,
    get_generation_id,
    get_generation_status,
    get_status,
    parse_json,
    write_document_urls,
    write_last_response,
)
from app.gpt_cards import generate_cards_for_root


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [INFO] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def poll_generations(
    app_dir: Path,
    generation_map: dict[str, Path],
    max_wait_minutes: int,
):
    if not generation_map:
        log.info("Nenhuma geração para consultar.")
        return

    start = time.time()
    pending = set(generation_map.keys())

    while pending:
        completed = set()
        for generation_id in list(pending):
            response = get_generation_status(app_dir, generation_id)
            payload = parse_json(response)
            status = get_status(payload)
            status_lower = status.lower()
            log.info(f"Status {generation_id}: {status}")

            if status_lower == "completed":
                url = get_gamma_url(payload)
                material_dir = generation_map[generation_id]
                write_document_urls(material_dir, generation_id, url)
                open_document(url)
                completed.add(generation_id)
            elif status_lower in {"failed", "error", "canceled", "cancelled"}:
                raise RuntimeError(f"Falha na geração {generation_id}: {status}")

        pending -= completed
        if not pending:
            break

        if max_wait_minutes > 0:
            elapsed = time.time() - start
            if elapsed > max_wait_minutes * 60:
                raise TimeoutError("Tempo máximo de espera excedido.")

        time.sleep(2)

    log.info("Todas as gerações estão concluídas.")


def resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path


def run_pipeline(args):
    app_dir = Path(args.app_dir).resolve()
    course_dir = Path(args.course_dir).resolve()
    export_dir = resolve_path(course_dir, args.export_dir)
    prompt_md_path = resolve_path(app_dir, args.prompt_md)
    generated_cards = generate_cards_for_root(
        root=course_dir,
        prompt_md_path=prompt_md_path,
        model=args.model,
        export_dir=export_dir,
        only=args.only,
        force=args.force,
        exclude_dirs={
            "cards",
            "cards_exemplo",
        },
    )

    cards_dir = (
        resolve_path(course_dir, args.cards_dir) if args.cards_dir else export_dir
    )
    if generated_cards:
        cards_files = generated_cards
    else:
        cards_files = list(cards_dir.glob("*.md"))

    if not cards_files:
        log.info("Nenhum arquivo de cards encontrado.")
        return

    generation_map: dict[str, Path] = {}
    for card_path in cards_files:
        log.info(f"Enviando cards para Gamma: {card_path.name}")
        material_name = card_path.stem.replace("_card", "")
        material_dir = course_dir / material_name
        url_marker = material_dir / "gamma_urls.txt"
        if url_marker.exists() and not args.force:
            log.info(f"Pulando Gamma (já existe gamma_urls.txt): {material_dir.name}")
            continue
        response = generate_content_from_template(app_dir, card_path, args.folder_id)
        payload = parse_json(response)
        generation_id = get_generation_id(payload)
        write_last_response(
            app_dir / "output" / course_dir.name, response, generation_id
        )
        generation_map[generation_id] = material_dir

    poll_generations(
        app_dir=app_dir,
        generation_map=generation_map,
        max_wait_minutes=args.max_wait_minutes,
    )
