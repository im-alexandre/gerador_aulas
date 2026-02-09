from __future__ import annotations

import json
import logging
import os
import random
import time
from pathlib import Path

from openai import OpenAI

from app.debug_payload import dump_payload
from app.logging_utils import log_step


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
                f"(with_backoff) Falha na API (tentativa {attempt}/{MAX_RETRIES}): {exc}"
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


def _extract_usage(resp) -> dict:
    usage: dict = {}
    raw = getattr(resp, "usage", None)
    if raw is None and isinstance(resp, dict):
        raw = resp.get("usage")
    if raw is None:
        return usage

    def _get(obj, key: str):
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    input_tokens = _get(raw, "input_tokens")
    input_tokens_cached = _get(raw, "input_tokens_cached")
    output_tokens = _get(raw, "output_tokens")
    total_tokens = _get(raw, "total_tokens")

    if input_tokens is None:
        input_tokens = _get(raw, "prompt_tokens")
    if output_tokens is None:
        output_tokens = _get(raw, "completion_tokens")
    if input_tokens_cached is None:
        input_tokens_cached = _get(raw, "prompt_tokens_cached")

    if input_tokens is not None:
        usage["prompt_tokens"] = int(input_tokens)
    if input_tokens_cached is not None:
        usage["prompt_cached_tokens"] = int(input_tokens_cached)
    if output_tokens is not None:
        usage["completion_tokens"] = int(output_tokens)
    if total_tokens is not None:
        usage["total_tokens"] = int(total_tokens)
    elif input_tokens is not None and output_tokens is not None:
        usage["total_tokens"] = int(input_tokens) + int(output_tokens)

    return usage


def call_llm(
    client: OpenAI,
    model: str,
    instructions: str,
    file_ids: list[str],
    user_input: str,
    directory: str,
    use_code_interpreter: bool,
) -> tuple[str, dict]:
    """Chama o modelo com arquivos anexados e retorna o texto da resposta."""
    tool_label = "code_interpreter" if use_code_interpreter else "none"
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
    if use_code_interpreter:
        payload["tools"] = [
            {
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "file_ids": file_ids,
                },
            }
        ]
        payload["tool_choice"] = "auto"
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
    usage = _extract_usage(resp)
    return (resp.output_text or "").strip(), usage


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
    use_code_interpreter: bool = True,
) -> tuple[dict, dict]:
    """Gera o plano de slides (JSON) a partir de conteúdo e roteiro."""
    if use_code_interpreter:
        content_id = upload_file(client, content_docx)
        roteiro_id = upload_file(client, roteiro_docx)
        file_ids = [content_id, roteiro_id]
        user_input = (
            "Use o code_interpreter para abrir e ler os 2 DOCX anexados.\n"
            "Extraia a ordem de tópicos do DOCX de CONTEÚDO.\n"
            "O ROT é apenas referência editorial (título e ordem macro).\n"
            "É PROIBIDO reutilizar exemplos do prompt.\n"
            "Se um conceito não estiver no DOCX, não invente.\n"
            "Retorne APENAS JSON válido conforme o contrato."
        )
        log_step(
            log,
            directory,
            "upload_file",
            "Arquivos de conteudo + roteiro incluidos no pipeline",
        )
        log_step(log, directory, "call_llm", "LLM processando dados (code_interpreter)")
    else:
        content_text = extract_docx_text(content_docx)
        roteiro_text = extract_docx_text(roteiro_docx)
        file_ids = []
        user_input = (
            "Os textos extraidos dos DOCX seguem abaixo. Use-os diretamente.\n"
            "NAO chame ferramentas.\n"
            "Extraia a ordem de topicos do TEXTO de CONTEUDO.\n"
            "O ROT é apenas referencia editorial (titulo e ordem macro).\n"
            "É PROIBIDO reutilizar exemplos do prompt.\n"
            "Se um conceito nao estiver no texto, nao invente.\n"
            "Retorne APENAS JSON valido conforme o contrato.\n\n"
            "CONTEUDO_DOCX:\n"
            "<<<\n"
            f"{content_text}\n"
            ">>>\n\n"
            "ROTEIRO_DOCX:\n"
            "<<<\n"
            f"{roteiro_text}\n"
            ">>>"
        )
        log_step(
            log,
            directory,
            "call_llm",
            "LLM processando dados (texto inline)",
        )
    response_text, usage = call_llm(
        client=client,
        model=model,
        instructions=prompt_md,
        file_ids=file_ids,
        directory=directory,
        user_input=user_input,
        use_code_interpreter=use_code_interpreter,
    )
    if strict_json:
        return parse_json_strict(response_text), usage
    return extract_json(response_text), usage


def generate_plan_for_dir(
    content_docx: Path,
    roteiro_docx: Path,
    prompt_md: str,
    model: str,
    output_json: Path,
    force: bool = False,
    strict_json: bool = False,
    use_code_interpreter: bool = True,
) -> tuple[dict | None, dict | None]:
    """Gera e salva o JSON do plano para um diretório de núcleo."""
    if output_json.exists() and not force:
        log_step(
            log,
            content_docx.parent.name,
            "generate_plan_for_dir",
            "Plano existente (reaproveitado)",
        )
        return None, None
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Defina OPENAI_API_KEY.")

    client = OpenAI()
    plan, usage = generate_plan(
        client=client,
        prompt_md=prompt_md,
        content_docx=content_docx,
        roteiro_docx=roteiro_docx,
        model=model,
        directory=content_docx.parent.name,
        strict_json=strict_json,
        use_code_interpreter=use_code_interpreter,
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
    return plan, usage
