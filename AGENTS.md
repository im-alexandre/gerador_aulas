# Repository Guidelines

## Project Structure & Module Organization
- Root entry point: `app.py` runs the end-to-end flow (DOCX → JSON → PPTX).
- Core logic: `app/docx_tagger.py`, `app/gpt_planner.py`, `app/pptx_renderer.py`, and modules in `app/`.
- Configs and prompts: `app/config/` and `app/prompts/`.
- Course data: `curso_*/` directories with DOCX files, `assets/`, and `roteiros/`.
- Outputs: `slides_plan.json` and `*.pptx` inside each `modX_ncY` / `modX_npY`.

## Build, Test, and Development Commands
- Full pipeline:
  - `python .\app.py --curso-dir .\curso_exemplo_testes_software --force`
  - Extrai roteiros do zip, gera `*_tagged.docx`, gera JSON e renderiza PPTX.

## Coding Style & Naming Conventions
- Python: 4-space indentation and `snake_case` for variables and functions.
- Keep prompts/instructions in `app/prompts/` and configs in `app/config/`.
- Prefer constantes em `app/config/paths.py` e `app/config/pipeline.py`.

## Testing Guidelines
- No automated test suite is configured. If you add tests, document the framework and command here.

## Commit & Pull Request Guidelines
- Git history is not available; follow clear, action-oriented commit messages (e.g., “Adicionar validação do JSON do plano”).
- PRs should include: a change summary, affected scripts, config/prompt updates when contracts change, and example outputs/logs for API changes.

## Security & Configuration Tips
- Set `OPENAI_API_KEY` in the environment for GPT calls.
- Review `app/config/paths.py` e `app/config/pipeline.py` before running.

## Agent-Specific Instructions
- Keep edits concise and repository-specific; prefer updating prompts/configs over hardcoding.
