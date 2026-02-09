import os
import sys
import threading
import queue
import zipfile
import subprocess
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox


ROOT_DIR = Path(__file__).resolve().parent


class PipelineGUI(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("criador_aulas — GUI")
        self.geometry("900x700")
        self.minsize(900, 700)

        self.proc = None
        self.log_queue: queue.Queue[str] = queue.Queue()

        self._build_ui()
        self._poll_logs()

    def _suggest_nucleus_workers(self) -> int:
        cpu_count = os.cpu_count() or 1
        suggested = max(1, int(round(cpu_count * 0.75)))
        return min(cpu_count, suggested)

    def _build_ui(self) -> None:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        row = 0
        ctk.CTkLabel(frame, text="Diretório do curso").grid(row=row, column=0, sticky="w")
        self.course_dir_var = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.course_dir_var, width=500).grid(
            row=row, column=1, sticky="w", padx=8
        )
        ctk.CTkButton(frame, text="Selecionar", command=self._pick_course_dir).grid(
            row=row, column=2, sticky="w"
        )

        row += 1
        ctk.CTkLabel(frame, text="DOCX (conteúdo)").grid(row=row, column=0, sticky="w")
        self.docx_var = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.docx_var, width=500).grid(
            row=row, column=1, sticky="w", padx=8
        )
        ctk.CTkButton(frame, text="Selecionar", command=self._pick_docx).grid(
            row=row, column=2, sticky="w"
        )

        row += 1
        ctk.CTkLabel(frame, text="ZIP (roteiros)").grid(row=row, column=0, sticky="w")
        self.zip_var = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.zip_var, width=500).grid(
            row=row, column=1, sticky="w", padx=8
        )
        ctk.CTkButton(frame, text="Selecionar", command=self._pick_zip).grid(
            row=row, column=2, sticky="w"
        )

        row += 1
        ctk.CTkLabel(frame, text="Template PPTX (opcional)").grid(row=row, column=0, sticky="w")
        self.template_var = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.template_var, width=500).grid(
            row=row, column=1, sticky="w", padx=8
        )
        ctk.CTkButton(frame, text="Selecionar", command=self._pick_template).grid(
            row=row, column=2, sticky="w"
        )

        row += 1
        ctk.CTkLabel(frame, text="Model (LLM)").grid(row=row, column=0, sticky="w")
        self.model_var = ctk.StringVar(value="gpt-5.2")
        ctk.CTkEntry(frame, textvariable=self.model_var, width=200).grid(
            row=row, column=1, sticky="w", padx=8
        )

        row += 1
        ctk.CTkLabel(frame, text="Nucleus workers").grid(row=row, column=0, sticky="w")
        self.nucleus_workers_var = ctk.StringVar(value=str(self._suggest_nucleus_workers()))
        ctk.CTkEntry(frame, textvariable=self.nucleus_workers_var, width=120).grid(
            row=row, column=1, sticky="w", padx=8
        )

        row += 1
        ctk.CTkLabel(frame, text="Only (núcleos separados por vírgula)").grid(
            row=row, column=0, sticky="w"
        )
        self.only_var = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.only_var, width=500).grid(
            row=row, column=1, sticky="w", padx=8
        )

        row += 1
        ctk.CTkLabel(frame, text="Image provider").grid(row=row, column=0, sticky="w")
        self.image_provider_var = ctk.StringVar(value="openai")
        ctk.CTkOptionMenu(
            frame,
            values=["openai", "gamma"],
            variable=self.image_provider_var,
        ).grid(row=row, column=1, sticky="w", padx=8)

        row += 1
        ctk.CTkLabel(frame, text="Image model").grid(row=row, column=0, sticky="w")
        self.image_model_var = ctk.StringVar(value="gpt-image-1.5")
        ctk.CTkOptionMenu(
            frame,
            values=["gpt-image-1-mini", "gpt-image-1.5"],
            variable=self.image_model_var,
        ).grid(row=row, column=1, sticky="w", padx=8)

        row += 1
        ctk.CTkLabel(frame, text="Image size").grid(row=row, column=0, sticky="w")
        self.image_size_var = ctk.StringVar(value="1024x1536")
        ctk.CTkOptionMenu(
            frame,
            values=["1024x1024", "1024x1536", "1536x1024"],
            variable=self.image_size_var,
        ).grid(row=row, column=1, sticky="w", padx=8)

        row += 1
        ctk.CTkLabel(frame, text="Image quality").grid(row=row, column=0, sticky="w")
        self.image_quality_var = ctk.StringVar(value="low")
        ctk.CTkOptionMenu(
            frame,
            values=["low", "medium", "high"],
            variable=self.image_quality_var,
        ).grid(row=row, column=1, sticky="w", padx=8)

        row += 1
        ctk.CTkLabel(frame, text="Code interpreter").grid(row=row, column=0, sticky="w")
        self.code_interpreter_var = ctk.StringVar(value="default")
        ctk.CTkOptionMenu(
            frame,
            values=["default", "force", "disable"],
            variable=self.code_interpreter_var,
        ).grid(row=row, column=1, sticky="w", padx=8)

        row += 1
        self.force_var = ctk.BooleanVar(value=False)
        self.reuse_assets_var = ctk.BooleanVar(value=False)
        self.verbose_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame, text="--force", variable=self.force_var).grid(
            row=row, column=0, sticky="w"
        )
        ctk.CTkCheckBox(frame, text="--reuse-assets", variable=self.reuse_assets_var).grid(
            row=row, column=1, sticky="w", padx=8
        )
        ctk.CTkCheckBox(frame, text="--verbose", variable=self.verbose_var).grid(
            row=row, column=2, sticky="w", padx=8
        )

        row += 1
        self.run_btn = ctk.CTkButton(frame, text="Executar", command=self._run_pipeline)
        self.run_btn.grid(row=row, column=0, sticky="w", pady=8)
        self.export_btn = ctk.CTkButton(frame, text="Exportar ZIP do dist", command=self._export_dist)
        self.export_btn.grid(row=row, column=1, sticky="w", pady=8, padx=8)

        row += 1
        self.status_var = ctk.StringVar(value="Idle")
        ctk.CTkLabel(frame, textvariable=self.status_var).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(8, 4)
        )

        row += 1
        self.log_box = ctk.CTkTextbox(frame, width=820, height=300)
        self.log_box.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=8)
        self.log_box.configure(state="disabled")

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(row, weight=1)

    def _pick_course_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.course_dir_var.set(path)

    def _pick_docx(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("DOCX", "*.docx")])
        if path:
            self.docx_var.set(path)

    def _pick_zip(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("ZIP", "*.zip")])
        if path:
            self.zip_var.set(path)

    def _pick_template(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PPTX", "*.pptx")])
        if path:
            self.template_var.set(path)

    def _log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _poll_logs(self) -> None:
        try:
            while True:
                line = self.log_queue.get_nowait()
                self._log(line)
        except queue.Empty:
            pass
        self.after(200, self._poll_logs)

    def _run_pipeline(self) -> None:
        if self.proc and self.proc.poll() is None:
            messagebox.showwarning("Em execução", "Já existe um processo em execução.")
            return

        course_dir = self.course_dir_var.get().strip()
        docx_path = self.docx_var.get().strip()
        zip_path = self.zip_var.get().strip()

        if not course_dir or not docx_path or not zip_path:
            messagebox.showerror("Erro", "Selecione curso, DOCX e ZIP.")
            return

        course_dir_path = Path(course_dir).resolve()
        course_dir_path.mkdir(parents=True, exist_ok=True)

        # Validar que os arquivos estão dentro do diretório do curso
        try:
            Path(docx_path).resolve().relative_to(course_dir_path)
        except Exception:
            messagebox.showerror(
                "Erro",
                "O DOCX deve estar dentro do diretório do curso.",
            )
            return
        try:
            Path(zip_path).resolve().relative_to(course_dir_path)
        except Exception:
            messagebox.showerror(
                "Erro",
                "O ZIP deve estar dentro do diretório do curso.",
            )
            return

        cmd = [sys.executable, str(ROOT_DIR / "app.py"), "--curso-dir", str(course_dir_path)]

        template_path = self.template_var.get().strip()
        if template_path:
            cmd += ["--template", template_path]

        only = self.only_var.get().strip()
        if only:
            cmd += ["--only", only]

        model = self.model_var.get().strip()
        if model:
            cmd += ["--model", model]

        nucleus_workers_raw = self.nucleus_workers_var.get().strip()
        if nucleus_workers_raw:
            try:
                nucleus_workers = int(nucleus_workers_raw)
            except ValueError:
                messagebox.showerror("Erro", "Nucleus workers deve ser um número inteiro.")
                return
            if nucleus_workers <= 0:
                messagebox.showerror("Erro", "Nucleus workers deve ser >= 1.")
                return
            cmd += ["--nucleus-workers", str(nucleus_workers)]

        if self.force_var.get():
            cmd.append("--force")

        if self.reuse_assets_var.get():
            cmd.append("--reuse-assets")

        if self.verbose_var.get():
            cmd.append("--verbose")

        image_provider = self.image_provider_var.get().strip()
        if image_provider:
            cmd += ["--image-provider", image_provider]

        image_model = self.image_model_var.get().strip()
        if image_model:
            cmd += ["--image-model", image_model]

        image_size = self.image_size_var.get().strip()
        if image_size:
            cmd += ["--image-size", image_size]

        image_quality = self.image_quality_var.get().strip()
        if image_quality:
            cmd += ["--image-quality", image_quality]

        code_interpreter_mode = self.code_interpreter_var.get().strip()
        if code_interpreter_mode == "force":
            cmd.append("--use-code-interpreter")
        elif code_interpreter_mode == "disable":
            cmd.append("--no-code-interpreter")

        self._log(f"\n$ {' '.join(cmd)}\n")
        self.status_var.set("Rodando...")

        def _run():
            try:
                self.proc = subprocess.Popen(
                    cmd,
                    cwd=str(ROOT_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                if self.proc.stdout:
                    for line in self.proc.stdout:
                        self.log_queue.put(line)
                self.proc.wait()
            finally:
                self.status_var.set("Finalizado")

        threading.Thread(target=_run, daemon=True).start()

    def _export_dist(self) -> None:
        course_dir = self.course_dir_var.get().strip()
        if not course_dir:
            messagebox.showerror("Erro", "Selecione o diretório do curso.")
            return
        course_dir_path = Path(course_dir).resolve()
        dist_dir = course_dir_path / "dist"
        if not dist_dir.exists():
            messagebox.showerror("Erro", "dist/ não encontrado.")
            return

        target = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP", "*.zip")],
            initialfile="dist.zip",
        )
        if not target:
            return

        try:
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in dist_dir.rglob("*"):
                    if path.is_file():
                        zf.write(path, path.relative_to(dist_dir))
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao criar ZIP: {exc}")
            return

        messagebox.showinfo("OK", f"ZIP criado: {target}")

if __name__ == "__main__":
    app = PipelineGUI()
    app.mainloop()
