from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path

from openai import OpenAI

from app.config.paths import APP_DIR, USER_INPUT_SLIDES
from app.debug_payload import dump_payload
from app.logging_utils import log_step
from app.prompt_utils import render_prompt_template


from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


def docx_chars(path):
    d = Document(path)
    paras = [p.text.strip() for p in d.paragraphs if p.text and p.text.strip()]
    return len("\n".join(paras))


def iter_block_items(parent):
    """Itera por parágrafos e tabelas mantendo a ordem no DOCX."""
    for child in parent.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def extract_docx_text(path: Path) -> str:
    """Extrai texto do DOCX preservando ordem de parágrafos e tabelas."""
    doc = Document(path)
    chunks: list[str] = []
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                chunks.append(text)
            continue
        for row in block.rows:
            cells = [cell.text.strip() for cell in row.cells]
            cells = [cell for cell in cells if cell]
            if cells:
                chunks.append(" | ".join(cells))
    return "\n".join(chunks).strip()


log = logging.getLogger(__name__)
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 2


def with_backoff(fn, *args, **kwargs):
    """Executa uma função com backoff exponencial e jitter."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            is_last = attempt == MAX_RETRIES
            if is_last:
                raise
            delay = min(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)), 30)
            delay += random.uniform(0, 0.5)
            log.warning(
                f"(with_backoff) ({fn}) Falha na API (tentativa {attempt}/{MAX_RETRIES}): {exc}"
            )
            log.warning(
                f"(with_backoff) Aguardando {delay:.1f}s antes de tentar novamente."
            )
            time.sleep(delay)


def upload_file(client: OpenAI, path: Path) -> str:
    """Faz upload de um arquivo para a API e retorna o file_id."""
    try:
        size = path.stat().st_size
    except OSError:
        size = -1
    log_step(
        log,
        path.parent.name,
        "upload_file",
        f"request: file={path.name} size_bytes={size} purpose=user_data",
        level=logging.DEBUG,
    )
    with open(path, "rb") as fh:
        f = with_backoff(client.files.create, file=fh, purpose="user_data")
    return f.id


def call_llm(
    client: OpenAI,
    model: str,
    instructions: str,
    file_ids: list[str],
    user_input: str,
    directory: str,
) -> tuple[str, dict]:
    """Chama o modelo com arquivos anexados e retorna o texto da resposta."""
    tool_label = "code_interpreter"
    log_step(
        log,
        directory,
        "call_llm",
        (
            "request: "
            f"model={model} "
            f"files={len(file_ids)} "
            f"instructions_len={len(instructions or '')} "
            f"input_len={len(user_input or '')} "
            f"tool={tool_label}"
        ),
        level=logging.DEBUG,
    )
    payload = {
        "model": model,
        "instructions": instructions,
        "input": user_input,
    }
    payload["tools"] = [
        {
            "type": "code_interpreter",
            "container": {
                "type": "auto",
                "file_ids": file_ids,
            },
        }
    ]
    payload["tool_choice"] = {"type": "code_interpreter"}
    dump_path = dump_payload(payload)
    log_step(
        log,
        directory,
        "call_llm",
        f"request_dump={dump_path}",
        level=logging.DEBUG,
    )
    resp = with_backoff(
        client.responses.create,
        **payload,
    )
    return (resp.output_text or "").strip()


def extract_json(text: str) -> dict:
    """Extrai JSON da resposta, mesmo quando houver texto extra."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def parse_json_strict(text: str) -> dict:
    """Exige JSON puro (sem texto adicional) e parseia."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Resposta não contém JSON válido.")
    if text[:start].strip() or text[end + 1 :].strip():
        raise ValueError("Resposta contém texto extra fora do JSON.")
    return json.loads(text[start : end + 1])


def generate_plan(
    client: OpenAI,
    prompt_md: str,
    content_docx: Path,
    roteiro_docx: Path,
    model: str,
    directory: str,
    strict_json: bool = False,
) -> dict:
    """Gera o plano de slides (JSON) a partir de conteúdo e roteiro."""
    content_id = upload_file(client, content_docx)
    roteiro_id = upload_file(client, roteiro_docx)
    file_ids = [content_id, roteiro_id]
    user_input = render_prompt_template(APP_DIR / USER_INPUT_SLIDES)
    log_step(
        log,
        directory,
        "upload_file",
        "Arquivos de conteudo + roteiro incluidos no pipeline",
    )
    log_step(log, directory, "call_llm", "LLM processando dados")
    response_text = call_llm(
        client=client,
        model=model,
        instructions=prompt_md,
        file_ids=file_ids,
        directory=directory,
        user_input=user_input,
    )
    if strict_json:
        return parse_json_strict(response_text)
    return extract_json(response_text)


def generate_plan_for_dir(
    api_key_override: str | None,
    content_docx: Path,
    roteiro_docx: Path,
    prompt_md: str,
    model: str,
    output_json: Path,
    force: bool = False,
    strict_json: bool = False,
    use_code_interpreter: bool = True,
) -> dict | None:
    """Gera e salva o JSON do plano para um diretório de núcleo."""
    if output_json.exists() and not force:
        log_step(
            log,
            content_docx.parent.name,
            "generate_plan_for_dir",
            "Plano existente (reaproveitado)",
        )
        return None

    if api_key_override:
        api_key = api_key_override.strip()
    else:
        with open("app/prompts/openai_api_key") as key_file:
            api_key = key_file.read().strip()

    client = OpenAI(api_key=api_key)
    plan = generate_plan(
        client=client,
        prompt_md=prompt_md,
        content_docx=content_docx,
        roteiro_docx=roteiro_docx,
        model=model,
        directory=content_docx.parent.name,
        strict_json=strict_json,
    )
    log_step(
        log,
        content_docx.parent.name,
        "generate_plan_for_dir",
        "Formulando abstracao dos slides",
    )
    output_json.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_step(
        log,
        content_docx.parent.name,
        "generate_plan_for_dir",
        f"Plano gerado: {output_json}",
        level=logging.DEBUG,
    )
    return plan
