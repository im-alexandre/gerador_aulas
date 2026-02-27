import os
from pathlib import Path

from .gamma_api import (
    get_generation_id,
    generate_content_from_template,
    parse_json,
    write_last_response,
)


def find_course_dir(app_dir: Path) -> Path:
    env_dir = os.getenv("COURSE_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    root = app_dir.parent
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name == "app":
            continue
        return entry
    raise SystemExit("Nenhum diretório de curso encontrado na raiz.")


def main():
    app_dir = Path(os.getenv("APP_DIR", Path(__file__).resolve().parents[1])).resolve()
    os.environ.setdefault("APP_DIR", str(app_dir))
    course_dir = find_course_dir(app_dir)
    os.environ.setdefault("COURSE_DIR", str(course_dir))
    cards_dir = course_dir / "cards_exemplo"
    for file in os.listdir(cards_dir):
        if file.endswith(".md"):
            response = generate_content_from_template(app_dir, cards_dir / file)
            payload = parse_json(response)
            generation_id = get_generation_id(payload)
            write_last_response(
                app_dir / "output" / course_dir.name, response, generation_id
            )
            print("Status:", response.status_code)
            print(response.text)


if __name__ == "__main__":
    main()
