# Repository Guidelines

## Project Structure & Module Organization
- `app/`: core Python package (content splitting, slide planning, rendering, image generation).
- `app/slide/`: slide kinds, validation, and PPTX rendering helpers (see `app/slide/README.md`).
- `app/prompts/`: LLM and image prompts plus `openai_api_key` path used at runtime.
- `terraform/`: course data inputs and outputs (modules/nuclei directories and `dist/`).
- Root files: `app.py` (main entrypoint), `requirements.txt`, template files like `template_ppt_graduacao.pptx` and `template_ppt_graduacao_map.json`.

## Build, Test, and Development Commands
- `python -m venv .venv`: create a local virtualenv.
- `.venv\\Scripts\\Activate.ps1`: activate the virtualenv on Windows PowerShell.
- `pip install -r requirements.txt`: install runtime dependencies.
- `python app.py --curso-dir terraform --template-id graduacao`: process a course directory end-to-end.
- `python app.py --curso-dir terraform --template-id graduacao --only mod1_nc1,mod1_nc2`: run selected nuclei only.
- `python app.py --curso-dir terraform --template-id graduacao --reuse-assets`: skip image regeneration when assets already exist.

## Coding Style & Naming Conventions
- Python, 4-space indentation, UTF-8.
- Follow PEP 8 naming: `snake_case` for functions/variables, `CamelCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep module imports ordered: standard library, third-party, then local.
- No formatter or linter is configured; keep changes tight and readable.

## Testing Guidelines
- No automated test suite is present in this repository.
- If you add tests, prefer `pytest` and keep names like `test_<feature>.py`.
- Run targeted manual checks by executing `python app.py` with a small `--only` set.

## Commit & Pull Request Guidelines
- Git history uses short, direct messages without a strict convention.
- Recommended: imperative, concise, optionally scoped. Example: `render: handle missing image`.
- PRs should include:
  - Summary of changes and affected modules.
  - How you validated (command output or manual run).
  - Screenshots or sample PPTX outputs when modifying rendering/templates.

## Security & Configuration Notes
- API key file lives at `app/prompts/openai_api_key`; avoid exposing it in logs or commits.
- Template changes require regenerating the map: delete `template_ppt_graduacao_map.json` to force rebuild on the next run.
