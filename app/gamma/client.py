from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests

from app.config.pipeline import GAMMA_POLL_INTERVAL_SECONDS, GAMMA_POLL_TIMEOUT_SECONDS
from app.gamma.config import load_gamma_config
from app.config.paths import APP_DIR


GAMMA_BASE_URL = "https://public-api.gamma.app/v1.0/generations"
GAMMA_FROM_TEMPLATE_URL = "https://public-api.gamma.app/v1.0/generations/from-template"


def _build_headers(cfg: dict[str, Any]) -> dict[str, str]:
    api_key = (cfg.get("api_key") or "").strip()
    cookie = (cfg.get("cookie") or "").strip()
    if not api_key or not cookie:
        raise ValueError("gamma_config.json precisa de api_key e cookie.")
    return {
        "X-API-KEY": api_key,
        "Cookie": cookie,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _build_payload(input_text: str, cfg: dict[str, Any], endpoint: str) -> dict[str, Any]:
    payload = dict(cfg.get("payload") or {})
    if endpoint == "from-template":
        instruction = (cfg.get("instruction") or "").strip()
        instruction_path = (cfg.get("instruction_path") or "").strip()
        if instruction_path:
            path = Path(instruction_path)
            if not path.is_absolute():
                path = APP_DIR / instruction_path
            instruction = path.read_text(encoding="utf-8").strip()
        if instruction:
            payload["prompt"] = f"{instruction}\n\n{input_text}".strip()
        else:
            payload["prompt"] = input_text

        gamma_id = (cfg.get("gamma_id") or "").strip()
        if gamma_id:
            payload["gammaId"] = gamma_id
        folder_ids = cfg.get("folder_ids") or cfg.get("folderIds")
        if isinstance(folder_ids, list) and folder_ids:
            payload["folderIds"] = folder_ids
    else:
        payload["inputText"] = input_text
        payload.setdefault("textMode", "generate")
        payload.setdefault("format", "presentation")
        payload.setdefault("cardSplit", "inputTextBreaks")
        payload.setdefault("cardOptions", {"dimensions": "16x9"})
        payload.setdefault(
            "imageOptions",
            {
                "style": "",
                "source": "aiGenerated",
                "model": "flux-kontext-fast",
            },
        )
    payload["exportAs"] = "pptx"
    return payload


def create_generation(input_text: str, cfg: dict[str, Any]) -> str:
    """Cria uma geracao no Gamma e retorna o generationId."""
    headers = _build_headers(cfg)
    endpoint = (cfg.get("endpoint") or "").strip().lower()
    payload = _build_payload(input_text, cfg, endpoint)
    url = GAMMA_FROM_TEMPLATE_URL if endpoint == "from-template" else GAMMA_BASE_URL
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    generation_id = data.get("generationId")
    if not generation_id:
        raise ValueError("Resposta do Gamma sem generationId.")
    return generation_id


def wait_for_export_url(
    generation_id: str,
    cfg: dict[str, Any],
    *,
    poll_interval: int | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """Aguarda o exportUrl ficar disponivel."""
    headers = _build_headers(cfg)
    interval = poll_interval or GAMMA_POLL_INTERVAL_SECONDS
    timeout = timeout_seconds or GAMMA_POLL_TIMEOUT_SECONDS
    deadline = time.monotonic() + timeout
    url = f"{GAMMA_BASE_URL}/{generation_id}"

    while time.monotonic() < deadline:
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        status = (data.get("status") or "").lower()
        export_url = data.get("exportUrl") or ""
        if status == "completed" and export_url:
            return data
        if status in {"failed", "canceled"}:
            raise RuntimeError(f"Gamma falhou: status={status}.")
        time.sleep(interval)

    raise TimeoutError("Timeout aguardando exportUrl do Gamma.")


def download_export(export_url: str, out_path: Path) -> None:
    """Baixa o PPTX exportado pelo Gamma."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(export_url, timeout=120)
    resp.raise_for_status()
    out_path.write_bytes(resp.content)


def generate_pptx_from_cards(
    input_text: str,
    out_path: Path,
    *,
    poll_interval: int | None = None,
    timeout_seconds: int | None = None,
) -> tuple[Path, int]:
    """Gera PPTX no Gamma a partir dos cards e salva localmente."""
    cfg = load_gamma_config()
    if not cfg:
        raise FileNotFoundError("gamma_config.json nao encontrado.")
    generation_id = create_generation(input_text, cfg)
    data = wait_for_export_url(
        generation_id,
        cfg,
        poll_interval=poll_interval,
        timeout_seconds=timeout_seconds,
    )
    credits = data.get("credits") or {}
    deducted = int(credits.get("deducted") or 0)
    export_url = data.get("exportUrl")
    if not export_url:
        raise RuntimeError("exportUrl nao retornado pelo Gamma.")
    download_export(export_url, out_path)
    return out_path, deducted
