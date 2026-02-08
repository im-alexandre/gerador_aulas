from __future__ import annotations

import json
import logging
import os
import random
import time
from pathlib import Path

from openai import OpenAI


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [INFO] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
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
            log.warning(f"Falha na API (tentativa {attempt}/{MAX_RETRIES}): {exc}")
            log.warning(f"Aguardando {delay:.1f}s antes de tentar novamente.")
            time.sleep(delay)


def upload_file(client: OpenAI, path: Path) -> str:
    """Faz upload de um arquivo para a API e retorna o file_id."""
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
) -> tuple[str, dict]:
    """Chama o modelo com arquivos anexados e retorna o texto da resposta."""
    log.info(f"[{directory}] Chamando o LLM")
    resp = with_backoff(
        client.responses.create,
        model=model,
        instructions=instructions,
        tools=[
            {
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "file_ids": file_ids,
                },
            }
        ],
        tool_choice={"type": "code_interpreter"},
        input=user_input,
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
) -> tuple[dict, dict]:
    """Gera o plano de slides (JSON) a partir de conteúdo e roteiro."""
    content_id = upload_file(client, content_docx)
    roteiro_id = upload_file(client, roteiro_docx)
    response_text, usage = call_llm(
        client=client,
        model=model,
        instructions=prompt_md,
        file_ids=[content_id, roteiro_id],
        user_input="Gere o JSON do plano de slides conforme o contrato.",
        directory=directory,
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
) -> tuple[dict | None, dict | None]:
    """Gera e salva o JSON do plano para um diretório de núcleo."""
    if output_json.exists() and not force:
        log.info(f"[{content_docx.parent.name}] JSON ja existe: {output_json.name}")
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
    )
    output_json.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(f"[{content_docx.parent.name}] JSON salvo: {output_json}")
    return plan, usage
