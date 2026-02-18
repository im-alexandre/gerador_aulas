from __future__ import annotations

import os
from pathlib import Path


def find_course_dir(root: Path, exclude_dirs: set[str]) -> Path:
    """Resolve o diretório de curso pela env ou pela raiz do projeto."""
    env_dir = os.getenv("COURSE_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in exclude_dirs:
            continue
        return entry.resolve()

    raise SystemExit("Nenhum diretório de curso encontrado na raiz.")


def resolve_prompt_path(app_dir: Path, prompt_md: str) -> Path:
    """Resolve o caminho do prompt a partir do APP_DIR."""
    prompt_path = Path(prompt_md)
    if prompt_path.is_absolute():
        return prompt_path
    return app_dir / prompt_path


def resolve_template_path(project_root: Path, template_pptx: str) -> Path:
    """Resolve o caminho do template PPTX."""
    template_path = Path(template_pptx)
    if template_path.is_absolute():
        return template_path
    return project_root / template_path


def resolve_template_id(project_root: Path, template_id: str, catalog: dict[str, str]) -> Path:
    """Resolve o caminho do template PPTX a partir do ID."""
    template_key = (template_id or "").strip().lower()
    if not template_key:
        raise SystemExit("Template ID ausente. Use --template-id.")
    template_rel = catalog.get(template_key)
    if not template_rel:
        valid = ", ".join(sorted(catalog.keys()))
        raise SystemExit(f"Template ID inválido: {template_id}. Válidos: {valid}")
    return resolve_template_path(project_root, template_rel)
