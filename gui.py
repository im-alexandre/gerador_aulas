from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Any

import customtkinter as ctk
from tkinter import filedialog

from app.config.paths import APP_DIR
from app.runner import RunConfig, run_pipeline

RECENTS_PATH = APP_DIR / "config" / "gui_recent.json"
MAX_RECENTS = 5


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("Criador de Aulas")
        self.geometry("880x620")
        self.minsize(820, 560)

        self._queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._cancel_event = threading.Event()
        self._worker: threading.Thread | None = None

        self._build_ui()
        self.after(150, self._process_queue)
        self._load_recents()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, padx=16, pady=16, sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="Curso").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.course_entry = ctk.CTkEntry(top, placeholder_text="Selecione a pasta do curso")
        self.course_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ctk.CTkButton(top, text="Procurar", command=self._browse_course).grid(
            row=0, column=2, sticky="e", padx=8, pady=6
        )
        ctk.CTkLabel(top, text="Recentes").grid(row=0, column=3, sticky="w", padx=8, pady=6)
        self.recents_var = ctk.StringVar(value="")
        self.recents_menu = ctk.CTkOptionMenu(
            top, variable=self.recents_var, values=[""], command=self._select_recent
        )
        self.recents_menu.grid(row=0, column=4, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(top, text="Template").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.template_var = ctk.StringVar(value="graduacao")
        ctk.CTkOptionMenu(top, variable=self.template_var, values=["graduacao", "tecnico"]).grid(
            row=1, column=1, sticky="w", padx=8, pady=6
        )

        ctk.CTkLabel(top, text="Provedor de imagens").grid(
            row=1, column=2, sticky="w", padx=8, pady=6
        )
        self.provider_var = ctk.StringVar(value="openai")
        ctk.CTkOptionMenu(top, variable=self.provider_var, values=["openai", "gamma"]).grid(
            row=1, column=3, sticky="w", padx=8, pady=6
        )

        ctk.CTkLabel(top, text="Only (opcional)").grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )
        self.only_entry = ctk.CTkEntry(top, placeholder_text="ex.: mod1_nc1,mod1_nc2")
        self.only_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        self.force_var = ctk.BooleanVar(value=False)
        self.force_check = ctk.CTkCheckBox(
            top, text="Force", variable=self.force_var
        )
        self.force_check.grid(row=2, column=2, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(top, text="OpenAI API Key (opcional)").grid(
            row=3, column=0, sticky="w", padx=8, pady=6
        )
        self.api_key_entry = ctk.CTkEntry(top, show="*", placeholder_text="sk-...")
        self.api_key_entry.grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        self.api_key_toggle = ctk.CTkButton(
            top, text="Mostrar", width=80, command=self._toggle_api_key
        )
        self.api_key_toggle.grid(row=3, column=2, sticky="w", padx=8, pady=6)

        actions = ctk.CTkFrame(self)
        actions.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)

        self.run_button = ctk.CTkButton(actions, text="Executar", command=self._run)
        self.run_button.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        self.cancel_button = ctk.CTkButton(
            actions, text="Cancelar", command=self._cancel, state="disabled"
        )
        self.cancel_button.grid(row=0, column=1, sticky="w", padx=8, pady=8)

        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=2, column=0, padx=16, pady=(0, 6), sticky="ew")
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(self, text="Pronto")
        self.status_label.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="w")

        self.log_box = ctk.CTkTextbox(self, height=240)
        self.log_box.grid(row=4, column=0, padx=16, pady=(0, 16), sticky="nsew")
        self.log_box.configure(state="disabled")

    def _browse_course(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self.course_entry.delete(0, "end")
            self.course_entry.insert(0, folder)
            self._push_recent(folder)

    def _select_recent(self, value: str) -> None:
        if not value:
            return
        self.course_entry.delete(0, "end")
        self.course_entry.insert(0, value)

    def _toggle_api_key(self) -> None:
        show = self.api_key_entry.cget("show")
        if show:
            self.api_key_entry.configure(show="")
            self.api_key_toggle.configure(text="Ocultar")
        else:
            self.api_key_entry.configure(show="*")
            self.api_key_toggle.configure(text="Mostrar")

    def _log(self, msg: str) -> None:
        self._queue.put(("log", msg))

    def _progress(self, current: int, total: int, name: str) -> None:
        self._queue.put(("progress", (current, total, name)))

    def _run(self) -> None:
        course = self.course_entry.get().strip()
        if not course:
            self._log("Selecione um diretório de curso válido.")
            return
        course_dir = Path(course)
        if not course_dir.exists():
            self._log("Diretório não encontrado.")
            return

        only_raw = self.only_entry.get().strip()
        only_set = None
        if only_raw:
            only_set = {n.strip() for n in only_raw.split(",") if n.strip()}

        api_key = self.api_key_entry.get().strip() or None

        config = RunConfig(
            course_dir=course_dir,
            template_id=self.template_var.get(),
            only=only_set,
            image_provider=self.provider_var.get(),
            openai_api_key=api_key,
            force=bool(self.force_var.get()),
        )
        self._push_recent(str(course_dir))

        self._cancel_event.clear()
        self.run_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.set(0)
        self.status_label.configure(text="Executando...")
        self._log("Iniciando processamento...")

        def _worker() -> None:
            try:
                run_pipeline(
                    config=config,
                    progress_cb=self._progress,
                    log_cb=self._log,
                    cancel_event=self._cancel_event,
                )
                self._queue.put(("done", None))
            except Exception as exc:
                self._queue.put(("error", str(exc)))

        self._worker = threading.Thread(target=_worker, daemon=True)
        self._worker.start()

    def _cancel(self) -> None:
        self._cancel_event.set()
        self.status_label.configure(text="Cancelando...")
        self._log("Cancelamento solicitado.")

    def _process_queue(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "progress":
                    current, total, name = payload
                    if total > 0:
                        self.progress.set(current / total)
                    self.status_label.configure(text=f"{current}/{total} concluídos ({name})")
                elif kind == "done":
                    self.status_label.configure(text="Concluído")
                    self.run_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                elif kind == "error":
                    self.status_label.configure(text="Erro")
                    self._append_log(f"Erro: {payload}")
                    self.run_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(150, self._process_queue)

    def _append_log(self, msg: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _load_recents(self) -> None:
        try:
            data = RECENTS_PATH.read_text(encoding="utf-8")
            items = [p for p in data.splitlines() if p.strip()]
        except FileNotFoundError:
            items = []
        except OSError:
            items = []
        self._update_recents(items)

    def _save_recents(self, items: list[str]) -> None:
        try:
            RECENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            RECENTS_PATH.write_text("\n".join(items), encoding="utf-8")
        except OSError:
            pass

    def _update_recents(self, items: list[str]) -> None:
        values = [""] + items
        self.recents_menu.configure(values=values)
        if self.recents_var.get() not in values:
            self.recents_var.set("")

    def _push_recent(self, path: str) -> None:
        path = path.strip()
        if not path:
            return
        try:
            current = [
                p
                for p in RECENTS_PATH.read_text(encoding="utf-8").splitlines()
                if p.strip()
            ]
        except OSError:
            current = []
        if path in current:
            current.remove(path)
        current.insert(0, path)
        current = current[:MAX_RECENTS]
        self._save_recents(current)
        self._update_recents(current)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
