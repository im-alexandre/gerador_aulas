from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def render_prompt_template(template_path: str | Path, **kwargs) -> str:
    """Renderiza um template Jinja2 com variáveis fornecidas."""
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Template não encontrado: {path}")
    loader = FileSystemLoader(str(path.parent))
    env = Environment(
        loader=loader,
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template(path.name)
    return template.render(**kwargs).strip()
