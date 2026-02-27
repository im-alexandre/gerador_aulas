import argparse
import os
from pathlib import Path

from .gamma_api import get_generation_status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("generation_id")
    default_app_dir = os.getenv("APP_DIR", str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--app-dir", default=default_app_dir)
    args = ap.parse_args()

    app_dir = Path(args.app_dir).resolve()
    response = get_generation_status(app_dir, args.generation_id)
    status = (
        get_generation_status(base_dir=app_dir, generation_id=args.generation_id)
        or "unknown"
    )
    print(response.text)
    print("Status:", status)


if __name__ == "__main__":
    main()
