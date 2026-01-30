import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


def resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path


def load_configs(
    base_dir: Path,
    config_path: Path | None = None,
    api_config_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    config_path = config_path or base_dir / "config" / "config.json"
    api_config_path = api_config_path or base_dir / "config" / "api_config.json"

    with open(config_path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    with open(api_config_path, "r", encoding="utf-8") as api_config_file:
        api_config = json.load(api_config_file)

    api_key_path = resolve_path(base_dir, config["api_key_path"])
    api_key = api_key_path.read_text(encoding="utf-8").strip()

    return config, api_config, api_key


def build_headers(api_config: dict[str, Any], api_key: str) -> dict[str, str]:
    headers = dict(api_config.get("headers", {}))
    headers["X-API-KEY"] = api_key
    return headers


def build_body(
    api_config: dict[str, Any],
    prompt: str,
    folder_id: str | None = None,
) -> dict[str, Any]:
    body = dict(api_config.get("body", {}))
    body["prompt"] = prompt
    if folder_id:
        body["folderIds"] = [folder_id]
    return body


def generate_content_from_template(
    base_dir: Path,
    cards_path: Path,
    folder_id: str | None = None,
) -> requests.Response:
    config, api_config, api_key = load_configs(base_dir)
    headers = build_headers(api_config, api_key)

    instructions_path = resolve_path(base_dir, config["instructions_path"])
    instrucoes_md = instructions_path.read_text(encoding="utf-8").strip()
    cards_md = cards_path.read_text(encoding="utf-8").strip()
    prompt_final = f"{instrucoes_md}\n\n{cards_md}"

    body = build_body(api_config, prompt_final, folder_id)
    response = requests.post(config["url"], headers=headers, json=body)
    return response


def write_last_response(
    output_dir: Path,
    response: requests.Response,
    generation_id: str | None = None,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "saida.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"[{timestamp}] status={response.status_code}"
    if generation_id:
        header += f" generation_id={generation_id}"
    with open(output_path, "a", encoding="utf-8") as fp:
        fp.write(f"{header}\n{response.text}\n\n")


def parse_json(response: requests.Response) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return {}


def get_generation_id(payload: dict[str, Any]) -> str:
    generation_id = payload.get("generationId")
    if isinstance(generation_id, str) and generation_id:
        return generation_id
    raise KeyError("generationId não encontrado na resposta.")


def get_generation_status(base_dir: Path, generation_id: str) -> requests.Response:
    config, api_config, api_key = load_configs(base_dir)
    headers = build_headers(api_config, api_key)
    url = f"{config['url'].rsplit('/', 1)[0]}/{generation_id}"
    return requests.get(url, headers=headers)


def get_status(payload: dict[str, Any]) -> str:
    status = payload.get("status")
    if isinstance(status, str) and status:
        return status
    raise KeyError("status não encontrado na resposta.")


def get_gamma_url(payload: dict[str, Any]) -> str:
    gamma_url = payload.get("gammaUrl")
    if isinstance(gamma_url, str) and gamma_url:
        return gamma_url
    raise KeyError("gammaUrl não encontrado na resposta.")


def write_document_urls(material_dir: Path, generation_id: str, url: str):
    material_dir.mkdir(parents=True, exist_ok=True)
    output_path = material_dir / "gamma_urls.txt"
    with open(output_path, "a", encoding="utf-8") as fp:
        fp.write(f"generation_id={generation_id}\n")
        fp.write(f"{url}\n")
        fp.write("\n")
