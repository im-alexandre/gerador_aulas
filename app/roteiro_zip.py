from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from zipfile import ZipFile

from app.config.paths import ROTEIROS_DIRNAME
from app.config.pipeline import ROTEIRO_PATTERN


log = logging.getLogger(__name__)
ROTEIRO_REGEX = re.compile(ROTEIRO_PATTERN, re.IGNORECASE)


def extract_roteiros_zip(course_dir: Path, force: bool) -> list[Path]:
    """Extrai docx de zips de roteiros para a pasta roteiros."""
    zips = list(course_dir.glob("*.zip"))
    if not zips:
        return []

    roteiros_dir = course_dir / ROTEIROS_DIRNAME
    roteiros_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []

    for zip_path in zips:
        with ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if not info.filename.lower().endswith(".docx"):
                    continue
                target = roteiros_dir / Path(info.filename).name
                if target.exists() and not force:
                    continue
                with zf.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.append(target)

    return extracted


def distribute_roteiros(course_dir: Path, force: bool) -> None:
    """Move roteiros extraídos para o diretório de núcleo correto."""
    roteiros_dir = course_dir / ROTEIROS_DIRNAME
    if not roteiros_dir.exists():
        return

    for roteiro in roteiros_dir.glob("*.docx"):
        match = ROTEIRO_REGEX.search(roteiro.name)
        if not match:
            log.warning(f"[roteiros] Nome fora do padrão: {roteiro.name}")
            continue
        mod, kind, nuc = match.groups()
        if kind and nuc:
            kind = "c" if kind.upper() == "C" else "p"
            target_dir = course_dir / f"mod{int(mod)}_n{kind}{int(nuc)}"
        else:
            target_dir = course_dir / f"mod{int(mod)}_vidint"
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            log.info(
                f"[roteiros] Diretório criado para {roteiro.name}: {target_dir.name}"
            )
        target_path = target_dir / roteiro.name
        if target_path.exists() and not force:
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(roteiro), str(target_path))
