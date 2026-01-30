import argparse
import os
import sys
from pathlib import Path


def find_course_dir() -> Path:
    env_dir = os.getenv("COURSE_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    root = Path(".").resolve()
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name == "app":
            continue
        return entry

    raise SystemExit("Nenhum diretório de curso encontrado na raiz.")


def parse_args(default_course: Path) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--curso-dir", dest="course_dir", default=str(default_course))
    ap.add_argument("--root", dest="course_dir")
    ap.add_argument("--app-dir", default=str(Path(".").resolve() / "app"))
    ap.add_argument("--prompt-md", default="prompts/prompt_gpt.md")
    ap.add_argument("--model", default="gpt-5.2")
    ap.add_argument("--export-dir", default="cards")
    ap.add_argument("--cards-dir", default="")
    ap.add_argument("--folder-id", required=True)
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--max-wait-minutes", type=int, default=0)
    return ap.parse_args()


if __name__ == "__main__":
    root_dir = Path(".").resolve()
    default_course = find_course_dir()
    args = parse_args(default_course)

    app_dir = Path(args.app_dir).resolve()
    course_dir = Path(args.course_dir).resolve()
    if not args.folder_id:
        args.folder_id = None
    os.environ.setdefault("COURSE_DIR", str(course_dir))
    os.environ.setdefault("APP_DIR", str(app_dir))
    sys.path.insert(0, str(root_dir))

    from app.pipeline_core import run_pipeline  # noqa: E402

    run_pipeline(args)
