import argparse
import logging
import os
import random
import shutil
import time
from pathlib import Path

from openai import OpenAI


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [INFO] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 2


def with_backoff(fn, *args, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            is_last = attempt == MAX_RETRIES
            if is_last:
                raise
            delay = min(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)), 30)
            delay += random.uniform(0, 0.5)
            log.warning(f"Falha na API (tentativa {attempt}/{MAX_RETRIES}): {exc}")
            log.warning(f"Aguardando {delay:.1f}s antes de tentar novamente.")
            time.sleep(delay)


def upload_file(client: OpenAI, path: Path) -> str:
    with open(path, "rb") as fh:
        f = with_backoff(client.files.create, file=fh, purpose="user_data")
    return f.id


def call_llm(
    client: OpenAI,
    model: str,
    instructions: str,
    file_ids: list[str],
    user_input: str,
    directory: str,
) -> str:
    log.info(f"[{directory}]Chamando o LLM")
    resp = with_backoff(
        client.responses.create,
        model=model,
        instructions=instructions,
        tools=[
            {
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "file_ids": file_ids,
                },
            }
        ],
        tool_choice={"type": "code_interpreter"},
        input=user_input,
    )
    return (f"[{directory} {resp.output_text}" or "").strip()


def generate_cards(
    client: OpenAI,
    prompt_md: str,
    docx_a: Path,
    docx_b: Path,
    model: str,
    directory: str,
) -> str:
    a_id = upload_file(client, docx_a)
    b_id = upload_file(client, docx_b)

    md = call_llm(
        client=client,
        model=model,
        instructions=prompt_md,
        file_ids=[a_id, b_id],
        user_input="Gere os cards para o gama de acordo com o as instruções em anexo",
        directory=directory,
    )

    if len(md) < 200:
        raise RuntimeError("Resposta curta demais. Provável falha na leitura dos DOCX.")

    if len(md) > 4200:
        md = call_llm(
            client=client,
            model=model,
            instructions=(
                "Reescreva o Markdown abaixo mantendo:\n"
                "- os mesmos cards\n"
                "- os mesmos títulos\n"
                "- códigos e notas intactos\n\n"
                "Objetivo:\n"
                "- reduzir texto corrido\n"
                "- no máximo 3 frases por card\n"
                "- não remover conceitos\n"
                "- não adicionar conteúdo\n\n"
                "Retorne APENAS o Markdown final."
            ),
            file_ids=[a_id, b_id],
            user_input=md,
            directory=directory,
        )

    return md


def prompt_choice(files: list[Path], msg: str) -> int:
    while True:
        s = input(msg).strip()
        if s.isdigit():
            idx = int(s)
            if 1 <= idx <= len(files):
                return idx - 1
        print("Escolha um número válido.")


def choose_two_files(docxs: list[Path]) -> tuple[Path, Path]:
    print("\nDOCX encontrados:")
    for i, p in enumerate(docxs, 1):
        print(f"  {i}) {p.name}")

    i1 = prompt_choice(docxs, "Selecione o 1º arquivo: ")
    f1 = docxs[i1]

    rest = [p for j, p in enumerate(docxs) if j != i1]
    print("\nRestantes:")
    for i, p in enumerate(rest, 1):
        print(f"  {i}) {p.name}")

    i2 = prompt_choice(rest, "Selecione o 2º arquivo: ")
    return f1, rest[i2]


def export_cards_md(source_dir: Path, export_root: Path) -> Path:
    export_root.mkdir(parents=True, exist_ok=True)
    src = source_dir / "cards.md"
    dst = export_root / f"{source_dir.name}_card.md"
    shutil.copyfile(src, dst)
    return dst


def select_docx_files(d: Path) -> tuple[Path, Path] | None:
    docxs = list(d.glob("*.docx"))
    if len(docxs) < 2:
        return None
    if len(docxs) == 2:
        return docxs[0], docxs[1]
    return choose_two_files(docxs)


def process_dir(
    client: OpenAI,
    d: Path,
    prompt_md: str,
    model: str,
    export_dir: Path,
    force: bool,
) -> Path | None:
    log.info(f"Processando pasta: {d.name}")
    cards_md = d / "cards.md"

    selected = select_docx_files(d)
    if not selected:
        return None
    a_path, b_path = selected
    log.info(f"analisando os arquivos {a_path.name} e {b_path.name}")
    if cards_md.exists() and not force:
        dst = export_cards_md(d, export_dir)
        log.info(f"[{d.name}]Acessando o LLM e encaminhando os arquivos")
        log.info(f"[{d.name}]Encaminhando fontes de dados para o LLM")
        log.info(
            f"[{d.name}]Encaminhando Idéias para o chatgpt: \n -arquivos {a_path.name} e {b_path.name}"
        )
        return dst

    md = generate_cards(
        client=client,
        prompt_md=prompt_md,
        docx_a=a_path,
        docx_b=b_path,
        model=model,
        directory=d.name,
    )

    cards_md.write_text(md, encoding="utf-8")
    dst = export_cards_md(d, export_dir)
    log.info(f"OK — Gerado {cards_md} → {dst}")
    return dst


def generate_cards_for_root(
    root: Path,
    prompt_md_path: Path,
    model: str,
    export_dir: Path,
    only: str | None = None,
    force: bool = False,
    exclude_dirs: set[str] | None = None,
) -> list[Path]:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Defina OPENAI_API_KEY.")

    client = OpenAI()
    prompt_md = prompt_md_path.read_text(encoding="utf-8")

    exclude_dirs = exclude_dirs or set()
    if only:
        subdirs = [root / only]
    else:
        subdirs = []
        for p in root.iterdir():
            if not p.is_dir():
                continue
            if p.name.startswith("."):
                continue
            if p.name in exclude_dirs:
                continue
            subdirs.append(p)

    results = []
    for d in subdirs:
        result = process_dir(
            client=client,
            d=d,
            prompt_md=prompt_md,
            model=model,
            export_dir=export_dir,
            force=force,
        )
        if result:
            results.append(result)
    return results


def cli_main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    default_prompt = Path(os.getenv("APP_DIR", ".")) / "prompts" / "prompt_gpt.md"
    ap.add_argument("--prompt-md", default=str(default_prompt))
    ap.add_argument("--model", default="gpt-5.2")
    ap.add_argument("--export-dir", default="cards")
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    generate_cards_for_root(
        root=Path(args.root),
        prompt_md_path=Path(args.prompt_md),
        model=args.model,
        export_dir=Path(args.export_dir),
        only=args.only,
        force=args.force,
        exclude_dirs={
            "app",
            "cards",
            "cards_exemplo",
            "config",
            "output",
            "prompts",
            "scripts",
        },
    )


if __name__ == "__main__":
    cli_main()
