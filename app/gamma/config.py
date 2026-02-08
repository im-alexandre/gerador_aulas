from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.paths import APP_DIR


GAMMA_CONFIG_PATH = APP_DIR / "config" / "gamma_config.json"


def load_gamma_config(path: Path | None = None) -> dict[str, Any]:
    """Carrega o JSON de configuracao do Gamma."""
    cfg_path = path or GAMMA_CONFIG_PATH
    if not cfg_path.exists():
        return {}
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return data
