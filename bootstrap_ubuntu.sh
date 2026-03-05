#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y python3-tk tk-dev
sudo apt install -y python3.12-tk || true

python3.12 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt

python -c "import tkinter; import customtkinter as ctk; print('tk', tkinter.TkVersion, 'ctk', ctk.__version__)"
