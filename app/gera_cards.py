import os
from pathlib import Path

from .gpt_cards import cli_main


app_dir = Path(__file__).resolve().parents[1]
os.environ.setdefault("APP_DIR", str(app_dir))


if __name__ == "__main__":
    cli_main()
