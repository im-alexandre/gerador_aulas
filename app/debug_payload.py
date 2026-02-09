from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from app.config.paths import PROJECT_ROOT


def dump_payload(payload: dict[str, Any], out_dir: str | Path | None = None) -> Path:
    target_dir = Path(out_dir) if out_dir is not None else PROJECT_ROOT / ".debug_llm"
    target_dir.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = target_dir / f"{ts}_{digest}.json"
    path.write_text(raw, encoding="utf-8")
    return path
